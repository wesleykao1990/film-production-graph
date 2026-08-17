from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VersionCreateRequest(BaseModel):
    payload: dict[str, Any]
    created_by: str = "human"
    status: str = "draft"


class DecisionRequest(BaseModel):
    actor: str = "prototype-user"
    rationale: str = Field(min_length=1, max_length=2000)


class SkillRunRequest(BaseModel):
    project_id: str
    input_version_ids: list[str] = Field(min_length=1)


class WorkflowRunRequest(BaseModel):
    project_id: str
    inputs: dict[str, str]


class WorkflowApprovalRequest(BaseModel):
    actor: str = "prototype-user"
    rationale: str = Field(min_length=1, max_length=2000)
