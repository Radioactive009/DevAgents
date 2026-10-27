# DevAgents — Complete Autonomous Multi-Agent Software Engineering Platform

DevAgents is a research-oriented autonomous software engineering platform that accepts a high-level requirement and independently carries out the full software development lifecycle: requirement decomposition, architecture planning, multi-file code generation, isolated execution, testing, automated failure classification, root-cause diagnosis, AST source code patching, retesting, evidence-based verification, and live interactive web application preview.

---

## 1. Research Problem & Motivation
Does a structured multi-agent software-engineering workflow improve the functional correctness, debugging performance, and requirement coverage of LLM-based software development compared with a single-agent LLM baseline?

### Primary Research Questions
- **RQ1:** Does a structured multi-agent software engineering workflow (`Supervisor -> Architecture -> Coding -> Testing -> Debugging -> Verification`) achieve higher functional correctness and test pass rates than a single-agent baseline with iterative feedback?
- **RQ2:** Do project-specific retrieval-augmented generation (RAG) and persistent project memory improve requirement coverage and reduce redundant debugging iterations across runs?
- **RQ3:** Does integrating hybrid failure classification (rule-based + ML) improve root-cause diagnosis and automated bug-fix success?

---

## 2. System Architecture & Workflow

DevAgents implements a robust six-agent orchestration pipeline with shared `ProjectState`:

```
User Requirement
       ↓
[SupervisorAgent]  -->  Decomposes requirements, generates testable plan & acceptance criteria
       ↓
[ArchitectureAgent] -->  Designs components, interfaces, file mappings & tech stack
       ↓
(Optional Human Approval Checkpoint) --> Interactive Pause: Approve / Reject with Feedback
       ↓
[CodingAgent]       -->  Generates multi-file project source code with AST & syntax validation
       ↓
[TestingAgent]      -->  Executes real code in LocalProcessSandbox or DockerSandbox
       ↓
    [Failed?] ----Yes----> [DebuggingAgent]  -->  Diagnoses failure, generates & applies real patch
       ^                         |
       |                         | (Retest Loop - bounded retries)
       +-------------------------+
       ↓ No (Tests Passed or Max Retries)
[VerificationAgent] -->  Verifies implementation against execution evidence (VERIFIED / INCOMPLETE / FAILED)
       ↓
[Telemetry & Observability] --> Logs metrics, events, and diffs to JSONL; feeds Live Dashboard
```

---

## 3. Supported Languages & Multi-Language Execution
- **Python**: Full execution support, `pytest` test runner, virtual environment and dependency target isolation, traceback parsing.
- **JavaScript & TypeScript (Node.js)**: `package.json` detection, `npm install`, test execution via `node --test`, `Vitest`, or `Jest`, production build verification, and JS/TS source patching.
- **Web Applications**: Auto-detection of HTML/JS/CSS entrypoints with sandboxed live preview in dashboard.

---

## 4. Key Capabilities & Phases

### Phase 1: Six-Agent Workflow & Baseline
- Supervisor, Architecture, Coding, Testing, Debugging, and Verification agents.
- `SingleAgentBaseline` for controlled scientific comparison.

### Phase 2: Multi-Language Execution Engine
- `LocalProcessSandbox` (with Windows/Linux executable path resolution) and `DockerSandbox`.
- Timeout enforcement, execution resource boundaries, and isolation.

### Phase 3: Live Web Application Preview
- Serving generated web applications via `/api/runs/{run_id}/preview/{file}`.
- Dashboard iframe embedding with reload controls and entrypoint auto-detection.

### Phase 4: Context Optimization for Large Projects
- `ContextOptimizer` extracts relevant files from failure stack traces.
- Diff-based prompt formulation across debugging cycles reduces context token usage by up to 60-80% on multi-file repositories.

### Phase 5: Optional Human Approval Checkpoint
- When enabled, execution pauses after ArchitectureAgent.
- Review components, dependencies, and file structures.
- Approve or reject via UI buttons or `POST /api/runs/{run_id}/approve`.

### Phase 6 & 7: RAG Context & Project Memory
- Document chunking, TF-IDF / vector retrieval (`RAGPipeline`, `Retriever`).
- Persistent episodic memory (`ProjectMemory`) storing validated conventions and fixes across runs.

### Phase 8 & 9: Research Configurations & Empirical Benchmark
Four reproducible configurations:
1. `SINGLE_AGENT_BASELINE`
2. `MULTI_AGENT`
3. `MULTI_AGENT_RAG`
4. `MULTI_AGENT_RAG_MEMORY`

Quantitative evaluation metrics: functional correctness, test pass rate, bug fix success rate, requirement coverage, debug iterations, execution latency, and token consumption.

### Phase 10: Hybrid Failure Classification
- Rule-based diagnostics + `TfidfVectorizer` and `LogisticRegression` ML classifier.
- Categorizes errors into: `SYNTAX_ERROR`, `ASSERTION_FAILURE`, `TYPE_ERROR`, `DEPENDENCY_ERROR`, `BUILD_ERROR`, `TIMEOUT_ERROR`, `LOGIC_ERROR`, `INFRASTRUCTURE_ERROR`.

### Phase 11: Security & Robustness
- Workspace path traversal protection (`..`, absolute paths blocked).
- Protected file write guards (`.env`, `.git`).
- API key and secret scrubbing across all logs and prompt contexts.

---

## 5. Quick Start & Startup Commands

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### Installation
```bash
# Clone the repository
git clone https://github.com/Radioactive009/DevAgents.git
cd DevAgents

# Install Python dependencies
pip install -r requirements.txt

# Install Frontend dependencies
cd ui
npm install
cd ..
```

### Environment Configuration
Copy `.env.example` to `.env` and set your preferred provider keys:
```env
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
```
*(Deterministic mock mode is supported out-of-the-box without API keys)*

### Running Backend API Server
```bash
py -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Running Frontend Dashboard
```bash
cd ui
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### Running CLI Demo
```bash
# Run with Mock Provider
py run_demo_cli.py --provider mock

# Run with Groq Provider
py run_demo_cli.py --provider groq --model openai/gpt-oss-120b

# Run with Gemini Provider
py run_demo_cli.py --provider gemini --model gemini-2.0-flash
```

### Running Automated Test Suite
```bash
# Python backend tests
py -m pytest

# Frontend React/Vite tests
cd ui
npm test
npm run build
```

### Running Empirical Research Evaluation
```bash
py experiments/run_research_evaluation.py
```

---

## 6. Project Directory Structure
```
DevAgents/
├── agents/             # AI agent implementations (Supervisor, Arch, Code, Test, Debug, Verify, Baseline)
├── api/                # FastAPI backend endpoints (runs, events, preview, approval)
├── benchmarks/         # Benchmark adapters (SWE-bench, dataset ingestion)
├── configs/            # Configuration protocols and task manifests
├── evaluation/         # Metrics and hybrid failure classification
├── execution/          # Sandboxes (LocalProcessSandbox, DockerSandbox)
├── experiments/        # Research evaluation runners and protocols
├── experiment_results/ # Empirical evaluation tables and metric summaries
├── llm/                # LLM provider abstractions (Groq, Gemini, OpenRouter, Mock)
├── observability/      # Telemetry, event logging, and schemas
├── rag/                # RAG retrieval, context builder, context optimizer, memory
├── tests/              # Comprehensive unit and integration test suite
└── ui/                 # React, TypeScript, and Vite interactive dashboard
```

---

## 7. License
Academic and Educational Research License. Developed for Advanced Autonomous Multi-Agent Software Engineering Research.
