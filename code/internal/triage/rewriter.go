package triage

import (
	"fmt"
	"strings"
	"support-triage/internal/config"
	"support-triage/internal/llm"
)

const rewritePrompt = `You are a query optimizer for a support ticket retrieval system. Your job is to rewrite the user's support query to maximize retrieval accuracy.

Rules:
1. Fix typos and spelling errors.
2. Expand abbreviations (e.g., "HR" → "HackerRank", "txn" → "transaction").
3. Remove filler words.
4. Preserve the core intent and technical terms.
5. If the query mentions a specific product/feature, keep that name exact.
6. CRITICAL: If the user is asking for multiple independent things (e.g., "My card was stolen and I want to increase my limit"), split them into separate, self-contained queries on new lines.

Output ONLY the rewritten queries, one per line. No explanation, no preamble, no bullet points.`

// RewriteQuery uses a lightweight LLM call to normalize and expand a user's support query
// for better retrieval. Uses the backup model for speed.
func RewriteQuery(client *llm.Client, issue, subject, company string) string {
	// Build input
	raw := issue
	if subject != "" {
		raw = subject + ": " + issue
	}

	if client == nil {
		return raw
	}

	// Skip rewriting for very short or very clean queries
	wordCount := len(strings.Fields(raw))
	if wordCount < config.RewriterMinWords || wordCount > config.RewriterMaxWords {
		return raw
	}

	userPrompt := fmt.Sprintf("Company: %s\nOriginal query: %s\n\nRewritten query:", company, raw)

	rewritten, err := client.GenerateWithBackup(rewritePrompt, userPrompt)
	if err != nil {
		// Fallback: return original query
		return raw
	}

	rewritten = strings.TrimSpace(rewritten)

	// Remove any quotes the model might wrap around the output (do this BEFORE
	// the length check — quoted short strings would otherwise bypass the guard).
	rewritten = strings.Trim(rewritten, "\"'`")
	rewritten = strings.TrimSpace(rewritten)

	// Sanity check: if rewriting produced garbage or empty string, use original
	if len(rewritten) < 10 || float64(len(rewritten)) > float64(len(raw))*config.RewriterLengthMaxMul {
		return raw
	}

	return rewritten
}
