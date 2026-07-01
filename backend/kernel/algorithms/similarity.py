"""
Oneiros Cognitive Algorithms - Cosine Similarity & Duplicate Detection

Computes semantic similarity measures using vector embeddings or TF-IDF fallbacks.
"""

import numpy as np
from typing import List, Tuple, Optional
from domain.memory import MemoryNode
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity

def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Computes vector cosine similarity.
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def detect_duplicate_candidates(
    nodes: List[MemoryNode],
    threshold: float = 0.90
) -> List[Tuple[MemoryNode, MemoryNode, float]]:
    """
    Scans memory nodes and identifies pairs whose content similarity exceeds the threshold.
    
    Falls back to TF-IDF if nodes do not contain semantic vector embeddings.
    """
    candidates = []
    if len(nodes) < 2:
        return candidates

    # Check if all nodes have embeddings of matching dimensions
    has_embeddings = all(n.embedding is not None and len(n.embedding) > 0 for n in nodes)

    if has_embeddings:
        matrix = np.array([n.embedding for n in nodes])
        sim_matrix = sklearn_cosine_similarity(matrix)
    else:
        # TF-IDF Fallback
        corpus = [n.content for n in nodes]
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(corpus)
        sim_matrix = sklearn_cosine_similarity(tfidf_matrix)

    # Extract upper triangular indices to avoid checking (i, i) and duplicate pairs (i, j) vs (j, i)
    n_nodes = len(nodes)
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            sim_score = float(sim_matrix[i, j])
            if sim_score >= threshold:
                candidates.append((nodes[i], nodes[j], sim_score))

    return candidates
