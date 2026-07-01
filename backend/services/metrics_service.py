"""
Oneiros Services Layer - Metrics Service

Calculates analytical performance aggregates from historical dream reports.
"""

import logging
from typing import List, Dict, Any, Optional
from domain.dream import DreamReport

logger = logging.getLogger("oneiros.services.metrics_service")

class MetricsService:
    """
    Service for analyzing historical metrics of the Cognitive OS sleep cycles.
    """
    @staticmethod
    def calculate_aggregates(reports: List[DreamReport]) -> Dict[str, Any]:
        """
        Computes aggregates (averages and sums) over a list of dream reports.
        """
        if not reports:
            return {
                "total_cycles": 0,
                "avg_duration": 0.0,
                "total_nodes_processed": 0,
                "total_nodes_removed": 0,
                "total_concepts_created": 0,
                "avg_compression_ratio": 0.0,
                "health_trend": 0.0
            }

        total_cycles = len(reports)
        sum_duration = sum(r.duration for r in reports)
        sum_processed = sum(r.nodes_processed for r in reports)
        sum_removed = sum(r.nodes_removed for r in reports)
        sum_concepts = sum(r.concepts_created for r in reports)
        sum_compression = sum(r.compression_ratio for r in reports)
        
        # Calculate health trends based on latest report minus first report
        health_trend = reports[-1].memory_health_after - reports[0].memory_health_before

        return {
            "total_cycles": total_cycles,
            "avg_duration": sum_duration / total_cycles,
            "total_nodes_processed": sum_processed,
            "total_nodes_removed": sum_removed,
            "total_concepts_created": sum_concepts,
            "avg_compression_ratio": sum_compression / total_cycles,
            "health_trend": health_trend
        }
