package triage

import (
	"strings"
	"support-triage/internal/corpus"
)

// domainKeywords maps keywords strongly associated with each company.
var domainKeywords = map[string][]string{
	"hackerrank": {
		"hackerrank", "hacker rank", "coding test", "assessment", "test", "candidate",
		"interview", "screen", "library", "questions", "submissions", "challenges",
		"recruiter", "hiring", "certifications", "prep kit", "contest",
		"mock interview", "practice", "leaderboard", "coding challenge",
		"apply tab", "resume builder", "certificate",
	},
	"claude": {
		"claude", "anthropic", "conversation", "pro plan", "max plan",
		"team plan", "enterprise plan", "artifacts", "projects",
		"ai assistant", "mcp", "desktop extension", "claude desktop",
		"bedrock", "api", "prompt", "tokens", "context window",
		"subscription", "claude pro", "model selector", "cowork",
	},
	"visa": {
		"visa", "credit card", "debit card", "card", "transaction",
		"merchant", "payment", "atm", "chip", "contactless",
		"traveller", "cheque", "chargeback", "cardholder",
		"visa card", "visa india", "visa rules", "exchange rate",
	},
}

// InferCompany determines the most likely company from ticket text using keyword heuristics + BM25 scores.
func InferCompany(issue, subject string, bm25Scores map[string]float64) string {
	combined := strings.ToLower(issue + " " + subject)

	// Phase 1: Direct keyword matching with scoring
	keywordScores := map[string]float64{
		"hackerrank": 0,
		"claude":     0,
		"visa":       0,
	}

	for domain, keywords := range domainKeywords {
		for _, kw := range keywords {
			if strings.Contains(combined, kw) {
				weight := float64(len(kw)) / 5.0 // longer keywords = higher confidence
				keywordScores[domain] += weight
			}
		}
	}

	// Phase 2: Blend with BM25 domain scores
	for domain, score := range bm25Scores {
		d := strings.ToLower(domain)
		keywordScores[d] += score * 0.3 // BM25 is supplementary
	}

	// Find winner
	bestDomain := ""
	bestScore := 0.0
	for domain, score := range keywordScores {
		if score > bestScore {
			bestScore = score
			bestDomain = domain
		}
	}

	// Normalize domain names to match expected format
	switch bestDomain {
	case "hackerrank":
		return "HackerRank"
	case "claude":
		return "Claude"
	case "visa":
		return "Visa"
	}

	return "None"
}

var areaMapping = map[string]string{
	"travel_support":               "travel_support",
	"consumer":                     "general_support",
	"support":                      "general_support",
	"support/consumer":             "general_support",
	"support/merchant":             "general_support",
	"support/small_business":       "general_support",
	"visa":                         "general_support",
	"screen":                       "screen",
	"managing_tests":               "screen",
	"hackerrank_community":         "community",
	"community":                    "community",
	"conversation_management":      "conversation_management",
	"conversation-management":      "conversation_management",
	"privacy":                      "privacy",
	"personalization_settings":     "privacy",
	"personalization-and-settings": "privacy",
}

// InferProductArea determines the product area from top retrieved chunks.
func InferProductArea(chunks []corpus.ScoredChunk, company string) string {
	if len(chunks) == 0 {
		return "general_support"
	}

	// Use the section/category of the top-scoring chunk
	topChunk := chunks[0].Chunk
	path := strings.ToLower(topChunk.FilePath)

	// Phase 1: High-confidence path matches
	if strings.Contains(path, "travel-support.md") {
		return "travel_support"
	}
	if strings.Contains(path, "personalization-and-settings") {
		return "privacy"
	}
	if strings.Contains(path, "conversation-management") {
		return "conversation_management"
	}
	if strings.Contains(path, "hackerrank_community") {
		return "community"
	}

	section := topChunk.Section

	if section == "" {
		return inferProductAreaFromDomain(company)
	}

	// Clean up section names
	parts := strings.Split(section, "/")
	var area string
	if len(parts) > 1 {
		// Try deeper path first
		deep := strings.ToLower(strings.ReplaceAll(strings.ReplaceAll(section, "-", "_"), " ", "_"))
		if mapped, ok := areaMapping[deep]; ok {
			return mapped
		}
		area = parts[0]
	} else {
		area = section
	}

	area = strings.ToLower(strings.ReplaceAll(strings.ReplaceAll(area, "-", "_"), " ", "_"))
	if mapped, ok := areaMapping[area]; ok {
		return mapped
	}

	return inferProductAreaFromDomain(company)
}

func inferProductAreaFromDomain(company string) string {
	switch company {
	case "HackerRank":
		return "screen"
	case "Claude":
		return "conversation_management"
	case "Visa":
		return "general_support"
	default:
		return "general_support"
	}
}

// ClassifyRequestType determines the request type from the issue text.
func ClassifyRequestType(issue, subject string, safetyResult SafetyResult) string {
	if safetyResult.IsInvalid {
		return "invalid"
	}

	combined := strings.ToLower(issue + " " + subject)

	// Feature request indicators
	featureKeywords := []string{
		"feature request", "would be nice", "can you add", "please add",
		"suggestion", "wish list", "enhancement", "new feature",
		"it would be great if", "would love to see",
	}
	for _, kw := range featureKeywords {
		if strings.Contains(combined, kw) {
			return "feature_request"
		}
	}

	// Bug indicators
	bugKeywords := []string{
		"bug", "broken", "crash", "error", "not working", "doesn't work",
		"won't load", "fails", "failing", "stopped working", "down",
		"glitch", "defect", "malfunction", "issue", "problem",
	}
	bugCount := 0
	for _, kw := range bugKeywords {
		if strings.Contains(combined, kw) {
			bugCount++
		}
	}
	if bugCount >= 2 {
		return "bug"
	}

	// Invalid indicators
	invalidKeywords := []string{
		"iron man", "pizza", "weather", "movie", "actor", "actress",
		"thank you for helping", "thanks for your help",
	}
	for _, kw := range invalidKeywords {
		if strings.Contains(combined, kw) {
			return "invalid"
		}
	}

	// Check for out-of-scope / gratitude messages
	if isGratitude(combined) {
		return "invalid"
	}

	// Default: product issue (most common)
	return "product_issue"
}

func isGratitude(text string) bool {
	gratitudePatterns := []string{
		"thank you", "thanks", "appreciate", "grateful",
	}
	words := strings.Fields(text)
	if len(words) < 10 { // Short messages
		for _, p := range gratitudePatterns {
			if strings.Contains(text, p) {
				return true
			}
		}
	}
	return false
}
