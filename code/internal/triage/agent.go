package triage

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"support-triage/internal/config"
	"support-triage/internal/corpus"
	"support-triage/internal/llm"
	"support-triage/internal/output"
	"support-triage/internal/prompt"
	"time"
)

// Agent is the core triage agent that orchestrates retrieval, safety checks, and LLM calls.
type Agent struct {
	Index          *corpus.BM25Index
	VectorIndex    *corpus.VectorIndex
	LLMClient      *llm.Client
	TopK           int
	EmbedModel     string
	Cache          *llm.SemanticCache
	StreamCallback func(string)
	// Debug enables writing raw LLM responses to disk for troubleshooting.
	Debug bool
}

// LLMResponse is the JSON schema the LLM returns.
type LLMResponse struct {
	Status         string  `json:"status"`
	ProductArea    string  `json:"product_area"`
	RequestType    string  `json:"request_type"`
	Response       string  `json:"response"`
	Justification  string  `json:"justification"`
	GroundingScore float64 `json:"grounding_score"`
}

// TicketMetrics holds per-ticket processing details for the dashboard.
type TicketMetrics struct {
	TicketIndex       int
	Company           string
	RetrievedChunks   []corpus.ScoredChunk
	GroundingScore    float64
	VerifiedGrounding float64
	SafetyTriggered   bool
	SafetyReason      string
	TopCorpusSection  string
	CacheHit          bool
	Duration          time.Duration
}

