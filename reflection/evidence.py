from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
import time


@dataclass
class Evidence:
    id: str
    content: str
    source: str
    page: Optional[int] = None
    bbox: Optional[Dict[str, float]] = None
    row: Optional[int] = None
    col: Optional[int] = None
    confidence: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # flatten meta if None
        if d.get('meta') is None:
            d['meta'] = {}
        return d
