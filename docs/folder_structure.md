# Oneiros Directory Structure & Architecture Manifest

This manifest documents the modular directory structure and file contents for the **Oneiros Cognitive Memory Operating System Kernel** (v2). The codebase is designed around **Dependency Inversion** and clear separation of concerns.

---

## Folder Structure Layout

```
oneiros/
├── requirements.txt           # Python dependency lists
├── README.md                  # Main project introduction
│
├── docs/                      # Technical documentation and plans
│   ├── folder_structure.md    # [THIS FILE] Project layout manifest
│   ├── development-log.md     # 7-day development progress roadmap log
│   ├── cognitive_research_validation.md # Algorithmic parameters & calculations
│   └── walkthrough.md         # Walkthrough instructions for judges
│
├── frontend/                  # Independent React / Vite / TypeScript Frontend
│   ├── src/
│   │   ├── components/        # Frontend visual component modules
│   │   │   ├── DevConsolePage.tsx # Developer console dashboard
│   │   │   ├── DevConsolePage.css # DevConsolePage styling sheets
│   │   │   ├── GraphViewport.tsx  # Force-directed network graphs (2D/3D toggle)
│   │   │   ├── GraphViewport.css  # Graph styling, toggles, confirmation overlays
│   │   │   ├── AgentConsole.tsx   # Chat console inputs and memories tab lists
│   │   │   └── ... (other layout components)
│   │   ├── hooks/
│   │   │   └── useDreamState.ts   # Core UI state managers & API fetching hooks
│   │   └── App.tsx            # App container with routing to dev console
│   └── ... (Vite/TypeScript setup files)
│
└── backend/                   # FastAPI and Cognitive Operating System
    ├── app.py                 # Application bootstrapper and DI wiring
    ├── config.py              # Configuration & factory for CogneeCloudProvider
    │
    ├── api/                   # Controller router layers
    │   ├── chat.py            # Conversational REST & delete endpoints
    │   ├── dream.py           # Sleep cycle triggers & SSE broadcasts
    │   └── debug.py           # Comprehensive developer diagnosis API controllers
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
    ├── utils/                 # Standard utilities and helper scripts
    │   ├── logger.py          # Standard project logger configuration
    │   └── embedding_utils.py # String normalization & token size calculations
    │
    ├── infrastructure/        # Third-party adapters and registry configurations
    │   ├── cognee_client.py   # Cognee Cloud authentication & connect clients
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
    │   │   └── llm.py         # ReasoningEngine orchestrator
    │   │
    │   └── sleep/             # Sleep Stages & cycle coordinators
    │       ├── coordinator.py # Sleep coordinator & cognitive memory gates
    │       ├── replay.py      # N1 Replay - Active Working Set builder
    │       ├── consolidation.py # N2 Consolidation - Connected components clustering
    │       ├── pruning.py     # N3 Pruning - Duplicate merge & contradictions resolver
    │       └── rem.py         # REM Abstraction - Semantic concept generation
    │
    └── tests/                 # Unit and integration test suites
        ├── test_memory.py     # Verifies provider exceptions
        ├── test_events.py     # Verifies EventBus pub/sub actions
        ├── test_sleep.py      # Verifies SleepCoordinator cycle sequences
        ├── test_debug_api.py  # Verifies new Developer API controllers
        └── test_api.py        # Verifies FastAPI endpoint health paths
```
