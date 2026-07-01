# Oneiros Directory Structure & Architecture Manifest

This manifest documents the modular directory structure and file contents for the **Oneiros Cognitive Memory Operating System Kernel** (v2). The codebase is designed around **Dependency Inversion** and clear separation of concerns.

---

## Folder Structure Layout

```
oneiros/
├── requirements.txt           # Python dependency lists
├── README.md                  # Main project introduction
│
├── docs/
│   └── folder_structure.md    # [THIS FILE] Project layout manifest
│
├── frontend/                  # Independent React / Vite / TypeScript Frontend
│
└── backend/                   # FastAPI and Cognitive Operating System
    ├── app.py                 # Application bootstrapper and DI wiring
    ├── config.py              # Configuration & factory for CogneeCloudProvider
    │
    ├── api/                   # Controller router layers
    │   └── chat.py            # Conversational REST controller
    │
    ├── domain/                # Strongly-typed business models (DTOs)
    │   ├── memory.py          # MemoryNode, MemoryEdge, SemanticConcept schemas
    │   ├── graph.py           # Visualizer graph schemas
    │   ├── dream.py           # DreamReport schemas
    │   ├── metrics.py         # DreamMetrics and ActivationScore schemas
    │   └── stages.py          # SleepStage models
    │
    ├── events/                # Internal publish-subscribe event system
    │   ├── events.py          # Unified Event telemetry schema
    │   └── event_bus.py       # Asynchronous event dispatcher bus
    │
    ├── services/              # Business operations services layer
    │   ├── graph_service.py   # Processes graph layout formatting
    │   ├── dream_service.py   # Coordinates sleep executions and histories
    │   ├── metrics_service.py # Aggregates dream execution telemetry
    │   └── report_service.py  # Generates readable summary reports
    │
    ├── utils/                 # Standard utilities and helper scripts
    │   ├── logger.py          # Standard project logger configuration
    │   ├── graph_helpers.py   # Helper methods for graph-level operations
    │   ├── timers.py          # Operation execution timer helpers
    │   └── embedding_utils.py # String normalization & token size calculations
    │
    ├── infrastructure/        # Third-party adapters and registry configurations
    │   ├── cognee/            # Cognee Cloud authentication adapters
    │   ├── gemini/            # Model parameters and LLM call clients
    │   ├── websocket/         # WebSocket managers for real-time broadcasts
    │   └── configuration/     # System settings and global DI registries
    │
    ├── memory/                # Memory abstraction layer
    │   ├── provider.py        # Abstract base class MemoryProvider
    │   └── cognee_cloud_provider.py # Cognee Cloud adapter driver
    │
    ├── kernel/                # Cognitive orchestrator kernel packages
    │   ├── wake/
    │   │   └── agent.py       # WakeAgent conversation workflow controller
    │   │
    │   ├── reasoning/         # Prompt engineering and LLM delegation
    │   │   ├── llm.py         # ReasoningEngine orchestrator
    │   │   ├── context_builder.py # Context assembly maps
    │   │   └── prompts.py     # System instructions and prompt templates
    │   │
    │   ├── sleep/             # Sleep Stages & cycle coordinators
    │   │   ├── coordinator.py # Main sleep coordinator
    │   │   ├── replay.py      # N1 Replay - Active Working Set builder
    │   │   ├── consolidation.py # N2 Consolidation - Connected components clustering
    │   │   ├── pruning.py     # N3 Pruning - Activation decay scoring
    │   │   └── rem.py         # REM Abstraction - Semantic concept generation
    │   │
    │   └── scheduler/         # Dream cycle threshold scheduling
    │       ├── scheduler.py   # Main scheduling loop
    │       ├── triggers.py    # Trigger rule evaluations
    │       └── policies.py    # Safe state boundary validators
    │
    └── tests/                 # Unit and integration test suites
        ├── test_memory.py     # Verifies provider stub exceptions
        ├── test_events.py     # Verifies EventBus pub/sub actions
        ├── test_sleep.py      # Verifies SleepCoordinator cycle sequences
        └── test_api.py        # Verifies FastAPI endpoint health paths
```
