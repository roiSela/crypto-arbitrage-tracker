import json
import time
from dataclasses import dataclass, asdict


@dataclass
class PriceEvent:
    exchange: str
    symbol: str
    price: float
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "PriceEvent":
        return cls(**json.loads(data))