// ProcessTicket handles a single support ticket through the full pipeline.
// Named returns ensure the deferred Duration measurement is captured correctly.
func (a *Agent) ProcessTicket(ticket output.Ticket, ticketIdx int) (result output.TriageResult, metrics TicketMetrics) {
	startTime := time.Now()
	metrics = TicketMetrics{TicketIndex: ticketIdx}
	defer func() { metrics.Duration = time.Since(startTime) }()

	// Step 1: Safety pre-filter
	safety := CheckSafety(ticket.Issue, ticket.Subject)

	company := ticket.Company

	// Step 2: Query Rewriting (normalize noisy input for better retrieval)
	queryText := ticket.Issue + " " + ticket.Subject
	rewrittenQuery := RewriteQuery(a.LLMClient, ticket.Issue, ticket.Subject, company)

	// Check cache first (Exact Match) using initial company
	cacheKey := fmt.Sprintf("%s:%s", company, queryText)
	if a.Cache != nil {
		if cached, ok := a.Cache.Get(cacheKey); ok {
			metrics.CacheHit = true
			metrics.Company = company
			result = output.TriageResult{
				Issue:         ticket.Issue,
				Subject:       ticket.Subject,
				Company:       company,
				Response:      cached.Response,
				ProductArea:   cached.ProductArea,
				Status:        cached.Status,
				RequestType:   cached.RequestType,
				Justification: cached.Justification,
			}
			return
		}
	}

	// Generate query embedding for hybrid search AND semantic cache
	var queryVec []float32
	var embedErr error
	if a.VectorIndex != nil && a.LLMClient != nil && a.EmbedModel != "" {
		queryVec, embedErr = a.LLMClient.Embed(a.EmbedModel, queryText)
	}

	// Check cache again (Semantic Match)
	if a.Cache != nil && embedErr == nil && len(queryVec) > 0 {
		if cached, ok := a.Cache.GetSemantic(cacheKey, queryVec); ok {
			metrics.CacheHit = true
			result = output.TriageResult{
				Issue:         ticket.Issue,
				Subject:       ticket.Subject,
				Company:       company,
				Response:      cached.Response,
				ProductArea:   cached.ProductArea,
				Status:        cached.Status,
				RequestType:   cached.RequestType,
				Justification: cached.Justification,
			}
			return
		}
	}

	var retrievedChunks []corpus.ScoredChunk

	// Handle Multi-Request Splitting
	queries := strings.Split(rewrittenQuery, "\n")
	var allRetrieved []corpus.ScoredChunk
	seenChunkIDs := make(map[string]bool)

	companyUnknown := company == "" || company == "None"

	for _, q := range queries {
		q = strings.TrimSpace(q)
		if q == "" {
			continue
		}

		var chunks []corpus.ScoredChunk
		if companyUnknown {
			// Use BM25 for domain inference (faster than vector when company unknown)
			c, domainScores := a.Index.QueryAllDomains(q, a.TopK)
			company = InferCompany(ticket.Issue, ticket.Subject, domainScores)
			companyUnknown = company == "" || company == "None"
			chunks = c
		} else {
			// Hybrid Search using pre-computed embedding when possible
			domain := strings.ToLower(company)
			currentVec := queryVec
			if q != queryText && a.LLMClient != nil && a.EmbedModel != "" {
				currentVec, _ = a.LLMClient.Embed(a.EmbedModel, q)
			}
			chunks = a.HybridSearchWithVector(q, domain, currentVec)
		}

		for _, chunk := range chunks {
			if !seenChunkIDs[chunk.Chunk.ID] {
				allRetrieved = append(allRetrieved, chunk)
				seenChunkIDs[chunk.Chunk.ID] = true
			}
		}
	}

	// Sort by score and keep top results (up to TopK * MultiIntentMaxChunksMul)
	sort.Slice(allRetrieved, func(i, j int) bool {
		return allRetrieved[i].Score > allRetrieved[j].Score
	})

	maxChunks := int(float64(a.TopK) * config.MultiIntentMaxChunksMul)
	if len(allRetrieved) > maxChunks {
		allRetrieved = allRetrieved[:maxChunks]
	}
	retrievedChunks = allRetrieved

	// Recompute cache key using the (now-inferred) company and the rewritten query,
	// so cache entries are stored under the correct domain and a normalised query.
	canonicalQuery := queryText
	for _, q := range queries {
		if q = strings.TrimSpace(q); q != "" {
			canonicalQuery = q
			break
		}
	}
	cacheKey = fmt.Sprintf("%s:%s", company, canonicalQuery)

	metrics.Company = company
	metrics.RetrievedChunks = retrievedChunks
	if len(retrievedChunks) > 0 {
		metrics.TopCorpusSection = retrievedChunks[0].Chunk.Section
	}

	// Step 3: Classify request type
	requestType := ClassifyRequestType(ticket.Issue, ticket.Subject, safety)

	// Step 4: Determine product area from retrieved chunks
	productArea := InferProductArea(retrievedChunks, company)

	// Step 5: Handle safety escalations (skip LLM)
	if safety.ShouldEscalate {
		metrics.SafetyTriggered = true
		metrics.SafetyReason = safety.Reason

		status := "escalated"
		response := "This ticket has been escalated to a human support agent for review."
		justification := safety.Reason

		if safety.IsInvalid {
			requestType = "invalid"
			status = "escalated"
			response = "I'm not sure I fully understand your request. Could you please provide more details or clarify what you need help with? If this is really an issue, I will take the appropriate action."
			justification = "Detected patterns consistent with prompt injection or malicious intent: " + strings.Join(safety.MatchedTriggers, ", ")
		} else {
			response = BuildEscalationResponse(company, safety)
		}

		result = output.TriageResult{
			Issue:         ticket.Issue,
			Subject:       ticket.Subject,
			Company:       company,
			Response:      response,
			ProductArea:   productArea,
			Status:        status,
			RequestType:   requestType,
			Justification: justification,
		}
		return
	}

	// Step 6: Handle invalid/out-of-scope tickets without LLM
	if requestType == "invalid" {
		result = output.TriageResult{
			Issue:         ticket.Issue,
			Subject:       ticket.Subject,
			Company:       company,
			Response:      "I'm not entirely sure how to help with that based on the current information. Could you please clarify your request? If this is really an issue, I will take the appropriate action.",
			ProductArea:   productArea,
			Status:        "replied",
			RequestType:   "invalid",
			Justification: "The ticket does not clearly pertain to supported topics. Asking follow-up questions.",
		}
		return
	}

	// Step 7: Check if we have enough context for a reply
	if len(retrievedChunks) == 0 {
		// No corpus context at all — escalate
		metrics.GroundingScore = 0.1
		result = output.TriageResult{
			Issue:         ticket.Issue,
			Subject:       ticket.Subject,
			Company:       company,
			Response:      "This ticket requires human assistance. We could not find sufficient information in our support documentation to provide a confident answer.",
			ProductArea:   productArea,
			Status:        "escalated",
			RequestType:   requestType,
			Justification: "No relevant corpus documents retrieved. Escalating to human agent.",
		}
		return
	}

	// Step 8: Call LLM with retrieved context
	userPrompt := prompt.BuildUserPrompt(company, ticket.Subject, ticket.Issue, retrievedChunks)

	var rawResponse string
	var err error
	if a.StreamCallback != nil {
		rawResponse, err = a.LLMClient.GenerateStream(prompt.SystemPrompt, userPrompt, a.StreamCallback)
	} else {
		rawResponse, err = a.LLMClient.Generate(prompt.SystemPrompt, userPrompt)
	}

	// Save raw model response for debugging (only when Debug mode is enabled).
	if a.Debug {
		rawDir := filepath.Join(config.DefaultOutputDir, "raw_responses")
		_ = os.MkdirAll(rawDir, 0o755)
		_ = os.WriteFile(filepath.Join(rawDir, fmt.Sprintf("raw_ticket_%d_%d.txt", ticketIdx, time.Now().UnixNano())), []byte(rawResponse), 0o644)
	}

	if err != nil {
		fmt.Printf("\n  ⚠ LLM error: %v — escalating\n", err)
		result = output.TriageResult{
			Issue:         ticket.Issue,
			Subject:       ticket.Subject,
			Company:       company,
			Response:      "This ticket has been escalated to a human support agent due to a processing error.",
			ProductArea:   productArea,
			Status:        "escalated",
			RequestType:   requestType,
			Justification: "LLM processing failed: " + err.Error(),
		}
		return
	}

	// Step 9: Parse LLM JSON response
	llmResult := ParseLLMResponse(rawResponse)
	metrics.GroundingScore = llmResult.GroundingScore

	// Step 9.5: Independent grounding verification (Triple-Check)
	verifiedScore := VerifyGroundingTripleCheck(llmResult.Response, retrievedChunks, a.LLMClient, a.EmbedModel)
	metrics.VerifiedGrounding = verifiedScore

	// Step 9.6: Citation Extraction
	citations := make([]string, 0)
	for _, sc := range retrievedChunks {
		// Only cite if the chunk was highly relevant (or mentioned in justification/response)
		if strings.Contains(strings.ToLower(llmResult.Response), strings.ToLower(sc.Chunk.Title)) ||
			strings.Contains(strings.ToLower(llmResult.Justification), strings.ToLower(sc.Chunk.Title)) {
			citations = append(citations, sc.Chunk.Title)
		}
	}
	// Fallback: If no explicit mentions, cite the top relevant chunk
	if len(citations) == 0 && len(retrievedChunks) > 0 {
		citations = append(citations, retrievedChunks[0].Chunk.Title)
	}

	// Step 10: Validate and apply LLM output
	status := llmResult.Status
	if status != "replied" && status != "escalated" {
		status = "escalated" // default to safe
	}

	rt := llmResult.RequestType
	if rt != "product_issue" && rt != "feature_request" && rt != "bug" && rt != "invalid" {
		rt = requestType // fallback to our classifier
	}

	pa := ValidateProductArea(company, llmResult.ProductArea, productArea)

	resp := llmResult.Response
	if resp == "" {
		resp = "This ticket has been escalated to a human support agent for review."
		status = "escalated"
	}

	just := llmResult.Justification
	if just == "" {
		just = "Processed via LLM with retrieved corpus context."
	}

	// Use the LOWER of LLM self-assessment and verified score for safety
	effectiveGrounding := llmResult.GroundingScore
	if verifiedScore < effectiveGrounding {
		effectiveGrounding = verifiedScore
	}

	// Low effective grounding → escalate
	if effectiveGrounding < config.GroundingThreshold && status == "replied" {
		status = "escalated"
		resp = "This ticket has been escalated to a human support agent. We could not confidently resolve your issue automatically."
		just += fmt.Sprintf(" Grounding verification failed (LLM: %.2f, Verified: %.2f) — escalated for safety.", llmResult.GroundingScore, verifiedScore)
	}

	result = output.TriageResult{
		Issue:         ticket.Issue,
		Subject:       ticket.Subject,
		Company:       company,
		Response:      resp,
		ProductArea:   pa,
		Status:        status,
		RequestType:   rt,
		Justification: just,
		Citations:     citations,
	}

	// Store in cache
	if a.Cache != nil {
		a.Cache.SetWithVector(cacheKey, queryVec, llm.CachedResult{
			Status:        status,
			ProductArea:   pa,
			RequestType:   rt,
			Response:      resp,
			Justification: just,
		})
	}
	return
}

