import sqlite3
import json
import uuid
from datetime import datetime

def populate_demo():
    db_path = "backend/data/local_brain.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Clear existing episodic memory nodes and edges
    cursor.execute("DELETE FROM nodes WHERE id LIKE 'mem-%'")
    cursor.execute("DELETE FROM edges WHERE source LIKE 'mem-%' OR target LIKE 'mem-%'")
    
    # 2. Define standard demo memories
    memories = [
        {
            "content": "My name is Nandu",
            "importance": 0.90,
            "category": "FACT",
            "semantic_tags": ["fact", "identity"],
            "fact": {"subject": "USER", "predicate": "identity.name", "object": "Nandu", "type": "Identity", "is_correction": False}
        },
        {
            "content": "I live in Hyderabad",
            "importance": 0.75,
            "category": "FACT",
            "semantic_tags": ["fact", "location"],
            "fact": {"subject": "USER", "predicate": "location", "object": "Hyderabad", "type": "Fact", "is_correction": False}
        },
        {
            "content": "I work as a Software Engineer",
            "importance": 0.80,
            "category": "FACT",
            "semantic_tags": ["fact", "profession"],
            "fact": {"subject": "USER", "predicate": "profession", "object": "Software Engineer", "type": "Fact", "is_correction": False}
        },
        {
            "content": "I have a Golden Retriever dog named Max",
            "importance": 0.85,
            "category": "FACT",
            "semantic_tags": ["fact", "pet"],
            "fact": {"subject": "USER", "predicate": "pet", "object": "Golden Retriever named Max", "type": "Fact", "is_correction": False}
        },
        {
            "content": "I like Chemex coffee",
            "importance": 0.70,
            "category": "PREFERENCE",
            "semantic_tags": ["preference", "beverage"],
            "fact": {"subject": "USER", "predicate": "likes", "object": "Chemex coffee", "type": "Preference", "is_correction": False}
        },
        {
            "content": "I prefer dark mode interfaces",
            "importance": 0.60,
            "category": "PREFERENCE",
            "semantic_tags": ["preference", "ui"],
            "fact": {"subject": "USER", "predicate": "likes", "object": "dark mode UI", "type": "Preference", "is_correction": False}
        },
        {
            "content": "I dislike mushrooms",
            "importance": 0.50,
            "category": "PREFERENCE",
            "semantic_tags": ["preference", "food"],
            "fact": {"subject": "USER", "predicate": "dislikes", "object": "mushrooms", "type": "Preference", "is_correction": False}
        }
    ]
    
    # 3. Insert each memory node
    now_str = datetime.now().isoformat()
    for mem in memories:
        node_id = f"mem-{uuid.uuid4().hex[:8]}"
        
        metadata = {
            "status": "ACTIVE",
            "category": mem["category"],
            "confidence": 0.95,
            "source_message": mem["content"],
            "timestamp": now_str,
            "created_at": now_str,
            "last_accessed": now_str,
            "last_reinforced": now_str,
            "retention_score": mem["importance"],
            "fact": mem["fact"]
        }
        
        cursor.execute(
            "INSERT INTO nodes (id, content, access_count, importance, source, semantic_tags, metadata, consolidated) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                node_id,
                mem["content"],
                1,
                mem["importance"],
                "user",
                json.dumps(mem["semantic_tags"]),
                json.dumps(metadata),
                0
            )
        )
        print(f"Inserted: {mem['content']} ({node_id})")
        
    conn.commit()
    conn.close()
    print("Successfully populated demo memories database!")

if __name__ == "__main__":
    populate_demo()
