import operator
from typing import Annotated, Any, TypedDict


class OrchestratorState(TypedDict, total=False):
    run_id: int
    digest_key: str
    posts: list[dict]        # collected candidates
    plan: dict               # DigestPlan
    draft: str               # markdown
    gate: dict               # deterministic gate result
    judge: dict              # JudgeVerdict
    # steps accumulate across nodes (reducer), forming the per-run evidence trail.
    steps: Annotated[list[dict[str, Any]], operator.add]
    status: str
