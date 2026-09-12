"""
Request/response shapes for the /generate endpoint. Every field here is
something the pipeline genuinely computes — nothing is fabricated. Fields
that are session-level (like coverage) or design choices (like the fact the
hybrid score does not override the prediction) are documented in their
description so the frontend/README can display them honestly.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    user_story: str = Field(..., min_length=1, description="The raw user story text.")


class RequirementItem(BaseModel):
    step: str                  # e.g. "Step-1: Validate"
    step_purpose: str = Field("", description="Why this step exists in the process (Initiation / Processing / Completion).")
    action_verb: str
    text: str                  # the generated IEEE-830 requirement sentence
    repaired: bool = Field(False, description="True if the automatic repair loop fixed a grammar/vague-term issue.")
    repair_actions: List[str] = Field(default_factory=list, description="What the repair loop actually changed, if anything.")
    requires_review: bool = Field(False, description="True if issues remained after repair -- kept and shown, not dropped.")
    unrepaired_issues: List[str] = Field(default_factory=list, description="Specific issues that could not be auto-repaired.")


class NERFieldResult(BaseModel):
    text: str
    confidence: float = Field(..., description="Model's own confidence for this extracted span (0-1).")
    low_confidence: bool = Field(..., description="True if confidence is below the quality threshold.")


class ClauseFieldResult(NERFieldResult):
    """Condition/Outcome go through the extra boundary-detection + candidate-
    scoring layers (see pipeline.py), so their result carries more detail
    than a plain actor/action span."""
    connector_detected: bool = Field(
        ..., description="Whether a known linguistic connector (if/when/before/so "
                          "that/etc.) was found anchoring this clause."
    )
    boundary_corrected: bool = Field(
        ..., description="Whether the linguistic boundary-detection layer extended or "
                          "shifted the model's raw span to a complete clause."
    )
    decision: str = Field(
        ..., description="'accepted' (used in generated requirements), 'flagged' "
                          "(shown but excluded — below the acceptance threshold), "
                          "'rejected' (too low quality to show), or 'not_found'."
    )


class ScoringInfo(BaseModel):
    model_confidence: float
    ontology_similarity: float
    hybrid_score: float
    alpha: float
    beta: float
    confidence_threshold: float
    selection_status: str      # "High confidence (model)" or "Low confidence — flagged for review"
    low_confidence: bool = Field(..., description="True if model_confidence is below confidence_threshold.")


class ExtractionSummary(BaseModel):
    actor_found: bool
    action_found: bool
    condition_found: bool
    outcome_found: bool


class ValidationInfo(BaseModel):
    status: str                 # "Passed" | "Passed with warnings" | "Issues found"
    issues: List[str] = Field(default_factory=list, description="Concrete, specific problems found.")
    checks_performed: List[str]
    duplicate_within_story: bool
    ambiguous_terms_found: List[str]
    extraction_summary: ExtractionSummary
    generic_fallback_count: int = Field(
        0, description="Number of generated requirements that used generic phrasing "
                        "because their action verb has no specific vocabulary entry."
    )
    session_processes_covered: int
    session_total_processes: int
    session_coverage_pct: float
    note: str


class NEROutput(BaseModel):
    actor: NERFieldResult
    action: NERFieldResult
    condition: ClauseFieldResult
    outcome: ClauseFieldResult


class GenerateResponse(BaseModel):
    user_story: str
    process_concept: str
    ontology_mapping: str
    domain_entity: str = Field("", description="The story-specific entity extracted from the raw text, "
                                                 "used as the object in every generated requirement.")
    ner: NEROutput
    scoring: ScoringInfo
    requirements: List[RequirementItem]
    validation: ValidationInfo
    warnings: List[str] = Field(
        default_factory=list,
        description="Top-level, human-readable warnings worth surfacing prominently in the UI "
                    "(low confidence prediction, incomplete extraction, generic fallback usage).",
    )
    history_id: Optional[int] = Field(
        None, description="Database id this result was saved under, if the history database is working."
    )


class HealthResponse(BaseModel):
    status: str
    ner_model_loaded: bool
    classifier_model_loaded: bool
    num_process_concepts: int
    device: str
    error: Optional[str] = Field(
        None, description="The real reason loading failed, if status is not 'ready'."
    )
