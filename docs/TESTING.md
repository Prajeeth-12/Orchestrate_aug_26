# Testing Guide

This project is a Go CLI application. It has no frontend, no database, and no first-party HTTP API server. API testing is focused on the Ollama client endpoints used by the agent:

- `GET /api/tags`
- `POST /api/generate`
- `POST /api/embed`

All API tests use `httptest` and do not require a live Ollama server.

## Test Commands

Run all unit and integration-style tests:

```bash
cd code
/usr/local/go/bin/go test ./...
```

Run race detection:

```bash
cd code
/usr/local/go/bin/go test -race ./...
```

Run coverage for all packages:

```bash
cd code
/usr/local/go/bin/go test -coverpkg=./internal/... -coverprofile=/tmp/support-triage-coverage.out ./...
/usr/local/go/bin/go tool cover -func=/tmp/support-triage-coverage.out
```

Run internal package coverage only:

```bash
cd code
/usr/local/go/bin/go test -coverpkg=./internal/... ./internal/...
```

Run performance benchmarks:

```bash
cd code
/usr/local/go/bin/go test -run '^$' -bench 'Benchmark' ./...
```

Build the CLI:

```bash
cd code
/usr/local/go/bin/go build -o /tmp/support-triage-check .
```

## Current Coverage Targets

The core internal packages are covered above 90%:

- `internal/corpus`: 92.1%
- `internal/llm`: 94.5%
- `internal/output`: 94.0%
- `internal/prompt`: 100.0%
- `internal/reporter`: 94.4%
- `internal/runner`: 98.4%
- `internal/triage`: 91.4%

The full repository coverage is lower because `main()` launches the complete CLI workflow, including live Ollama connectivity and interactive REPL behavior. Those paths are validated with build checks and targeted helper tests rather than unit tests.

## Test Coverage Map

- `internal/config`: constant sanity checks.
- `internal/corpus`: markdown loading, chunking, tokenization, BM25 retrieval, vector search, cache persistence, and benchmarks.
- `internal/llm`: semantic cache, Ollama generate/stream/embed/tags API behavior, failures, fallback, and retry orchestration.
- `internal/output`: CSV parsing and writing.
- `internal/reporter`: terminal dashboard rendering, anomaly detection, and HTML report generation.
- `internal/runner`: parallel ticket processing, concurrency control, and accuracy benchmarks.
- `internal/prompt`: prompt structure and no-context behavior.
- `internal/triage`: safety checks, company/product/request classifiers, query rewriting, grounding verification, response parsing, hybrid retrieval, caching, and end-to-end ticket processing with mocked LLM APIs.
- `main`: environment loading and default resolution helpers.
