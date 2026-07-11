package main

import (
	"bufio"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"support-triage/internal/config"
	"support-triage/internal/corpus"
	"support-triage/internal/llm"
	"support-triage/internal/output"
	"support-triage/internal/reporter"
	"support-triage/internal/runner"
	"support-triage/internal/triage"
)

func main() {
	// Load .env file if it exists
	config.LoadEnv("../.env")

	// CLI flags
	inputPath := flag.String("input", "../support_tickets/support_tickets.csv", "Path to input CSV")
	outputPath := flag.String("output", "../support_tickets/output.csv", "Path to output CSV")
	dataDir := flag.String("data", "../data", "Path to corpus data directory")
	model := flag.String("model", config.EnvOrDefault("OLLAMA_MODEL", "gemma4:31b"), "Ollama model name")
	backupModel := flag.String("backup-model", config.EnvOrDefault("OLLAMA_BACKUP_MODEL", "qwen3.6:latest"), "Ollama backup model name")
	embedModel := flag.String("embed-model", config.EnvOrDefault("OLLAMA_EMBED_MODEL", "nomic-embed-text-v2-moe"), "Ollama embedding model name")
	ollamaURL := flag.String("ollama-url", config.EnvOrDefault("OLLAMA_URL", "http://100.87.204.58:11434"), "Ollama server URL")
	showDashboard := flag.Bool("dashboard", true, "Show intelligence dashboard after processing")
	htmlReport := flag.String("html-report", filepath.Join(config.DefaultOutputDir, "report.html"), "Path to save HTML report")
	interactive := flag.Bool("interactive", false, "Interactive REPL mode")
	topK := flag.Int("top-k", config.DefaultTopK, "Number of corpus chunks to retrieve per ticket")
	concurrency := flag.Int("concurrency", 4, "Number of tickets to process in parallel")
	useCache := flag.Bool("use-cache", true, "Use semantic cache to speed up processing")
	benchmark := flag.Bool("benchmark", false, "Run in benchmark mode to measure accuracy against expected labels")
	verbose := flag.Bool("verbose", true, "Show per-ticket processing status")
	flag.Parse()

	// Ensure directories exist
	os.MkdirAll(config.DefaultOutputDir, 0755)
	os.MkdirAll(config.DefaultCacheDir, 0755)

	// Resolve and display the output path so users can find results easily.
	resolvedOutput, err := filepath.Abs(*outputPath)
	if err != nil {
		resolvedOutput = *outputPath
	}

	fmt.Println()
	printBanner()
	fmt.Printf("   %s%sOutput:%s %s\n\n", config.ColorGray, config.ColorItalic, config.ColorReset, resolvedOutput)

	// Step 1: Initialize LLM client
	fmt.Printf("\n%s[1/4]%s Connecting to Ollama at %s...\n", config.ColorBold, config.ColorReset, *ollamaURL)
	llmClient := llm.NewClient(*ollamaURL, *model, *backupModel)
	if err := llmClient.Ping(); err != nil {
		fmt.Printf("  %s✗ %v%s\n", config.ColorRed, err, config.ColorReset)
		fmt.Println("  Make sure Ollama is running and accessible.")
		os.Exit(1)
	}
	fmt.Printf("  %s✓ Connected — model: %s%s\n", config.ColorGreen, *model, config.ColorReset)

	// Step 2: Load corpus
	fmt.Printf("\n%s[2/4]%s Loading corpus from %s...\n", config.ColorBold, config.ColorReset, *dataDir)
	startLoad := time.Now()
	docs, err := corpus.LoadCorpus(*dataDir)
	if err != nil {
		fmt.Printf("  %s✗ Failed to load corpus: %v%s\n", config.ColorRed, err, config.ColorReset)
		os.Exit(1)
	}
	fmt.Printf("  %s✓ Loaded %d documents in %v%s\n", config.ColorGreen, len(docs), time.Since(startLoad).Round(time.Millisecond), config.ColorReset)

	// Step 3: Build retrieval indices
	fmt.Printf("\n%s[3/4]%s Building retrieval indices...\n", config.ColorBold, config.ColorReset)
	chunks := corpus.ChunkDocuments(docs)

	// BM25 Index
	bm25CachePath := filepath.Join(config.DefaultCacheDir, config.BM25CacheFilename)
	index, err := corpus.LoadBM25IndexFromDisk(bm25CachePath)
	if err == nil && len(index.Chunks) == len(chunks) {
		fmt.Printf("  %s✓ Loaded BM25 index from cache%s\n", config.ColorGreen, config.ColorReset)
	} else {
		index = corpus.NewBM25Index(chunks)
		if err := index.SaveToDisk(bm25CachePath); err != nil {
			fmt.Printf("  %s⚠ Failed to save BM25 cache: %v%s\n", config.ColorYellow, err, config.ColorReset)
		}
		fmt.Printf("  %s✓ Built BM25 index and saved to cache%s\n", config.ColorGreen, config.ColorReset)
	}

	// Vector Index
	startVec := time.Now()
	vecCachePath := filepath.Join(config.DefaultCacheDir, config.VectorCacheFilename)
	cachedEmbeddings, cacheValid := corpus.LoadEmbeddingsFromDisk(vecCachePath, len(chunks))
	var vectorIndex *corpus.VectorIndex

	if cacheValid {
		vectorIndex = corpus.NewVectorIndex(chunks, cachedEmbeddings)
		fmt.Printf("  %s✓ Loaded %d cached embeddings in %v%s\n", config.ColorGreen, len(chunks), time.Since(startVec).Round(time.Millisecond), config.ColorReset)
	} else {
		fmt.Printf("  %s! Generating embeddings for %d chunks (concurrently)...%s\n", config.ColorYellow, len(chunks), config.ColorReset)
		embeddings, err := corpus.GenerateEmbeddingsConcurrent(llmClient, *embedModel, chunks, *concurrency*2) // Higher concurrency for embedding
		if err != nil {
			fmt.Printf("  %s✗ Failed to generate embeddings: %v%s\n", config.ColorRed, err, config.ColorReset)
			os.Exit(1)
		}
		vectorIndex = corpus.NewVectorIndex(chunks, embeddings)
		fmt.Printf("  %s✓ Generated %d embeddings in %v%s\n", config.ColorGreen, len(chunks), time.Since(startVec).Round(time.Second), config.ColorReset)

		if err := vectorIndex.SaveToDisk(vecCachePath); err != nil {
			fmt.Printf("  %s⚠ Failed to save embedding cache: %v%s\n", config.ColorYellow, err, config.ColorReset)
		}
	}

	// Create agent
	agent := &triage.Agent{
		Index:       index,
		VectorIndex: vectorIndex,
		LLMClient:   llmClient,
		TopK:        *topK,
		EmbedModel:  *embedModel,
	}
	if *useCache {
		agent.Cache = llm.NewSemanticCache()
		semanticCachePath := filepath.Join(config.DefaultCacheDir, config.SemanticCacheFilename)
		if err := agent.Cache.LoadFromDisk(semanticCachePath); err == nil {
			fmt.Printf("  %s✓ Loaded semantic cache from %s%s\n", config.ColorGreen, semanticCachePath, config.ColorReset)
		}
	}

	if *interactive {
		runREPL(agent)
		return
	}

	// Step 4: Process tickets
	fmt.Printf("\n%s[4/4]%s Processing tickets from %s...\n", config.ColorBold, config.ColorReset, *inputPath)
	tickets, err := output.ReadTickets(*inputPath)
	if err != nil {
		fmt.Printf("  %s✗ Failed to read tickets: %v%s\n", config.ColorRed, err, config.ColorReset)
		os.Exit(1)
	}
	fmt.Printf("  Found %d tickets to process\n\n", len(tickets))

	r := &runner.Runner{
		Agent:       agent,
		Concurrency: *concurrency,
		Benchmark:   *benchmark,
		Verbose:     *verbose,
	}

	runResult := r.Run(tickets)

	n := len(runResult.Results)
	if n == 0 {
		fmt.Printf("\n  %s✓ No tickets processed%s\n", config.ColorGreen, config.ColorReset)
	} else {
		fmt.Printf("\n  %s✓ Processed %d tickets in %v (avg %.1fs/ticket)%s\n",
			config.ColorGreen, n, runResult.Elapsed.Round(time.Second),
			runResult.Elapsed.Seconds()/float64(n), config.ColorReset)
	}

	// Benchmark output
	if *benchmark && runResult.BenchmarkStats != nil {
		stats := runResult.BenchmarkStats
		fmt.Printf("\n%s%s── Benchmark Results ─────────────────────────────────%s\n", config.ColorBold, config.ColorPurple, config.ColorReset)
		fmt.Printf("  Total Evaluated:  %d\n", stats.TotalEvaluated)
		fmt.Printf("  Status Accuracy:  %s%.1f%%%s (%d/%d)\n", config.ColorGreen, stats.StatusAccuracy, config.ColorReset, stats.StatusMatches, stats.TotalEvaluated)
		fmt.Printf("  Type Accuracy:    %s%.1f%%%s (%d/%d)\n", config.ColorGreen, stats.TypeAccuracy, config.ColorReset, stats.TypeMatches, stats.TotalEvaluated)
		fmt.Printf("  Area Accuracy:    %s%.1f%%%s (%d/%d)\n\n", config.ColorGreen, stats.AreaAccuracy, config.ColorReset, stats.AreaMatches, stats.TotalEvaluated)
	}

	// Write output
	if err := output.WriteResults(*outputPath, runResult.Results); err != nil {
		fmt.Printf("  %s✗ Failed to write output: %v%s\n", config.ColorRed, err, config.ColorReset)
		os.Exit(1)
	}
	fmt.Printf("  %s✓ Output written to %s%s\n", config.ColorGreen, *outputPath, config.ColorReset)

	// Dashboard and Reporting
	if *showDashboard {
		dashData := reporter.BuildDashboardData(runResult.Results, runResult.Metrics, runResult.GroundingScores, runResult.SectionHits, runResult.SectionDomains)
		reporter.RenderDashboard(dashData)

		if *htmlReport != "" {
			if err := reporter.GenerateHTMLReport(*htmlReport, dashData, runResult.Results); err != nil {
				fmt.Printf("  %s✗ Failed to generate HTML report: %v%s\n", config.ColorRed, err, config.ColorReset)
			} else {
				fmt.Printf("  %s✓ HTML report saved to %s%s\n", config.ColorGreen, *htmlReport, config.ColorReset)
			}
		}
	}

	// Persist semantic cache before exiting
	if *useCache && agent.Cache != nil {
		semanticCachePath := filepath.Join(config.DefaultCacheDir, config.SemanticCacheFilename)
		if err := agent.Cache.SaveToDisk(semanticCachePath); err != nil {
			fmt.Printf("\n  %s⚠ Failed to save semantic cache: %v%s\n", config.ColorYellow, err, config.ColorReset)
		} else {
			fmt.Printf("\n  %s✓ Semantic cache persisted to %s%s\n", config.ColorGreen, semanticCachePath, config.ColorReset)
		}
	}
}

