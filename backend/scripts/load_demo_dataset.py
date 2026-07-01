"""
Demo Dataset Loader — Reads demo_memories.json and constructs a MemoryGraphSnapshot.
Separated from the API layer per separation of concerns.
"""

import json
import os
from domain.memory import MemoryNode, MemoryGraphSnapshot


def load_demo_snapshot() -> MemoryGraphSnapshot:
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "demo_memories.json")
    with open(data_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    nodes = [
        MemoryNode(
            id=item["id"],
            content=item["content"],
            importance=item.get("importance", 0.5),
            access_count=item.get("access_count", 1),
            source=item.get("source", "user"),
            semantic_tags=item.get("semantic_tags", [])
        )
        for item in raw
    ]
    return MemoryGraphSnapshot(nodes=nodes, edges=[])
