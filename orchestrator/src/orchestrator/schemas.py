"""Structured outputs. These schemas are enforced at decode time (Ollama
`format`), not merely requested in the prompt (design draft section 8)."""
from pydantic import BaseModel, Field


class PlanItem(BaseModel):
    reddit_id: str = Field(description="id of a candidate post to include")
    reason: str = Field(description="one line: why this post belongs in today's digest")


class DigestPlan(BaseModel):
    title: str = Field(description="Korean title for today's digest")
    angle: str = Field(description="one-line editorial angle tying the picks together")
    include: list[PlanItem] = Field(description="3-5 selected posts, most important first")


class JudgeVerdict(BaseModel):
    accuracy: int = Field(ge=1, le=5, description="faithful to the source posts")
    non_redundancy: int = Field(ge=1, le=5, description="items are distinct, no repetition")
    readability: int = Field(ge=1, le=5, description="clear, well-structured Korean")
    confidence: float = Field(ge=0.0, le=1.0, description="judge self-confidence")
    notes: str = Field(description="short justification")
