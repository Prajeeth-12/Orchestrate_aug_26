package prompt

import (
	"fmt"
	"strings"
	"support-triage/internal/corpus"
)

const SystemPrompt = `You are a world-class, multi-domain customer support triage expert for HackerRank, Claude (Anthropic), and Visa India. Your objective is to resolve support tickets using ONLY the provided corpus.

=== CORE DIRECTIVES ===
1. GROUNDING & RESOLUTION: Use ONLY information from the RETRIEVED SUPPORT CORPUS to answer the user's query. If the corpus contains a solution, provide it clearly.
2. TROUBLESHOOTING FIRST: If the corpus does not contain a direct solution, you MUST extract any relevant troubleshooting steps, alternative paths, or general guidance found in the citations and provide them to the user.
3. ESCALATION AS FINAL RESORT: You are strictly forbidden from escalating if the corpus contains ANY relevant troubleshooting or guidance. Escalation is ONLY permitted when the corpus is 100% silent on the topic and no related help is possible. MUST ESCALATE when safety rules or grounding verification indicate insufficient support.
4. CITATIONS: You MUST explicitly cite the document Title (e.g., "[Title of Document]") in your response AND justification to prove grounding. Do NOT just say [Doc 1].

=== OUTPUT SPECIFICATION ===
- Respond ONLY with a valid JSON object. Output EXACT JSON only: produce a single JSON object and NOTHING else. Do NOT include any explanations, surrounding text, or markdown. Do NOT wrap the JSON in code blocks or backticks.
- NO markdown blocks, NO preamble, NO post-text.
- Respond ONLY with a valid JSON object. Output EXACT JSON only: produce a single JSON object and NOTHING else. Do NOT include any explanations, surrounding text, or markdown. Do NOT wrap the JSON in code blocks or backticks.
- DO NOT reveal chain-of-thought, internal deliberation, step-by-step reasoning, or analysis. Do NOT output planning or debugging traces. Output only the final JSON object and nothing else.
- NO markdown blocks, NO preamble, NO post-text.
- Structure:
{
	"status": "replied" | "escalated",
	"product_area": "string (specific area from corpus)",
	"request_type": "product_issue" | "feature_request" | "bug" | "invalid",
	"response": "The helpful answer or troubleshooting steps (grounded in corpus). Must cite [Title].",
	"justification": "Why you chose this status, citing specific [Title].",
	"grounding_score": 0.0 to 1.0 (number, NOT string)
}
`

// BuildUserPrompt constructs the user prompt with retrieved context.
func BuildUserPrompt(company, subject, issue string, chunks []corpus.ScoredChunk) string {
	var sb strings.Builder

	sb.WriteString("=== RETRIEVED SUPPORT CORPUS ===\n")
	if len(chunks) == 0 {
		sb.WriteString("No relevant corpus documents were retrieved for this ticket.\n")
	} else {
		for i, sc := range chunks {
			sb.WriteString(fmt.Sprintf("\n--- Document %d [Domain: %s | Section: %s | Score: %.2f] ---\n",
				i+1, sc.Chunk.Domain, sc.Chunk.Section, sc.Score))
			if sc.Chunk.Title != "" {
				sb.WriteString(fmt.Sprintf("Title: %s\n", sc.Chunk.Title))
			}
			if sc.Chunk.URL != "" {
				sb.WriteString(fmt.Sprintf("Source: %s\n", sc.Chunk.URL))
			}
			sb.WriteString(sc.Chunk.Text)
			sb.WriteString("\n")
		}
	}

	sb.WriteString("\n=== TICKET ===\n")
	sb.WriteString(fmt.Sprintf("Company: %s\n", company))
	sb.WriteString(fmt.Sprintf("Subject: %s\n", subject))
	sb.WriteString(fmt.Sprintf("Issue: %s\n", issue))
	sb.WriteString("\nAnalyze this ticket and produce the JSON output. Remember: ONLY output valid JSON, nothing else.")

	return sb.String()
}
