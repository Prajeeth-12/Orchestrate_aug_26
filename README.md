# 🛡️ VeraQX: Enterprise Support Triage Agent

[![Go Version](https://img.shields.io/badge/Go-1.22.5+-00ADD8?style=flat&logo=go)](https://go.dev/)
[![AI Engine](https://img.shields.io/badge/AI-Ollama-ED333B?style=flat)](https://ollama.com/)
[![Challenge](https://img.shields.io/badge/HackerRank-Orchestrate-2EC866?style=flat)](https://www.hackerrank.com/)

**VeraQX** is a high-performance, terminal-based AI agent designed to resolve and triage complex support tickets across multi-product ecosystems (**HackerRank**, **Claude**, and **Visa**). Built for the *HackerRank Orchestrate* 24-hour hackathon, it leverages local Hybrid RAG and state-of-the-art LLMs to provide grounded, safe, and accurate support responses.

---

## ✨ v1.1.0 Features

- 🧠 **Multi-Domain Intelligence**: Seamlessly context-switches between help centers for **HackerRank**, **Claude**, and **Visa**.
- 🚀 **Hybrid RAG (Semantic + BM25)**: Combines keyword search with dense vector embeddings using **Reciprocal Rank Fusion (RRF)** ($k=60$) for superior accuracy on technical terms.
- 🛡️ **Zero-Hallucination Guardrails**:
    - **Independent Grounding Verifier**: An external Go module that checks token-overlap between LLM output and corpus documents.
    - **Citation Enforcement**: Every response *must* cite specific corpus documents (e.g., `Document 4 [visa/card]`).
- ⚡ **Performance Engineering**:
    - **Semantic Cache**: Reduces LLM costs by caching semantically similar query intents.
    - **Vector Persistence**: Binary serialization (`.gob`) of embeddings reduces system init time by 30x.
- 🧩 **Multi-Intent Splitting**: Automatically decomposes complex, multi-part support tickets into independent sub-queries.
- 📊 **Judge-Ready Reporting**: Generates a self-contained HTML dashboard with grounding scores and anomaly flags.
- 💬 **Streaming REPL**: Real-time LLM response streaming in the interactive terminal.

---

## 🏗️ Architecture

VeraQX uses a sophisticated hybrid retrieval pipeline:

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

---

## 📂 Repository Structure

```text
.
├── code/                    # Core Go implementation
│   ├── main.go              # CLI Entry point
│   ├── internal/
│   │   ├── config/          # Centralized constants & thresholds
│   │   ├── corpus/          # Hybrid indexing (BM25 + Vector)
│   │   ├── triage/          # Agent logic & classification
│   │   ├── llm/             # Ollama client & Semantic Cache
│   │   └── output/          # CSV/Benchmarking utilities
├── data/                    # The Support Corpus (HackerRank, Claude, Visa)
├── support_tickets/         # Input CSVs and generated Output.csv
├── docs/                    # Official challenge specifications
└── AGENTS.md                # AI Agent logging rules & transcript
```

---

## 🚀 Quick Start

### 1. Setup
```bash
# Clone the repository
git clone <repo-url>
cd hackerrank-orchestrate-may26

# Pull the required models
ollama pull qwen3.6:latest
ollama pull nomic-embed-text  # Recommended for embeddings

# Configure environment
cp .env.example .env
```

### 2. Run Benchmark
Measure accuracy against sample data:
```bash
cd code
go run main.go --benchmark
```

### 3. Run Interactive Mode
```bash
go run main.go --interactive
```

## ✅ Testing

```bash
cd code
/usr/local/go/bin/go test ./...
/usr/local/go/bin/go test -race ./...
/usr/local/go/bin/go test -coverprofile=/tmp/support-triage-coverage.out ./...
```

See [`docs/TESTING.md`](./docs/TESTING.md) for coverage details, API test scope, and benchmark commands.

---

## 🛠 Advanced Configuration

VeraQX can be tuned via CLI flags:
- `--model`: Primary LLM for classification and responses.
- `--embed-model`: Model used for vector embeddings (e.g., `nomic-embed-text`).
- `--benchmark`: Run accuracy evaluation on the input dataset.
- `--top-k`: Number of documents to retrieve per ticket (default: 15).
- `--use-cache`: Enable/disable semantic caching (default: true).

---

## ⚖️ License & Rules

This project is part of the **HackerRank Orchestrate** hackathon. 
- **Solo Challenge**: Authoring must be original.
- **Evaluative Entry Point**: `code/main.go` is the canonical entry point.

---

*VeraQX — Precision Triage, Grounded Intelligence.*
