"""Read scheduler diagnostics using the workspace owner's account."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from softmax_client.http import observatory_client


class _WorkspaceIdentity(BaseModel):
    provisioning_id: UUID


class ResearcherReservation(BaseModel):
    attempt_id: str
    session_id: str
    task_id: int | None
    coworld_id: str | None
    run_id: str | None
    status: str
    dispatch_started: bool
    resolution_required: bool
    execution_uncertain: bool


class SchedulerWork(BaseModel):
    attempt_id: str
    blocked_by_attempt_id: str | None
    session_id: str
    state: str
    reason_code: str


class WorkspaceSchedulerStatus(BaseModel):
    inference_state: str
    paused: bool
    heartbeat: datetime | None
    restart_required: bool
    researcher_limit: int
    researcher_slots_reserved: int
    reservations_truncated: bool
    reservations: list[ResearcherReservation]
    work_count: int
    work: list[SchedulerWork]


def scheduler_status(*, server: str, token: str) -> WorkspaceSchedulerStatus | None:
    with observatory_client(server=server, token=token, timeout=25.0) as client:
        current = client.get("/v2/hermes")
        current.raise_for_status()
        if current.json() is None:
            return None
        workspace = _WorkspaceIdentity.model_validate_json(current.content)
        response = client.get(f"/v2/workspaces/{workspace.provisioning_id}/scheduler-status")
        response.raise_for_status()
        return WorkspaceSchedulerStatus.model_validate_json(response.content)
