from app.errors import DAGValidationError
from app.models import WorkflowNode


def validate_dag(nodes: list[WorkflowNode]) -> None:
    """Validate node ids are unique, every depends_on references a real node, and
    the dependency graph has no cycles (Kahn's algorithm)."""
    ids = [node.id for node in nodes]
    if len(ids) != len(set(ids)):
        raise DAGValidationError("workflow definition has duplicate node ids")

    id_set = set(ids)
    for node in nodes:
        for dep in node.depends_on:
            if dep not in id_set:
                raise DAGValidationError(
                    f"node '{node.id}' depends_on unknown node '{dep}'"
                )

    in_degree = {node.id: 0 for node in nodes}
    dependents: dict[str, list[str]] = {node.id: [] for node in nodes}
    for node in nodes:
        for dep in node.depends_on:
            dependents[dep].append(node.id)
            in_degree[node.id] += 1

    queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
    visited = 0
    while queue:
        current = queue.pop()
        visited += 1
        for neighbor in dependents[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if visited != len(nodes):
        raise DAGValidationError("workflow definition contains a cycle")
