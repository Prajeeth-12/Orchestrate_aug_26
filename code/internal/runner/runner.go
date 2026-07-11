package runner

import (
	"fmt"
	"strings"
	"sync"
	"time"

	"support-triage/internal/config"
	"support-triage/internal/output"
	"support-triage/internal/triage"
)

// Runner orchestrates the processing of multiple support tickets.
type Runner struct {
	Agent       *triage.Agent
	Concurrency int
	Benchmark   bool
	Verbose     bool
}

// RunResult contains the aggregated results and metrics from a processing run.
type RunResult struct {
	Results         []output.TriageResult
	Metrics         []triage.TicketMetrics
	GroundingScores []float64
	SectionHits     map[string]int
	SectionDomains  map[string]string
	Elapsed         time.Duration
	BenchmarkStats  *BenchmarkStats
}

// BenchmarkStats holds accuracy metrics if running in benchmark mode.
type BenchmarkStats struct {
	TotalEvaluated int
	StatusAccuracy float64
	TypeAccuracy   float64
	AreaAccuracy   float64
	StatusMatches  int
	TypeMatches    int
	AreaMatches    int
}

// Run processes a slice of tickets in parallel and returns aggregated results.
func (r *Runner) Run(tickets []output.Ticket) *RunResult {
	res := &RunResult{
		Results:         make([]output.TriageResult, len(tickets)),
		Metrics:         make([]triage.TicketMetrics, len(tickets)),
		GroundingScores: make([]float64, len(tickets)),
		SectionHits:     make(map[string]int),
		SectionDomains:  make(map[string]string),
	}

	start := time.Now()
	var wg sync.WaitGroup
	var mu sync.Mutex
	sem := make(chan struct{}, r.Concurrency)

	processed := 0
	replied := 0
	escalated := 0
	cacheHits := 0

	// Clear screen and hide cursor for a clean start if verbose
	if r.Verbose {
		fmt.Print("\033[2J\033[H\033[?25l")
		fmt.Printf("%s%s VeraQX Support Triage — Batch Processing %s%s\n", config.ColorBold, config.ColorCyan, config.ColorReset, config.ColorDim)
		fmt.Printf("%s----------------------------------------------------------%s\n\n", config.ColorGray, config.ColorReset)
	}

	for i, ticket := range tickets {
		wg.Add(1)
		sem <- struct{}{}

		go func(idx int, t output.Ticket) {
			defer wg.Done()
			defer func() { <-sem }()

			result, metrics := r.Agent.ProcessTicket(t, idx)

			mu.Lock()
			res.Results[idx] = result
			res.Metrics[idx] = metrics
			res.GroundingScores[idx] = metrics.GroundingScore

			processed++
			if result.Status == "replied" {
				replied++
			} else {
				escalated++
			}
			if metrics.CacheHit {
				cacheHits++
			}

			for _, sc := range metrics.RetrievedChunks {
				section := sc.Chunk.Section
				if section != "" {
					res.SectionHits[section]++
					res.SectionDomains[section] = sc.Chunk.Domain
				}
			}

			if r.Verbose {
				// Move to line 4 to start printing progress
				fmt.Print("\033[4;1H")

				// Progress Bar — guard against zero-length ticket slice
				width := 40
				total := len(tickets)
				var filled, pct int
				if total > 0 {
					filled = (processed * width) / total
					pct = (processed * 100) / total
				}
				bar := strings.Repeat("█", filled) + strings.Repeat("░", width-filled)

				// Guard against near-zero elapsed to avoid +Inf tps
				var tps float64
				if elapsed := time.Since(start).Seconds(); elapsed > 0 {
					tps = float64(processed) / elapsed
				}

				fmt.Printf("  %sProgress:%s [%s] %d%% (%d/%d)\n", config.ColorBold, config.ColorReset, bar, pct, processed, total)
				fmt.Printf("  %sSpeed:%s    %.2f tickets/sec\n\n", config.ColorBold, config.ColorReset, tps)

				fmt.Printf("  %sStats:%s    %s%d Replied%s | %s%d Escalated%s | %s%d Cache Hits%s\n\n",
					config.ColorBold, config.ColorReset,
					config.ColorGreen, replied, config.ColorReset,
					config.ColorRed, escalated, config.ColorReset,
					config.ColorPurple, cacheHits, config.ColorReset)

				// Current Activity
				fmt.Printf("  %sActivity:%s %s%-12s%s %-40s\n",
					config.ColorBold, config.ColorReset,
					config.ColorCyan, t.Company, config.ColorReset,
					t.Subject)
			}
			mu.Unlock()
		}(i, ticket)
	}
	wg.Wait()

	// Show cursor again
	if r.Verbose {
		fmt.Print("\033[?25h")
		fmt.Printf("\n%s%s Batch Complete! Total Time: %v %s\n\n", config.ColorBold, config.ColorGreen, time.Since(start).Round(time.Millisecond), config.ColorReset)
	}

	res.Elapsed = time.Since(start)

	if r.Benchmark {
		res.BenchmarkStats = r.CalculateBenchmark(tickets, res.Results)
	}

	return res
}

func (r *Runner) CalculateBenchmark(tickets []output.Ticket, results []output.TriageResult) *BenchmarkStats {
	stats := &BenchmarkStats{}
	for i, t := range tickets {
		if t.ExpectedStatus == "" && t.ExpectedRequestType == "" {
			continue
		}
		stats.TotalEvaluated++

		if strings.EqualFold(results[i].Status, t.ExpectedStatus) {
			stats.StatusMatches++
		}
		if strings.EqualFold(results[i].RequestType, t.ExpectedRequestType) {
			stats.TypeMatches++
		}

		actualArea := strings.ReplaceAll(strings.ToLower(results[i].ProductArea), "_", " ")
		expectedArea := strings.ReplaceAll(strings.ToLower(t.ExpectedProductArea), "_", " ")
		if strings.TrimSpace(actualArea) == strings.TrimSpace(expectedArea) {
			stats.AreaMatches++
		}
	}

	if stats.TotalEvaluated > 0 {
		stats.StatusAccuracy = float64(stats.StatusMatches) / float64(stats.TotalEvaluated) * 100
		stats.TypeAccuracy = float64(stats.TypeMatches) / float64(stats.TotalEvaluated) * 100
		stats.AreaAccuracy = float64(stats.AreaMatches) / float64(stats.TotalEvaluated) * 100
	}
	return stats
}