func printBanner() {
	banner := `
   _   __               ____  _  __
  | | / /__ _ __ ____ _/ __ \| |/ /
  | |/ / -_) '__/ _  / / /_/ />  < 
  |___/\___/_/  \_,_/_/\___\_\_|\_\
`
	fmt.Printf("%s%s%s%s\n", config.ColorBold, config.ColorPurple, banner, config.ColorReset)
	fmt.Printf("   %s%sGrounding Intelligence for Support Engineering%s\n", config.ColorBold, config.ColorGray, config.ColorReset)
	fmt.Printf("   %s%sVersion %s %s│ %sHackerRank Orchestrate 2026%s\n\n", config.ColorGray, config.ColorItalic, config.Version, config.ColorReset+config.ColorGray, config.ColorBold+config.ColorCyan, config.ColorReset)
}

func runREPL(agent *triage.Agent) {
	fmt.Printf("\n%s%s── Interactive Mode ──────────────────────────────────%s\n", config.ColorBold, config.ColorPurple, config.ColorReset)
	fmt.Printf("%s  Type a ticket to triage. Commands: %s/company <name>%s, %s/quit%s\n", config.ColorGray, config.ColorBold, config.ColorGray, config.ColorBold, config.ColorReset)
	fmt.Println()

	scanner := bufio.NewScanner(os.Stdin)
	company := "None"

	for {
		promptColor := config.ColorPurple
		if company != "None" {
			promptColor = config.ColorCyan
		}
		fmt.Printf("%svera %s❯ %s", config.ColorBold+promptColor, promptColor, config.ColorReset)
		if !scanner.Scan() {
			break
		}
		input := strings.TrimSpace(scanner.Text())

		if input == "" {
			continue
		}
		if input == "/quit" || input == "/exit" || input == "/q" {
			fmt.Println("Goodbye!")
			break
		}
		if strings.HasPrefix(input, "/company ") {
			company = strings.TrimPrefix(input, "/company ")
			fmt.Printf("  Company set to: %s%s%s\n", config.ColorCyan, company, config.ColorReset)
			continue
		}

		ticket := output.Ticket{
			Issue:   input,
			Subject: "",
			Company: company,
		}

		fmt.Println()
		fmt.Printf("  %s○ %sThinking...%s\n  ", config.ColorPurple, config.ColorItalic+config.ColorGray, config.ColorReset)

		agent.StreamCallback = func(token string) {
			fmt.Printf("%s%s%s", config.ColorDim, token, config.ColorReset)
		}

		result, metrics := agent.ProcessTicket(ticket, 0)
		agent.StreamCallback = nil
		fmt.Println()

		fmt.Printf("\n  %s═══ RETRIEVED CONTEXT ═══%s\n", config.ColorCyan, config.ColorReset)
		if len(metrics.RetrievedChunks) == 0 {
			fmt.Printf("  %sNo relevant corpus chunks found.%s\n", config.ColorDim, config.ColorReset)
		} else {
			for i, sc := range metrics.RetrievedChunks {
				title := sc.Chunk.Title
				if len(title) > 50 {
					title = title[:47] + "..."
				}
				fmt.Printf("  %d. [%.2f] %s%s%s — %s\n",
					i+1, sc.Score, config.ColorBold, sc.Chunk.Domain, config.ColorReset, title)
			}
		}

		statusColor := config.ColorGreen
		if result.Status == "escalated" {
			statusColor = config.ColorRed
		}
		fmt.Printf("\n  %s%s%s%s  %s%s%s\n", config.ColorBold, statusColor, "●", config.ColorReset, config.ColorBold, strings.ToUpper(result.Status), config.ColorReset)
		fmt.Printf("  %sRequest Type:%s %s\n", config.ColorGray, config.ColorReset, result.RequestType)
		fmt.Printf("  %sProduct Area:%s %s\n", config.ColorGray, config.ColorReset, result.ProductArea)
		fmt.Printf("  %sGrounding:%s    %.2f (LLM) | %.2f (Verified)\n", config.ColorGray, config.ColorReset, metrics.GroundingScore, metrics.VerifiedGrounding)
		fmt.Printf("  %sLatency:%s      %v\n", config.ColorGray, config.ColorReset, metrics.Duration.Round(time.Millisecond))

		fmt.Printf("\n  %sResponse%s\n", config.ColorBold+config.ColorPurple, config.ColorReset)
		fmt.Printf("  %s\n", result.Response)

		fmt.Printf("\n  %sJustification%s\n", config.ColorItalic+config.ColorGray, config.ColorReset)
		fmt.Printf("  %s%s%s\n\n", config.ColorGray, result.Justification, config.ColorReset)
	}
}
