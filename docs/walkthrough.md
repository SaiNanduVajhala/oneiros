# Oneiros Visualization Dashboard Walkthrough (WeMakeDevs Cognee Hackathon)

> [!NOTE]
> This document serves as the official project walkthrough submission for the [WeMakeDevs Cognee Hackathon](https://www.wemakedevs.org/hackathons/cognee), detailing our architecture decisions and stage achievements.

We have successfully designed, built, and verified the visualization and explainability layers for the **Oneiros Cognitive Memory Operating System**. The dashboard shifts Oneiros from an engine to a transparent, inspectable cognitive console.

---

## 1. Five-Panel Responsive Dashboard Layout

The interface is structured in a responsive 3-column / 2-row CSS grid mapping out the lifecycle of the system:
1.  **Agent Console (Wake Phase)**: Standard chat interface enabling interactive conversation with the Wake Agent. Shows generated memories and simulated cognitive fatigue.
2.  **Graph Viewport (Cognitive Graph)**: Canvas-based rendering engine using force-directed particle positioning. Animates stage actions (replay glows, cluster drift, duplicate fades, concept expands) driven entirely by VisEvents.
3.  **Dream Replay (Structured Timeline)**: Streaming timeline of stage-specific cards detailing executed algorithms, input counts, and output counts.
4.  **Metrics Dashboard**: 12 algorithm-derived diagnostic metrics (e.g., Activation Threshold, Compression Ratio, Semantic Cohesion, Contradictions Resolved) with animated counters.
5.  **Cognitive MRI (Radial Diagnostic Gauge)**: Instant visual representation of graph health, density, fragmentation, and cohesion using a Canvas radial meter.

---

## 2. Structured, Immutable Telemetry (VisEvents)

The backend now logs and emits structured `VisEvent` dicts over Server-Sent Events (SSE) via the EventBus:
*   **Decoupled & Immutable**: Each event is a serialized historic fact. The frontend acts purely as a renderer, eliminating duplicate cognitive logic.
*   **Visualization Instructions**: Events explicitly specify transition rules (`node_activate`, `cluster_form`, `node_merge`, `concept_create`, `edge_create`).

---

## 3. Cognitive Scrubber Playback (Scrubber)

We implemented stage-by-stage temporal scrubbing playback:
*   **Historical Snapshots**: The backend captures complete `StageSnapshot` objects after N1 Replay, N2 Consolidation, N3 Pruning, and REM stages.
*   **Temporal Exploration**: Users can drag the playback slider to view the visual layout and metric values at any past step, transitioning seamlessly between chronological stages of the sleep cycle.

---

## 4. Algorithmic Trace Explainability

Clicking on any node, metric, or timeline event opens the **Explain Panel**:
*   **Trace Visualization**: Renders clear **Input → Algorithm → Output** flows.
*   **Trace Example**: Shows exact algorithm parameters (e.g., `DBSCAN (eps=0.25, metric=cosine)`), node counts, and detailed transition logs.
*   **Audit logs**: Lists explain_log reasons why a node was pruned or merged.

---

## 5. Architectural Polish & Refinements

Based on the architecture review, the following enhancements have been integrated:
*   **Unified StageSnapshot**: Extended the domain models to encapsulate all events, metrics, and algorithm traces for each stage cleanly.
*   **Stable Deterministic Layout**: Eliminated random velocity drifts from the Canvas rendering loop. Node layouts are now calculated deterministically and interpolate smoothly toward their target positions during stages like consolidation.
*   **Cognitive MRI Diagnostics**: Added a dynamic diagnostic evaluation status badge (`HEALTHY` / `WARNING` / `CRITICAL`) with detailed reasons explaining the memory health state.
*   **Node Decision Details**: Exposed detailed execution weights, counts, and action rationales inside the inspect panel.

---

## 6. Verification Check

All backend pytest tests and frontend Vite typescript compilations compile and execute cleanly:
*   `python -m pytest backend/tests/ -v` → **6 Passed**
*   `npm run build` → **Flawless Compile** (`dist/assets/index.js` created successfully)

---

## 7. Phase 4 — Core Cognee Integration & Storytelling Frontend Redesign

We have successfully refined the codebase to enforce **Cognee as the single source of truth** for memory, eliminating duplicate relational stores and redesigning the frontend around storytelling.

### 7.1 Thin Adapter Architecture (No Duplicate SQLite Memories)
*   **Decoupled Database**: Removed the `nodes` and `edges` memory tables from the SQLite database completely.
*   **Direct Provenance Queries**: The `LocalCogneeProvider.get_graph_data()` method now calls `cognee.get_memory_provenance_graph(include_memory=True)` natively to query and project nodes and edges directly from local Cognee.
*   **Isolated Metadata**: Local SQLite (`local_brain.db`) is now restricted purely to storing visual coordinate layouts (`node_positions` table) to cache stable node positioning, adhering to the Single Responsibility Principle.
*   **Dynamic Sleep Syncing**: At the end of the sleep consolidation cycle, the final consolidated `MemoryGraphSnapshot` is written back directly to the provider (`save_graph_snapshot`), prompting `cognee.forget()` to prune deleted nodes from the real memory substrate.

### 7.2 Narrative Storytelling Frontend (Redesigned Layout)
*   **3-Column Storytelling Grid**: Collapsed the layout into a clean, narrative-focused 3-column workspace:
    1.  **Column 1**: Wake Agent Chat Console.
    2.  **Column 2**: Memory Graph Viewport (with scrubber playback).
    3.  **Column 3**: Dream Replay Timeline (Top) + Memory Health & Story Diagnostics (Bottom).
*   **Removed Unused Components**: Deleted the `MetricsDashboard` panel and styles, removing confusing engineering metrics (e.g. Graph Density, Average Degree) that distract from the user story.
*   **Consolidation Narrative Card**: Redesigned `CognitiveMRI` to act as the primary narrative diagnostic card, displaying the radial health gauge, active state, the real text summary from `report.summary_narrative`, and clean story metrics:
    *   **Memory Health Target** (Initial % → Final %)
    *   **Redundant Merges**
    *   **Logical Conflicts Resolved**
    *   **Abstract Concepts Synthesized**
    *   **Active Working Nodes**

### 7.3 Compilation & Test Verification
*   `python -m pytest backend/tests/` → **7 Passed** successfully.
*   `npm run build` → Compiled with **0 errors and 0 warnings** into production asset bundles.

### 7.4 Environment Configuration & Cloud Readiness
*   **Tracked env.example Contract**: Created [.env.example](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/.env.example) containing all settings, backend host bindings, and empty placeholders for future Cognee Cloud credentials.
*   **Local configuration persistence**: Created local [.env](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/.env) to manage local API keys and vector storage options.
*   **Git ignore enforcement**: Created [.gitignore](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/.gitignore) ignoring local credentials (`.env`), python cached artifacts (`__pycache__/`, `*.pyc`), environments (`.venv/`), and database files (`backend/data/*.db`).
*   **Configuration Isolation**: Updated [settings.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/infrastructure/configuration/settings.py) using `load_dotenv` to resolve the root workspace `.env` file robustly. Configured [cognee_local_provider.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/memory/cognee_local_provider.py) to initialize its path directly from settings database path variables.

---

## 8. Phase 5 — High-Fidelity Stitch UI Integration

We successfully integrated the Stitch screens assets, incorporating state-of-the-art interactive WebGL backgrounds and Three.js 3D cognitive graphs.

### 8.1 WebGL Synaptic Shader Background
*   **Shader Canvas Background**: Created the [ShaderBackground.tsx](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/frontend/src/components/ShaderBackground.tsx) component, rendering a full-screen WebGL canvas layer in the background. It executes the custom GLSL fragment shader displaying synaptic particle pulses, grid lines, and interactive mouse-reactive lighting.

### 8.2 Three.js 3D Memory Network Viewport
*   **3D Network Nodes**: Replaced the 2D canvas in [GraphViewport.tsx](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/frontend/src/components/GraphViewport.tsx) with a full-fledged Three.js scene. 
*   **Spatial Styling**: Rendered episodic memories as floating glowing spheres (`THREE.SphereGeometry`) and concept abstract classes as 3D hexagonal prisms (`THREE.CylinderGeometry` with 6 radial segments).
*   **Smooth State Morphing**: Rather than destroying and recreating graph elements, the viewport preserves the 3D meshes and smoothly interpolates (lerps) their positions toward updated coordinates (or cluster centers), grows concept nodes, and scales active glows over animation ticks.
*   **Edge Drawing**: Links (edges) are drawn dynamically using connected line segments that attach to nodes, adjusting their length, position, and opacity in real time.
*   **3D Raycast Tooltips**: Implemented hover raycasting to display custom meta-tooltips and trigger selection panels. Enabled mouse rotation (drag to rotate the camera around the network space) and wheel-based zooming.

### 8.3 Dual-State Layout Synchronization (Awake vs. Dreaming)
*   **State-Driven Structure**: Updated [App.tsx](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/frontend/src/App.tsx) and [App.css](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/frontend/src/App.css) to switch layouts:
    *   **Awake State Layout**: Features a left side navigation panel, a dedicated Wake Agent console, a large graph viewport rendering on the screen background, and the live event log column on the right.
    *   **Dreaming State Layout**: Adjusts to a centered Three.js network console, with scrubber timeline playback control on the bottom, live consolidation logs on the left, and explain mode/Cognitive MRI gauges on the right.

### 8.4 Verification Checks
*   **Test Status**: All 7 backend tests pass.
*   **Vite Bundle Build**: `npm run build` succeeds with 0 errors and warnings.

---

## 9. Phase 9 — Cognee Cloud Migration & Clean Architecture Boundary

We migrated the memory layer backend to **Cognee Cloud** while establishing a clean separation of concerns and thread-safe write synchronization during sleep cycles.

### 9.1 Connection Lifecycle & Infrastructure Client
*   **CogneeClient**: Created [cognee_client.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/infrastructure/cognee_client.py) in the infrastructure layer to wrap authentication, connection status, retry handling, and raw SDK API operations.
*   **Constructor Injection**: Injected `CogneeClient` into [cognee_cloud_provider.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/memory/cognee_cloud_provider.py) at startup via [settings.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/infrastructure/configuration/settings.py). The provider is now a thin adapter responsible only for model mapping and domain logic.
*   **Optional COGNEE_BASE_URL**: Treated the cloud base URL as optional, allowing the Cognee SDK to resolve its default cloud endpoint automatically, while requiring `COGNEE_API_KEY`.
*   **Fail-Fast Validations**: Added validation checks in [settings.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/infrastructure/configuration/settings.py) to raise a clear `ValueError` at startup if `ONEIROS_PROVIDER=cloud` is selected without a valid key.

### 9.2 Memory Synchronization (Option A - Write Locking & Queueing)
*   **Mutation Locking**: Extended the base `MemoryProvider` in [provider.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/memory/provider.py) to support sleep states (`is_sleeping()`).
*   **Queueing & Replay**: During sleep stage consolidation, write operations (`remember`) from user messages are intercepted, assigned a temporary ID (`queued-...`), and stored in an in-memory queue.
*   **Post-Sleep Flush**: Once [coordinator.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/kernel/sleep/coordinator.py) completes the sleep cycle execution, the lock is released, and queued writes are sequentially replayed against the database substrate.

### 9.3 Incremental Mutations (No Full Graph Overwrites)
*   **Incremental Deletion**: Replaced complete graph writes in `save_graph_snapshot()` with incremental deletions. Obsolete nodes are deleted via `forget()` commands. Layout visual coordinates continue caching in local SQLite SQLite db tables securely.
*   **Dynamic Abstractions**: Subsystem stages create entities and ontology structures by calling `remember()`, `improve()`, and `forget()` incrementally.

### 9.4 Verification Check
*   **Mocked Unit Tests**: Updated [test_memory.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/tests/test_memory.py) to mock client SDK calls, testing parameter mapping, write queueing, and fail-fast checks offline.
*   **Live Integration Suite**: Configured optional integration tests against the live Cognee Cloud endpoint that execute automatically if keys are in the local workspace environment, and skip cleanly otherwise.
*   **Test Success**: Run `python -m pytest backend/tests/` confirming **9/9 tests pass successfully** (including sleep coordinator algorithm suites).

---

## 10. Phase 10 — Backend Audit, Refactoring & Cleanup Optimization

We performed a comprehensive evidence-driven project-wide reference audit, removing dead abstractions and securing critical concurrency locks.

### 10.1 Dead Code & Obsolete Abstractions Purged
*   **Services Layer**: Deleted the entire `backend/services` package (including `dream_service.py`, `graph_service.py`, `metrics_service.py`, and `report_service.py`), resolving direct API projections.
*   **Obsolete Domain Models**: Deleted `stages.py`, `metrics.py`, and `graph.py` from `backend/domain/`.
*   **Duplicate Infrastructure**: Deleted the old duplicate `backend/infrastructure/cognee` client stubs and the unused `backend/infrastructure/websocket` manager.
*   **Unused Utilities**: Deleted `timers.py` and `graph_helpers.py` from `backend/utils/`.
*   **Empty Folders**: Deleted empty placeholder directories `backend/static` and `backend/models`.

### 10.2 Clean Packaged Exports
*   Updated package definitions in [backend/domain/\_\_init\_\_.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/domain/__init__.py) and [backend/utils/\_\_init\_\_.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/utils/__init__.py) to remove all imports from deleted files, maintaining a clean package API boundary.

### 10.3 Concurrency Protection (asyncio.Lock)
*   Initialized `self._lock = asyncio.Lock()` inside [coordinator.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/kernel/sleep/coordinator.py) constructor.
*   Wrapped the sleep cycle execution inside `async with self._lock:` inside `execute_cycle()`. Checked `self._lock.locked()` to raise a descriptive `RuntimeError` if a duplicate execution is triggered, guaranteeing coroutine-safe operations.

### 10.4 Compilation & Verification
*   **Pytest Status**: Executed `python -m pytest backend/tests/` confirming **9/9 tests pass successfully** with 0 syntax errors or circular import dependencies.
*   **Git Synchronized**: Staged, committed, and pushed the clean audited backend modifications directly to the remote GitHub `main` branch.

---

## 11. Phase 11 — Cognee Cloud Exclusive Migration (Single Source of Truth)

We removed the local SQLite and LanceDB provider fallbacks completely, solidifying Cognee Cloud as the single, permanent database substrate for Oneiros.

### 11.1 Deletion of Local Provider
*   Deleted the redundant [cognee_local_provider.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/memory/cognee_local_provider.py) module.

### 11.2 Unconditional Cloud Binding
*   Refactored [settings.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/infrastructure/configuration/settings.py) to always instantiate and bind `CogneeCloudProvider` unconditionally on boot.
*   Enforced fast-fail startup check: if `COGNEE_API_KEY` is not set or set to a placeholder, the server will raise a `ValueError` on startup and prevent initialization.
*   Removed `ONEIROS_PROVIDER` flags from [.env](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/.env) and [.env.example](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/.env.example).

### 11.3 Integration Mock Testing
*   Refactored [test_api.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/tests/test_api.py) to use FastAPI's dependency overrides (`app.dependency_overrides`) mapping the provider to a mock class, ensuring health checks execute 100% offline.
*   Refactored [test_sleep.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/tests/test_sleep.py) and [test_memory.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/tests/test_memory.py) to remove local provider tests and mock the cloud client calls. All **8/8 offline tests pass successfully**.

---

## 12. Phase 12 — Backend Workspace Cleanup & CORS Robustness

We performed a deep-cleaning audit of the backend directory structure, removing dead/orphan modules, untracking generated SQLite binaries from source control, and ensuring development port robustness.

### 12.1 Dead Module Deletions
*   Deleted `backend/kernel/scheduler/` directory (`scheduler.py`, `triggers.py`, and `policies.py`) which contained unused background scheduling cron runners.
*   Deleted the empty placeholder directory `backend/kernel/memory/`.
*   Removed the duplicate database file `backend/data/local_brain.db` (which was a legacy database path).

### 12.2 Scratch File Deletions
*   Removed redundant scratch test scripts under the root `scratch/` directory (`check_env.py`, `test_cognee_serve.py`, and `test_cognee_sync.py`), keeping only core automated test files in `backend/tests/`.

### 12.3 Database Untracking & Ignoring
*   Untracked the visual layout coordinate database file `backend/infrastructure/data/local_brain.db` from Git history using `git rm --cached`.
*   Configured `.gitignore` with `backend/**/*.db` to prevent local cache databases from being committed or causing merge conflicts during evaluation.

### 12.4 Port Robustness (CORS allowed origins)
*   Updated [app.py](file:///c:/Users/nagendra%20prasad/Downloads/oneiros/backend/app.py) CORS permissions list to allow connection origins from ports `5174` and `5175` to support smooth frontend dashboard interactions when Vite dynamically binds to alternative ports.

---

## 13. WeMakeDevs Cognee Hackathon Disclosures
*   **AI Assistant Declaration**: Built using Google DeepMind's **Antigravity AI coding assistant** to co-author, debug, audit, and clean the repository structures.





