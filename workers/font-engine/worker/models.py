from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field
class QueueMessage(BaseModel):
    schemaVersion: Literal['3.3.0']
    jobId: str
    projectId: str
    kind: Literal['process','export']
    idempotencyKey: str
    callbackBaseUrl: str
class WorkerProgress(BaseModel):
    progress: int = Field(ge=0, le=100)
    message: str
class GlyphResult(BaseModel):
    page: int
    cellId: str
    character: str
    unicode: str
    status: Literal['ok','review','missing']
    rawIou: float
    tolerantF1: float
    inkRatio: float
    svgUrl: str
    metadataUrl: str
