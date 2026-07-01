"""
Oneiros Cognitive Algorithms - Contradiction Detection

Detects potential contradictions between memory nodes using semantic similarity and negation cues.
"""

from typing import List, Tuple
from domain.memory import MemoryNode
from kernel.algorithms.similarity import detect_duplicate_candidates

def find_potential_contradiction_pairs(
    nodes: List[MemoryNode]
) -> List[Tuple[MemoryNode, MemoryNode]]:
    """
    Identifies candidate memory pairs that cover similar topics but likely contradict.
    
    Checks pairs with high semantic overlap (similarity > 0.60) for opposite negation
    indicators or contradicting emotion words.
    """
    # Use similarity check with a lower threshold to find semantic matches
    similar_pairs = detect_duplicate_candidates(nodes, threshold=0.60)
    contradictions = []

    negation_words = {"not", "never", "no", "dont", "cannot", "wont", "stop", "avoid", "fail"}
    opposite_pairs = [
        ("like", "dislike"), ("like", "hate"), ("love", "hate"),
        ("want", "avoid"), ("agree", "disagree"), ("succeed", "fail")
    ]

    for node_a, node_b, _ in similar_pairs:
        text_a = node_a.content.lower()
        text_b = node_b.content.lower()
        
        words_a = set(text_a.split())
        words_b = set(text_b.split())
        
        # Scenario 1: Negation mismatch (one negates, the other asserts)
        has_negation_a = any(neg in words_a for neg in negation_words)
        has_negation_b = any(neg in words_b for neg in negation_words)
        
        is_contradiction = False
        if has_negation_a != has_negation_b:
            is_contradiction = True

        # Scenario 2: Antonym pairs present
        if not is_contradiction:
            for w1, w2 in opposite_pairs:
                if (w1 in words_a and w2 in words_b) or (w2 in words_a and w1 in words_b):
                    is_contradiction = True
                    break
                    
        if is_contradiction:
            contradictions.append((node_a, node_b))

    return contradictions