// HybridSearch combines BM25 and Vector search results using Reciprocal Rank Fusion (RRF).
func (a *Agent) HybridSearch(queryText, domain string) []corpus.ScoredChunk {
	var vec []float32
	if a.VectorIndex != nil && a.LLMClient != nil && a.EmbedModel != "" {
		vec, _ = a.LLMClient.Embed(a.EmbedModel, queryText)
	}
	return a.HybridSearchWithVector(queryText, domain, vec)
}

// HybridSearchWithVector performs hybrid search using a pre-computed vector.
func (a *Agent) HybridSearchWithVector(queryText, domain string, queryVector []float32) []corpus.ScoredChunk {
	// BM25 results
	bm25Results := a.Index.Query(queryText, a.TopK*2, domain)

	// Vector results
	var vectorResults []corpus.ScoredChunk
	if a.VectorIndex != nil && len(queryVector) > 0 {
		vectorResults = a.VectorIndex.Search(queryVector, a.TopK*2, domain)
	}

	// If no vector results, return BM25
	if len(vectorResults) == 0 {
		if len(bm25Results) > a.TopK {
			return bm25Results[:a.TopK]
		}
		return bm25Results
	}

	// RRF (Reciprocal Rank Fusion)
	// Score(d) = sum_{r in rankers} 1 / (k + rank(d, r))
	k := config.RRFConstant
	scores := make(map[string]float64)
	chunkMap := make(map[string]corpus.Chunk)

	for rank, res := range bm25Results {
		scores[res.Chunk.ID] += 1.0 / (k + float64(rank+1))
		chunkMap[res.Chunk.ID] = res.Chunk
	}

	for rank, res := range vectorResults {
		scores[res.Chunk.ID] += 1.0 / (k + float64(rank+1))
		chunkMap[res.Chunk.ID] = res.Chunk
	}

	// Convert back to ScoredChunks
	fused := make([]corpus.ScoredChunk, 0, len(scores))
	for id, score := range scores {
		fused = append(fused, corpus.ScoredChunk{
			Chunk: chunkMap[id],
			Score: score,
		})
	}

	sort.Slice(fused, func(i, j int) bool {
		return fused[i].Score > fused[j].Score
	})

	if len(fused) > a.TopK {
		return fused[:a.TopK]
	}
	return fused
}

