from typing import Literal

from pydantic import BaseModel


class ReflectionResult(BaseModel):

    passed: bool

    score: float

    issues: list[str]

    recommendation: Literal["BUY", "HOLD", "SELL"]