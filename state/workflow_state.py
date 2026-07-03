from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class WorkflowState:

    input_data: Any = None

    document: Any = None

    metrics: Any = None

    risk: Any = None

    output: Any = None

    metadata: dict = field(default_factory=dict)