func ParseLLMResponse(raw string) LLMResponse {
	// Normalize raw response to fix common issues from LLM outputs
	raw = normalizeLLMOutput(raw)
	raw = strings.TrimSpace(raw)

	// Strategy 1: Look for JSON blocks in triple backticks
	re := regexp.MustCompile("(?s)```(?:json)?\\s*(\\{.*?\\})\\s*```")
	matches := re.FindAllStringSubmatch(raw, -1)
	for i := len(matches) - 1; i >= 0; i-- { // Try from last to first
		var result LLMResponse
		if err := json.Unmarshal([]byte(matches[i][1]), &result); err == nil {
			if result.Status != "" {
				return result
			}
		}
	}

	// Strategy 2: Find the first '{' and the last '}' to extract JSON
	start := strings.Index(raw, "{")
	end := strings.LastIndex(raw, "}")
	if start != -1 && end != -1 && end > start {
		jsonStr := raw[start : end+1]
		var result LLMResponse
		if err := json.Unmarshal([]byte(jsonStr), &result); err == nil {
			return result
		}

		// If that fails, try to find the last valid { ... } block
		curr := start
		for {
			nextStart := strings.Index(raw[curr+1:], "{")
			if nextStart == -1 {
				break
			}
			curr = curr + 1 + nextStart
			potentialEnd := strings.LastIndex(raw[curr:], "}")
			if potentialEnd != -1 {
				potentialEnd += curr
				jsonStr := raw[curr : potentialEnd+1]
				var res LLMResponse
				if err := json.Unmarshal([]byte(jsonStr), &res); err == nil {
					if res.Status != "" {
						return res
					}
				}
			}
		}
	}

	// Strategy 3: Try direct parse
	var result LLMResponse
	if err := json.Unmarshal([]byte(raw), &result); err == nil {
		return result
	}

	// Strategy 4: Try to find a balanced JSON object by scanning for matching braces.
	if candidate := findBalancedJSON(raw); candidate != "" {
		var res LLMResponse
		if err := json.Unmarshal([]byte(candidate), &res); err == nil {
			return res
		}
	}

	// Strategy 5: If JSON looks truncated (unbalanced braces), attempt a best-effort repair
	// by extracting from the first '{' to the end and appending closing braces.
	startPos := strings.Index(raw, "{")
	if startPos != -1 {
		fragment := raw[startPos:]
		open := strings.Count(fragment, "{")
		close := strings.Count(fragment, "}")
		if open > close {
			needed := open - close
			repaired := fragment + strings.Repeat("}", needed)
			var res LLMResponse
			if err := json.Unmarshal([]byte(repaired), &res); err == nil {
				return res
			}
		}
	}

	// Strategy 6: Try to parse into a generic map and map common keys to the expected schema.
	var generic map[string]any
	if err := json.Unmarshal([]byte(raw), &generic); err == nil {
		mapped := mapToLLMResponse(generic)
		if mapped.Status != "" || mapped.Response != "" {
			return mapped
		}
	}

	// Also try the repaired fragment if we attempted repair above
	if startPos != -1 {
		fragment := raw[startPos:]
		open := strings.Count(fragment, "{")
		close := strings.Count(fragment, "}")
		if open > close {
			needed := open - close
			repaired := fragment + strings.Repeat("}", needed)
			var generic2 map[string]any
			if err := json.Unmarshal([]byte(repaired), &generic2); err == nil {
				mapped := mapToLLMResponse(generic2)
				if mapped.Status != "" || mapped.Response != "" {
					return mapped
				}
			}
		}
	}

	// Save raw response for debugging to outputs/raw_responses/<timestamp>.txt
	// Best-effort only; ignore errors.
	_ = os.MkdirAll("outputs/raw_responses", 0o755)
	_ = os.WriteFile(fmt.Sprintf("outputs/raw_responses/response_%d.txt", time.Now().UnixNano()), []byte(raw), 0o644)

	// Fallback: Save raw text and escalate by default for safety.
	// Tests and production require that unparseable JSON does not silently
	// produce an automated reply; escalate to human review instead.
	fmt.Printf("  ⚠ JSON parse failed; escalating with plain-text saved. Raw response length: %d\n", len(raw))

	// Use the raw output in the justification for debugging, but mark as escalated
	// and set grounding to 0.0 to force human review.
	return LLMResponse{
		Status:         "escalated",
		Response:       "This ticket has been escalated to a human support agent for review.",
		Justification:  "Failed to parse LLM response into structured format. Raw output saved for debugging.",
		GroundingScore: 0.0,
	}
}

