"""
Oneiros Cognitive Algorithms - Semantic Clustering

Clusters memory nodes based on semantic embeddings or TF-IDF fallbacks using DBSCAN.
"""

import numpy as np
from typing import List
from domain.memory import MemoryNode
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer

def cluster_memories(nodes: List[MemoryNode], preference: str = "embeddings") -> List[List[MemoryNode]]:
    """
    Groups memory nodes into semantic clusters.
    
    1. Attempts to cluster using vector embeddings.
    2. Falls back to TF-IDF text features if embeddings are unavailable.
    """
    if not nodes:
        return []
    if len(nodes) == 1:
        return [nodes]

    has_embeddings = (
        preference == "embeddings" and 
        all(n.embedding is not None and len(n.embedding) > 0 for n in nodes)
    )

    if has_embeddings:
        matrix = np.array([n.embedding for n in nodes])
        # Use DBSCAN with cosine distance
        db = DBSCAN(eps=0.25, min_samples=1, metric="cosine")
        labels = db.fit_predict(matrix)
    else:
        # TF-IDF Fallback
        corpus = [n.content for n in nodes]
        vectorizer = TfidfVectorizer(stop_words='english')
        try:
            tfidf_matrix = vectorizer.fit_transform(corpus).toarray()
            db = DBSCAN(eps=0.35, min_samples=1, metric="cosine")
            labels = db.fit_predict(tfidf_matrix)
        except Exception:
            # If tf-idf extraction fails (e.g. empty corpus or non-english punctuation only), return single-node clusters
            return [[n] for n in nodes]

    # Organize clusters based on generated labels
    clusters_dict = {}
    for idx, label in enumerate(labels):
        label_key = int(label)
        if label_key == -1:
            # In DBSCAN, -1 represents noise nodes; let's treat each noise node as its own single cluster
            clusters_dict[f"noise_{idx}"] = [nodes[idx]]
        else:
            if label_key not in clusters_dict:
                clusters_dict[label_key] = []
            clusters_dict[label_key].append(nodes[idx])

    return list(clusters_dict.values())
