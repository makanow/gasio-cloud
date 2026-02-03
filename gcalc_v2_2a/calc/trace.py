from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class TraceNode:
    key: str
    title: str
    formula: str
    inputs: Dict[str, Any]
    value: Any
    unit: str = ''
    notes: str = ''

@dataclass
class Trace:
    nodes: List[TraceNode] = field(default_factory=list)

    def add(self, **kwargs) -> TraceNode:
        node = TraceNode(**kwargs)
        self.nodes.append(node)
        return node

    def as_dict(self):
        return [n.__dict__ for n in self.nodes]
