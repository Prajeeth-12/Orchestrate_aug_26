# VeraQX: Multi-Domain Support Triage Agent (Go)

VeraQX is a high-performance, terminal-based AI agent designed to triage support tickets for **HackerRank**, **Claude**, and **Visa** using Hybrid RAG with independent grounding verification.

## Prerequisites

- **Go 1.22.5+**
- **Ollama** running locally or on a reachable network
- Required models:
  - `gemma4:31b` — primary LLM for classification and response generation
  - `qwen3.6:latest` — backup model & query rewriter
  - `nomic-embed-text-v2-moe` — embedding model for vector search

```bash
ollama pull gemma4:31b
ollama pull qwen3.6:latest
ollama pull nomic-embed-text
```

## Quick Start

```bash
cd code

# Configure environment
cp ../.env.example ../.env
# Edit ../.env to set OLLAMA_URL, OLLAMA_MODEL etc.

# Run batch processing (generates output.csv + HTML report)
go run main.go --html-report ../support_tickets/final_report.html

# Run in interactive REPL mode
go run main.go --interactive

# Run accuracy benchmark against labeled sample data
go run main.go --input ../support_tickets/sample_support_tickets.csv --benchmark
```

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--input` | `../support_tickets/support_tickets.csv` | Path to input CSV |
| `--output` | `../support_tickets/output.csv` | Path to output CSV |
| `--data` | `../data` | Path to corpus data directory |
| `--model` | `gemma4:31b` | Primary Ollama model |
| `--backup-model` | `qwen3.6:latest` | Backup/rewriter model |
| `--embed-model` | `nomic-embed-text-v2-moe` | Embedding model |
| `--ollama-url` | `http://localhost:11434` | Ollama server URL |
| `--top-k` | `15` | Number of corpus chunks to retrieve |
| `--concurrency` | `4` | Parallel ticket processing |
| `--use-cache` | `true` | Enable semantic cache |
| `--benchmark` | `false` | Run accuracy evaluation |
| `--interactive` | `false` | Interactive REPL mode |
| `--html-report` | `outputs/report.html` | Path to save HTML report |
| `--dashboard` | `true` | Show terminal intelligence dashboard |

## Testing & QA

The test suite uses Go's built-in `testing` package and `httptest`; it does not require a live Ollama server.

```bash
cd code

# Unit and integration-style tests
/usr/local/go/bin/go test ./...

# Race detection
/usr/local/go/bin/go test -race ./...

# Coverage
/usr/local/go/bin/go test -coverpkg=./internal/... -coverprofile=/tmp/support-triage-coverage.out ./...
/usr/local/go/bin/go tool cover -func=/tmp/support-triage-coverage.out

# Performance benchmark examples
/usr/local/go/bin/go test -run '^$' -bench 'Benchmark' ./...
```

Current internal package coverage:

| Package | Coverage |
|---------|----------|
| `internal/corpus` | 92.1% |
| `internal/llm` | 94.5% |
| `internal/output` | 94.0% |
| `internal/prompt` | 100.0% |
| `internal/reporter` | 94.4% |
| `internal/runner` | 98.4% |
| `internal/triage` | 91.4% |

See [`../docs/TESTING.md`](../docs/TESTING.md) for the full QA command reference and coverage map.

## Architecture (v1.1.0)

```text
Input Ticket ──► [ Query Rewriter ] ──► [ Semantic Cache ] ──► (Cache Hit?) ──► Response
                      │                       │
                (Multi-Intent Split)    (Cache Miss)
                      │                       │
                      ▼                       ▼
              [ Hybrid Retrieval ] ◄──────────┘
              ( BM25 + Vector )
                      │
                [ RRF Fusion ]
                      │
                      ▼
              [ LLM Generator ] ──► [ Grounding Verifier ] ──► Final Output
```

### Pipeline Stages

1. **Safety Pre-Filter** (`triage/safety.go`): Rule-based detection of prompt injection, malicious input, and high-risk topics.
2. **Query Rewriting** (`triage/rewriter.go`): Normalizes noisy input text and splits multi-intent queries into atomic sub-tasks using the backup model.
3. **Hybrid Retrieval** (`corpus/bm25.go` + `corpus/vector.go`): Dual-mode search combining BM25 keyword matching with dense vector embeddings.
4. **RRF Fusion** (`triage/agent.go`): Reciprocal Rank Fusion (k=60) merges ranked lists from both retrieval methods.
5. **LLM Generation** (`llm/ollama.go`): Grounded response generation with chain-of-thought prompting and mandatory corpus citations.
6. **Independent Grounding Verification** (`triage/verifier.go`): Post-generation token-overlap check between LLM output and retrieved corpus documents.
7. **Classification** (`triage/classifier.go`): Request type and product area inference from ticket content and retrieved chunks.
8. **Caching** (`llm/cache.go`): Vector-similarity semantic cache with configurable TTL for recurring intents.

### Performance Optimizations

- **Embedding Persistence**: Binary serialization (`.gob`) of corpus embeddings reduces cold-start from ~13s to <400ms.
- **Concurrent Processing**: Configurable goroutine pool for parallel ticket processing.
- **Model Fallback**: Automatic failover from primary to backup model on error with exponential backoff.

## Package Structure

```text
code/
├── main.go                    # CLI entry point (thin wrapper)
├── internal/
│   ├── config/config.go       # Centralized constants & thresholds
│   ├── corpus/
│   │   ├── loader.go          # Corpus file loading (Markdown → structured docs)
│   │   ├── chunker.go         # Sliding-window chunker with overlap
│   │   ├── bm25.go            # Pure Go BM25 index
│   │   └── vector.go          # Vector index with disk persistence
│   ├── llm/
│   │   ├── ollama.go          # Ollama HTTP client (generate, stream, embed)
│   │   └── cache.go           # Semantic similarity cache
│   ├── triage/
│   │   ├── agent.go           # Core triage logic (single ticket)
│   │   ├── safety.go          # Safety pre-filter & prompt injection detection
│   │   ├── classifier.go      # Request type & product area classification
│   │   ├── rewriter.go        # Query normalization & multi-intent splitting
│   │   └── verifier.go        # Independent grounding verification
│   ├── prompt/
│   │   └── templates.go       # System & user prompt templates with CoT
│   ├── runner/
│   │   └── runner.go          # Parallel batch processing orchestrator
│   ├── reporter/
│   │   └── reporter.go        # Dashboard & HTML report generation
│   └── output/
│       └── csv.go             # CSV I/O utilities
```

## Output Format

The agent generates `output.csv` with the following columns:

| Column | Values | Description |
|--------|--------|-------------|
| `issue` | _(original)_ | Original ticket issue text |
| `subject` | _(original)_ | Original ticket subject |
| `company` | HackerRank / Claude / Visa | Detected or provided company |
| `response` | _(generated)_ | Grounded agent response |
| `product_area` | screen / community / general_support / privacy / travel_support / conversation_management | Inferred product area |
| `status` | replied / escalated | Agent decision |
| `request_type` | product_issue / feature_request / bug / invalid | Classified request type |
| `justification` | _(generated)_ | Reasoning with corpus citations |
| `citations` | _(generated)_ | Semicolon-separated list of cited corpus document titles |
