"""Purpose limitation, consent receipts, retention, and claim-boundary contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.member2.common import (
    ClaimClass,
    ConsentStatus,
    EvidenceStatus,
    ProcessingPurpose,
    SourceType,
)

STRICT_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConsentReceiptCreate(BaseModel):
    receipt_id: UUID = Field(default_factory=uuid4)
    purpose: ProcessingPurpose
    purpose_version: str = Field(min_length=1, max_length=64)
    notice_version: str = Field(min_length=1, max_length=64)
    granted_metrics: list[str] = Field(min_length=1, max_length=100)
    granted_sources: list[SourceType] = Field(min_length=1, max_length=16)
    consented_at: datetime
    expires_at: datetime | None = None
    model_config = STRICT_CONFIG

    @field_validator("consented_at", "expires_at")
    @classmethod
    def aware_times(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("consent timestamps must include a UTC offset")
        return value

    @field_validator("granted_metrics", "granted_sources")
    @classmethod
    def unique_grants(cls, value: list) -> list:
        if len(value) != len(set(value)):
            raise ValueError("consent grants must be unique")
        return value

    @model_validator(mode="after")
    def validate_expiry(self) -> ConsentReceiptCreate:
        if self.expires_at is not None and self.expires_at <= self.consented_at:
            raise ValueError("expires_at must be after consented_at")
        return self


class ConsentReceiptResponse(ConsentReceiptCreate):
    id: int
    user_id: int
    status: ConsentStatus
    withdrawn_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ConsentWithdrawalRequest(BaseModel):
    delete_linked_observations: bool = True
    reason: str = Field(default="user_withdrawal", min_length=1, max_length=128)
    model_config = STRICT_CONFIG


class ConsentWithdrawalResponse(BaseModel):
    receipt_id: UUID
    status: Literal[ConsentStatus.WITHDRAWN] = ConsentStatus.WITHDRAWN
    deleted_observation_count: int = Field(ge=0)
    model_config = STRICT_CONFIG


class FeatureClaim(BaseModel):
    feature_id: str
    claim_class: ClaimClass
    evidence_status: EvidenceStatus
    intended_use: str
    prohibited_claims: list[str]
    promotion_requirements: list[str]
    model_config = STRICT_CONFIG


CLAIM_REGISTRY: tuple[FeatureClaim, ...] = (
    FeatureClaim(
        feature_id="health-connect-observation-ingestion",
        claim_class=ClaimClass.ENGINEERING,
        evidence_status=EvidenceStatus.TECHNICALLY_VALIDATED,
        intended_use="Source-faithful collection and normalization of supported observations.",
        prohibited_claims=["clinical accuracy", "diagnosis", "emergency detection"],
        promotion_requirements=["real-device matrix", "store-policy review", "privacy review"],
    ),
    FeatureClaim(
        feature_id="ppg-signal-usability-gate",
        claim_class=ClaimClass.RESEARCH_ONLY,
        evidence_status=EvidenceStatus.EXTERNALLY_VALIDATED,
        intended_use="Research-only rejection of low-usability PPG windows.",
        prohibited_claims=["medical-grade heart rate", "disease detection"],
        promotion_requirements=["prospective device-disjoint study", "subgroup evaluation"],
    ),
    FeatureClaim(
        feature_id="camera-capture-quality",
        claim_class=ClaimClass.ENGINEERING,
        evidence_status=EvidenceStatus.TECHNICALLY_VALIDATED,
        intended_use="In-memory exposure, blur, clipping, and motion guidance.",
        prohibited_claims=["rPPG measurement", "camera SpO2", "diagnosis"],
        promotion_requirements=["physical-device capture matrix"],
    ),
    FeatureClaim(
        feature_id="ppg-derived-respiration",
        claim_class=ClaimClass.PROHIBITED,
        evidence_status=EvidenceStatus.UNVALIDATED,
        intended_use="No production output; retained only as a documented rejected experiment.",
        prohibited_claims=["respiratory-rate estimation", "respiratory monitoring"],
        promotion_requirements=["new protocol", "external validation", "safety review"],
    ),
    FeatureClaim(
        feature_id="phone-camera-spo2",
        claim_class=ClaimClass.PROHIBITED,
        evidence_status=EvidenceStatus.UNVALIDATED,
        intended_use="No implementation or output.",
        prohibited_claims=["oxygen saturation estimation", "hypoxaemia detection"],
        promotion_requirements=["paired optical hardware", "calibration study", "regulatory review"],
    ),
)


__all__ = [
    "CLAIM_REGISTRY",
    "ConsentReceiptCreate",
    "ConsentReceiptResponse",
    "ConsentWithdrawalRequest",
    "ConsentWithdrawalResponse",
    "FeatureClaim",
]
