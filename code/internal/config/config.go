package config

import (
	"bufio"
	"os"
	"strings"
	"time"
)

const (
	// Version
	Version = "1.1.0"

	// Triage Thresholds
	GroundingThreshold     = 0.20
	SafetyEscalationReason = "Safety verification failed. Escalated for human review."

	// Retrieval
	DefaultTopK             = 15
	RRFConstant             = 60.0
	MultiIntentMaxChunksMul = 2.0
	ChunkOverlapPercentage  = 0.2

	// Semantic Cache
	CacheSimilarityThreshold = 0.85
	CacheTTL                 = 24 * time.Hour

	// Persistence
	DefaultOutputDir      = "outputs"
	DefaultCacheDir       = ".cache"
	VectorCacheFilename   = "vector.bin"
	SemanticCacheFilename = "semantic.bin"
	BM25CacheFilename     = "bm25.bin"

	// Rewriter
	RewriterMinWords     = 5
	RewriterMaxWords     = 200
	RewriterLengthMaxMul = 3.0

	// UI Colors
	ColorReset  = "\033[0m"
	ColorRed    = "\033[31m"
	ColorGreen  = "\033[32m"
	ColorYellow = "\033[33m"
	ColorBlue   = "\033[34m"
	ColorPurple = "\033[35m"
	ColorCyan   = "\033[36m"
	ColorGray   = "\033[90m"
	ColorBold   = "\033[1m"
	ColorDim    = "\033[2m"
	ColorItalic = "\033[3m"
)

// LoadEnv reads a .env file and sets environment variables.
func LoadEnv(path string) {
	file, err := os.Open(path)
	if err != nil {
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) == 2 {
			os.Setenv(strings.TrimSpace(parts[0]), strings.TrimSpace(parts[1]))
		}
	}
}

// EnvOrDefault returns the value of an environment variable or a fallback.
func EnvOrDefault(name, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(name)); value != "" {
		return value
	}
	return fallback
}
