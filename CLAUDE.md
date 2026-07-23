# Document Workflow Platform

Event-driven platform that ingests documents from many channels, runs them
through a configurable workflow (a DAG of steps), and gives full status
visibility at scale. Extraction is a pluggable black box — we do NOT build it.

## Stack
- Language: Python 3.12 + `uv` for deps/venv  (if using Node/TS, update commands)
- MongoDB (replica set — required for change streams), MinIO (raw files), Redis
- Redpanda/Kafka (event spine), Kafka Connect + Debezium (CDC)
- Kubernetes + KEDA (autoscale workers on consumer lag)
- Observability: Prometheus + Grafana + OpenTelemetry

## Core invariants — never violate these
1. **All messaging goes through the `EventBus` interface.** Two impls:
   `InMemoryEventBus` and `KafkaEventBus`, chosen by `RUN_MODE`.
   Never call Kafka directly from business logic.
2. **`RUN_MODE=inline`** = API + engine + executor in ONE process, in-memory bus,
   no Kafka. **`RUN_MODE=distributed`** = separate processes over Kafka.
   The node-execution logic is IDENTICAL in both modes; only the transport differs.
3. **Every consumer is idempotent** — delivery is at-least-once, so processing
   the same message twice must be safe.
4. **Extraction lives behind an interface** and never leaks into the engine.
5. **The join barrier fires exactly once**: atomic `$addToSet` of completed deps
   plus a guarded `pending -> ready` status flip.

## Architecture flow
channels -> API + ingestion (store raw, dedup, create run) -> trigger/startRun
-> engine resolves the DAG (dependsOn) -> executor runs each node -> results in
Mongo. CDC streams Mongo changes to Kafka for cache invalidation + read models.

## Data model
- `workflows`: definition (nodes with `dependsOn`), versioned
- `workflow_runs`: per-run state, per-node status/output
- `documents`: metadata + status; UNIQUE index on the dedup key

## Dev commands
- `docker compose up`        # Mongo(RS), Redpanda, Redis, MinIO
- `uv sync`                  # install deps from uv.lock
- `RUN_MODE=inline uv run uvicorn app.main:app --reload`   # run the whole thing locally
- `uv run pytest`            # tests

## Conventions
- Small, single-responsibility modules. Type hints everywhere.
- Every workflow step is idempotent and re-runnable.
- Commit at each green acceptance check.

## Build order (tick as you go)
- [x] 1. Contracts + docker-compose + EventBus interface
- [x] 2. API + ingestion
- [ ] 3. Trigger + startRun (dedup)
- [ ] 4. Engine (DAG + join barrier)
- [ ] 5. Executor (inline first)
- [ ] 6. Extra channels + scheduler
- [ ] 7. CDC (Debezium) + read models
- [ ] 8. Caching
- [ ] 9. Observability
- [ ] 10. Kubernetes + KEDA
- [ ] 11. DB optimization (measured)
- [ ] 12. Load test (capture RPS/p99)