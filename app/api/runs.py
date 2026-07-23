from fastapi import APIRouter

from app.api.schemas import RunResponse
from app.db import get_workflow_runs
from app.errors import NotFoundError

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str) -> RunResponse:
    run = await get_workflow_runs().find_one({"id": run_id})
    if run is None:
        raise NotFoundError(f"run '{run_id}' not found")

    return RunResponse(
        id=run["id"],
        workflow_id=run["workflow_id"],
        workflow_version=run["workflow_version"],
        document_id=run["document_id"],
        status=run["status"],
        node_states=run.get("node_states", {}),
    )