// mapToLLMResponse attempts to extract useful fields from a generic JSON
// object produced by an LLM and map them into the LLMResponse schema.
func mapToLLMResponse(g map[string]any) LLMResponse {
	var r LLMResponse

	// Helper to get string values flexibly, searching nested maps/arrays.
	getString := func(keys ...string) string {
		for _, k := range keys {
			if v := recursiveFind(g, k); v != nil {
				if s, ok := v.(string); ok {
					return s
				}
			}
		}
		return ""
	}

	r.Status = getString("status", "result_status", "state")
	r.ProductArea = getString("product_area", "productArea", "category")
	r.RequestType = getString("request_type", "requestType", "type")

	// Response extraction: prefer `response`, `solution`, `recommended_action` (steps)
	if resp := getString("response", "solution", "answer"); resp != "" {
		r.Response = resp
	} else if ra, ok := g["recommended_action"]; ok {
		switch t := ra.(type) {
		case string:
			r.Response = t
		case []any:
			parts := make([]string, 0, len(t))
			for _, p := range t {
				if s, ok := p.(string); ok {
					parts = append(parts, s)
				}
			}
			r.Response = strings.Join(parts, "\n")
		case map[string]any:
			// try to pull 'steps'
			if steps, ok := t["steps"]; ok {
				if arr, ok := steps.([]any); ok {
					parts := make([]string, 0, len(arr))
					for _, p := range arr {
						if s, ok := p.(string); ok {
							parts = append(parts, s)
						}
					}
					r.Response = strings.Join(parts, "\n")
				}
			}
		}
	}

	if r.Response == "" {
		// Try other possible keys and plural forms
		r.Response = getString("recommended_resolution", "recommended_action_text", "solution_text", "recommended_actions", "recommended_steps")
		if r.Response == "" {
			if v, ok := g["recommended_actions"]; ok {
				if arr, ok := v.([]any); ok {
					parts := make([]string, 0, len(arr))
					for _, p := range arr {
						if s, ok := p.(string); ok {
							parts = append(parts, s)
						}
					}
					r.Response = strings.Join(parts, "\n")
				}
			}
		}
	}

	// Justification extraction
	r.Justification = getString("justification", "analysis", "explanation", "gap_identified", "coverage_gap", "knowledge_base_analysis")

	// Grounding score if present
	if v, ok := g["grounding_score"]; ok {
		switch t := v.(type) {
		case float64:
			r.GroundingScore = t
		case int:
			r.GroundingScore = float64(t)
		}
	} else if r.Response != "" {
		// optimistic default if we extracted a response
		r.GroundingScore = 0.5
	}

	// Fallback status: if empty but we have a response, mark as replied
	if r.Status == "" {
		if r.Response != "" {
			r.Status = "replied"
		} else {
			r.Status = "escalated"
		}
	}

	return r
}

