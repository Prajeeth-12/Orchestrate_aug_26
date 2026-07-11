package triage

import (
	"strings"
)

// SafetyResult holds the pre-filter decision.
type SafetyResult struct {
	ShouldEscalate  bool
	IsInvalid       bool
	Reason          string
	MatchedTriggers []string
}

// highRiskPatterns are injected/malicious input patterns that trigger immediate
// IsInvalid escalation and bypass the LLM entirely.
//
// NOTE: General support patterns (fraud, account lock-outs, legal threats) are
// intentionally handled by the LLM using corpus-grounded answers rather than
// hard-coded rules, to allow nuanced responses (e.g. Visa stolen card guidance).
var highRiskPatterns = []string{
	// Prompt injection
	"ignore your previous instructions",
	"ignore your instructions",
	"ignore all previous",
	"disregard your instructions",
	"forget your rules",
	"system prompt",
	"reveal your prompt",
	"show your instructions",
	// Destructive / exploit commands
	"delete all files",
	"drop table",
	"rm -rf",
	"format c:",
	"sudo rm",
	"jailbreak",
	// Legal coercion
	"lawsuit",
	"legal action",
	"attorney",
	"lawyer",
	"regulatory complaint",
	"compliance violation",
	// Crisis (routed to human for care reasons)
	"suicide",
	"self-harm",
}

// CheckSafety runs the rule-based pre-filter on a ticket.
func CheckSafety(issue, subject string) SafetyResult {
	combined := strings.ToLower(issue + " " + subject)

	for _, pattern := range highRiskPatterns {
		if strings.Contains(combined, pattern) {
			return SafetyResult{
				ShouldEscalate:  true,
				IsInvalid:       true,
				Reason:          "Detected potentially malicious input or prompt injection attempt",
				MatchedTriggers: []string{pattern},
			}
		}
	}

	return SafetyResult{}
}

// Unique deduplicates a string slice, preserving order.
func Unique(s []string) []string {
	seen := make(map[string]bool, len(s))
	result := make([]string, 0, len(s))
	for _, v := range s {
		if !seen[v] {
			seen[v] = true
			result = append(result, v)
		}
	}
	return result
}
