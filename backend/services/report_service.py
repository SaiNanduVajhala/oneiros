"""
Oneiros Services Layer - Report Service

Generates formatted summaries and reports of cognitive dream cycles for users.
"""

from typing import List
from domain.dream import DreamReport

class ReportService:
    """
    Service for formatting dream analytics and narratives.
    """
    @staticmethod
    def generate_markdown_report(report: DreamReport) -> str:
        """
        Creates a markdown presentation of a dream report.
        """
        stages_list = ", ".join(report.stages_completed)
        compression_percent = report.compression_ratio * 100.0
        
        md = []
        md.append(f"# Cognitive Dream Report: {report.dream_id}")
        md.append(f"**Date:** {report.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        md.append(f"**Cycle Duration:** {report.duration:.2f} seconds")
        md.append(f"**Stages Executed:** {stages_list}")
        md.append("")
        md.append("## Graph Consolidation Metrics")
        md.append(f"- **Nodes Evaluated:** {report.nodes_processed}")
        md.append(f"- **Low-Activation Nodes Pruned:** {report.nodes_removed}")
        md.append(f"- **New Semantic Abstractions:** {report.concepts_created}")
        md.append(f"- **Relationships Established:** {report.relationships_created}")
        md.append(f"- **Graph Compression:** {compression_percent:.1f}%")
        md.append("")
        md.append("## Health Transition")
        md.append(f"From a baseline of **{report.memory_health_before:.2f}**, the post-cycle substrate health was assessed at **{report.memory_health_after:.2f}**.")
        md.append("")
        md.append("## Metacognitive Summary Narrative")
        md.append(report.summary_narrative or "No details recorded.")
        
        return "\n".join(md)