// recursiveFind searches nested maps and arrays for a key and returns its value if found.
func recursiveFind(v any, key string) any {
	switch t := v.(type) {
	case map[string]any:
		if val, ok := t[key]; ok {
			return val
		}
		// search deeper
		for _, vv := range t {
			if found := recursiveFind(vv, key); found != nil {
				return found
			}
		}
	case []any:
		for _, item := range t {
			if found := recursiveFind(item, key); found != nil {
				return found
			}
		}
	}
	return nil
}

// findBalancedJSON attempts to locate the last balanced JSON object in the string
// by scanning for '{' and matching '}' with a simple counter. Returns the JSON
// substring or empty string if none found.
func findBalancedJSON(s string) string {
	runes := []rune(s)
	n := len(runes)
	for i := 0; i < n; i++ {
		if runes[i] != '{' {
			continue
		}
		depth := 0
		for j := i; j < n; j++ {
			if runes[j] == '{' {
				depth++
			} else if runes[j] == '}' {
				depth--
				if depth == 0 {
					return string(runes[i : j+1])
				}
			}
		}
	}
	return ""
}

// normalizeLLMOutput attempts to fix common LLM output issues that break JSON
// parsing: zero-width/invisible characters, smart quotes, fullwidth braces,
// and HTML entities. It returns a cleaned string suitable for JSON extraction.
func normalizeLLMOutput(s string) string {
	// Remove common invisible/zero-width characters
	invisibles := []rune{0x200B, 0x200C, 0x200D, 0xFEFF, 0x2060}
	b := make([]rune, 0, len(s))
	for _, r := range s {
		skip := false
		for _, inv := range invisibles {
			if r == inv {
				skip = true
				break
			}
		}
		if !skip {
			b = append(b, r)
		}
	}
	out := string(b)

	// Replace fullwidth/bracket-like unicode with ASCII equivalents
	replacer := strings.NewReplacer(
		"“", "\"",
		"”", "\"",
		"‘", "'",
		"’", "'",
		"‒", "-",
		"–", "-",
		"—", "-",
		"｛", "{",
		"｝", "}",
		"﹙", "(",
		"﹚", ")",
		"＆", "&",
	)
	out = replacer.Replace(out)

	// Unescape common HTML entities if present
	entityReplacer := strings.NewReplacer(
		"&quot;", "\"",
		"&amp;", "&",
		"&lt;", "<",
		"&gt;", ">",
		"&apos;", "'",
		"&#39;", "'",
	)
	out = entityReplacer.Replace(out)

	// Trim BOM and non-printable prefix/suffix
	out = strings.Trim(out, "\uFEFF\u00A0\n\r \t")
	return out
}

