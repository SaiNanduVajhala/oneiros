# 🧠 Cognitive Memory OS — Research & Algorithmic Validation

This document contains the detailed mathematical models, algorithmic parameters, and design validation for the sleep consolidation stages and write-locking synchronization mechanisms in Oneiros.

---

## 1. Sequential Cognitive Sleep Pipeline (N1 ➔ REM)

Oneiros translates human sleep stages into concrete network manipulation algorithms executing over the Cognee memory graph.

```
          [ Raw Episodic Graph ]
                     │
                     ▼
          ┌─────────────────────┐
          │  N1: Replay Stage   │ ◄── Ranked by Activation Score (Decay)
          └──────────┬──────────┘
                     │  Active working set
                     ▼
          ┌─────────────────────┐
          │ N2: Consolidation   │ ◄── Semantically grouped via DBSCAN
          └──────────┬──────────┘
                     │  Dense Clusters
                     ▼
          ┌─────────────────────┐
          │  N3: Pruning Stage  │ ◄── Duplicate Merges & Contradiction Resolution
          └──────────┬──────────┘
                     │  Cleaned Graph
                     ▼
          ┌─────────────────────┐
          │   REM: Abstraction  │ ◄── Ontological Synthesis (Concept Generation)
          └─────────────────────┘
```

---

## 2. Algorithmic Formulations

### 📊 N1 Stage: Replay (Weighted Activation Decay)
During Replay, memories are ranked by an activation score to determine which items enter the active consolidation working set. The activation $A_i$ of node $i$ decays exponentially over time:

$$A_i = (W_r \cdot R_i + W_f \cdot F_i + W_c \cdot C_i + W_i \cdot I_i) \cdot e^{-\lambda t}$$

Where:
*   $R_i$: **Recency score** (time elapsed since last access)
*   $F_i$: **Frequency score** (total access count)
*   $C_i$: **Graph centrality** (relative degree centrality of the node)
*   $I_i$: **Importance weight** (assigned during ingestion)
*   $\lambda$: **Decay rate** ($0.1$ default)

### 🧮 N2 Stage: Consolidation (DBSCAN Clustering)
Activated working nodes are projected into embedding spaces. A DBSCAN algorithm groups semantically close memories using cosine distance metrics:

$$\text{Distance}(u, v) = 1 - \frac{u \cdot v}{\|u\|_2 \|v\|_2}$$

*   **Epsilon ($\epsilon$)**: $0.25$ (maximum distance between nodes to form a cluster)
*   **Min Samples**: $1$ (allows isolated singleton memory clusters)

### ✂️ N3 Stage: Pruning (Duplicate Merge & Contradiction Resolution)
To optimize storage density and health, the system detects logical redundancies and conflicts:
*   **Auto-Merge**: Duplicate candidates with cosine similarity $\ge 0.995$ are merged directly.
*   **LLM Verification**: Candidates with similarity $\ge 0.90$ are dispatched to the Gemini Reasoning Engine for semantic duplicate checking.
*   **Contradiction Resolution**: Logical contradiction pairs are detected and resolved by pruning the logically invalid or older statement.

### 🔮 REM Stage: Abstraction (Ontology Synthesis & Latent Linking)
The system synthesizes new knowledge from clusters:
1.  **Concept Creation**: LLM abstracts experiences in a cluster, generating a new parent `Concept` node.
2.  **Abstraction Edges**: `ABSTRACTED_BY` relationship edges connect child memories to the new Concept.
3.  **Latent Topic Linking**: Pairs of Concepts are compared. If semantic similarity is $\ge 0.40$, an `ASSOCIATED_WITH` relationship is generated to link different topic clusters.

---

## 3. Thread-Safe Memory Synchronization

To prevent user interactions during sleep cycles from corrupting active graph consolidations, Oneiros implements a write-locking sync queue:

```
Sleep Cycle Initiated
         ↓
Provider Lock set (is_sleeping = True)
         ↓
User sends message ➔ Ingestion caught ➔ Temp ID queued (queued-xxxx)
         ↓
Sleep Stage processing runs uninterrupted on Cognee
         ↓
Sleep Cycle Complete
         ↓
Provider Lock released (is_sleeping = False)
         ↓
Queued memories flushed ➔ Processed sequentially in Cognee Cloud
```
