"""
Oneiros Sleep Subsystem - REM Abstraction Stage (REM)

Synthesizes high-level parent semantic concepts and discovers latent cross-cluster relationships.
"""

import uuid
import logging
from typing import List, Tuple, Dict, Any
from memory.provider import MemoryProvider
from domain.memory import MemoryGraphSnapshot, MemoryNode, MemoryEdge, SemanticConcept
from kernel.reasoning.llm import ReasoningEngine
from kernel.algorithms.similarity import compute_cosine_similarity

logger = logging.getLogger("oneiros.kernel.sleep.rem")

class REMStage:
    """
    REM Sleep Stage: Prompts semantic abstractions and links cross-cluster latent relationships.
    """
    def __init__(self, provider: MemoryProvider, reasoning_engine: ReasoningEngine):
        self.provider = provider
        self.reasoning_engine = reasoning_engine

    async def execute(
        self,
        snapshot: MemoryGraphSnapshot,
        clusters: List[List[MemoryNode]]
    ) -> Tuple[MemoryGraphSnapshot, List[str]]:
        """
        Creates semantic concepts for each cluster, discovers latent links, and returns the enriched snapshot.
        """
        logger.info("Executing REM Stage (Semantic Abstraction & Latent Linking)...")
        timeline_events = []
        
        new_nodes: List[MemoryNode] = []
        new_edges: List[MemoryEdge] = []

        if not clusters:
            logger.info("No clusters available for REM processing.")
            return snapshot, timeline_events

        # Track already synthesized concept labels to prevent duplicates within the same cycle
        label_to_id: Dict[str, str] = {}

        # --- 1. Synthesize Parent Concepts ---
        for idx, cluster in enumerate(clusters):
            contents = [node.content for node in cluster]
            cluster_text = "\n".join([f"- {c}" for c in contents])

            system_prompt = (
                "You are the REM sleep stage of a cognitive memory graph system. Your objective is "
                "to perform abstraction and synthesize NEW knowledge from the provided experience statements."
            )
            
            user_prompt = (
                f"Experiences in this memory cluster:\n{cluster_text}\n\n"
                "Formulate a new abstract parent concept that generalizes these experiences.\n"
                "Your output must be a JSON object with keys:\n"
                "- 'label': A short, clear name for this concept (e.g. 'High Performance GPU Programming')\n"
                "- 'description': An explanation of this general concept and why it abstracts these nodes\n"
                "- 'confidence': A confidence score between 0.0 and 1.0\n"
                "- 'semantic_tags': A list of string category tags"
            )
            
            try:
                result = await self.reasoning_engine.generate_structured_response(system_prompt, user_prompt)
                
                label = result.get("label", f"Concept Cluster {idx}").strip()
                description = result.get("description", "Abstract generalization of experience cluster.")
                confidence = float(result.get("confidence", 0.85))
                tags = result.get("semantic_tags", ["abstraction"])
                
                label_key = label.lower()
                if label_key in label_to_id:
                    concept_id = label_to_id[label_key]
                    timeline_events.append(f"Linked cluster experiences to existing concept '{label}'")
                    # Update explanation logs for the existing node
                    for node in new_nodes:
                        if node.id == concept_id:
                            node.explain_log.append(f"Linked additional experiences: {', '.join([n.id for n in cluster])}")
                            break
                else:
                    concept_id = f"concept-{str(uuid.uuid4())[:8]}"
                    label_to_id[label_key] = concept_id
                    
                    explain_msg = f"Synthesized during REM to abstract: {', '.join([n.id for n in cluster])}. Rationale: {description}"
                    
                    concept_node = MemoryNode(
                        id=concept_id,
                        content=f"{label}: {description}",
                        source="sleep",
                        importance=confidence,
                        semantic_tags=tags,
                        explain_log=[explain_msg]
                    )
                    new_nodes.append(concept_node)
                    timeline_events.append(f"Created concept '{label}' to abstract {len(cluster)} experiences")
                
                # Create edges linking the source nodes to the new concept
                for source_node in cluster:
                    edge = MemoryEdge(
                        source=source_node.id,
                        target=concept_id,
                        type="ABSTRACTED_BY",
                        weight=0.8
                    )
                    new_edges.append(edge)
                    
                # Sync back to the database provider
                try:
                    await self.provider.improve(label, description, confidence)
                except NotImplementedError:
                    pass  # Stub fallback
            except Exception as e:
                logger.error(f"Error synthesizing concept for cluster {idx}: {e}")

        # --- 2. Discover Latent Cross-Cluster Relationships ---
        # Compare all synthesized concepts pairwise
        all_concepts = [n for n in new_nodes if n.source == "sleep"]
        n_concepts = len(all_concepts)
        
        for i in range(n_concepts):
            for j in range(i + 1, n_concepts):
                concept_a = all_concepts[i]
                concept_b = all_concepts[j]
                
                # If embeddings exist, calculate cosine similarity
                if concept_a.embedding and concept_b.embedding:
                    sim = compute_cosine_similarity(concept_a.embedding, concept_b.embedding)
                else:
                    # Simple text overlap token similarity for local fallback
                    words_a = set(concept_a.content.lower().split())
                    words_b = set(concept_b.content.lower().split())
                    common = words_a.intersection(words_b)
                    sim = len(common) / max(1, min(len(words_a), len(words_b)))
                
                if sim >= 0.40:
                    # Cross-cluster topic association discovered!
                    edge = MemoryEdge(
                        source=concept_a.id,
                        target=concept_b.id,
                        type="ASSOCIATED_WITH",
                        weight=float(sim),
                        metadata={"origin": "latent_linking", "similarity": sim}
                    )
                    new_edges.append(edge)
                    
                    label_a = concept_a.content.split(":")[0]
                    label_b = concept_b.content.split(":")[0]
                    timeline_events.append(f"Linked concept '{label_a}' ↔ '{label_b}' (Latent association: {sim:.2f})")

        # --- 3. Build Enriched Snapshot ---
        enriched_nodes = snapshot.nodes + new_nodes
        enriched_edges = snapshot.edges + new_edges
        
        updated_snapshot = MemoryGraphSnapshot(nodes=enriched_nodes, edges=enriched_edges)
        
        logger.info(f"REM complete. Created {len(new_nodes)} concepts and {len(new_edges)} abstraction edges.")
        return updated_snapshot, timeline_events