func BuildEscalationResponse(company string, safety SafetyResult) string {
	var sb strings.Builder
	sb.WriteString("This ticket has been escalated to a human support agent for immediate review. ")

	for _, cat := range safety.MatchedTriggers {
		switch {
		case strings.Contains(cat, "fraud") || strings.Contains(cat, "unauthorized") || strings.Contains(cat, "stolen"):
			sb.WriteString("For fraud or unauthorized transaction concerns, please contact your card issuer or bank immediately. ")
			if company == "Visa" {
				sb.WriteString("Visa India cardholders can call 000-800-100-1219. Visa's Global Customer Assistance Service is available 24/7 at +1 303 967 1090. ")
			}
		case strings.Contains(cat, "identity"):
			sb.WriteString("For identity theft concerns, please contact your financial institution and local authorities immediately. ")
		case strings.Contains(cat, "access") || strings.Contains(cat, "locked"):
			sb.WriteString("Account access issues require verification by a human agent. ")
		case strings.Contains(cat, "payment") || strings.Contains(cat, "refund") || strings.Contains(cat, "order"):
			sb.WriteString("Payment and billing matters require review by our billing team. ")
		case strings.Contains(cat, "subscription") || strings.Contains(cat, "pause") || strings.Contains(cat, "cancel"):
			sb.WriteString("Subscription changes require human authorization. ")
		}
	}

	return sb.String()
}

func ValidateProductArea(company, chosen, fallback string) string {
	allowed := map[string][]string{
		"HackerRank": {"screen", "community", "general_support"},
		"Claude":     {"conversation_management", "privacy", "general_support"},
		"Visa":       {"travel_support", "general_support"},
	}

	areas, ok := allowed[company]
	if !ok {
		return fallback
	}

	chosen = strings.ToLower(strings.TrimSpace(chosen))
	for _, a := range areas {
		if chosen == a {
			return chosen
		}
	}

	// If chosen contains an allowed keyword, use that
	for _, a := range areas {
		if strings.Contains(chosen, a) {
			return a
		}
	}

	return fallback
}
