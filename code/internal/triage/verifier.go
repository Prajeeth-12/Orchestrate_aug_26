package triage

import (
	"math"
	"strings"
	"support-triage/internal/corpus"
	"unicode"
)

// VerifyGrounding independently checks if the LLM's response is actually
// grounded in the retrieved corpus chunks.
func VerifyGrounding(response string, chunks []corpus.ScoredChunk) float64 {
	return VerifyGroundingTripleCheck(response, chunks, nil, "")
}

// VerifyGroundingTripleCheck performs a more rigorous validation using:
// 1. Lexical Token Overlap (n-grams)
// 2. Citation Presence (Are the cited documents actually in the context?)
// 3. Semantic Similarity (Optional, if embedder is provided)
func VerifyGroundingTripleCheck(response string, chunks []corpus.ScoredChunk, embedder corpus.EmbeddingClient, model string) float64 {
	if len(chunks) == 0 || response == "" {
		return 0.0
	}

	// 1. Lexical Overlap
	lexicalScore := calculateLexicalOverlap(response, chunks)

	// 2. Citation Check
	citationScore := calculateCitationScore(response, chunks)

	// 3. Semantic Similarity (if embedder available)
	semanticScore := 0.0
	if embedder != nil && model != "" {
		semanticScore = calculateSemanticSimilarity(response, chunks, embedder, model)
	} else {
		semanticScore = lexicalScore // Fallback to lexical if no embedder
	}

	// Weighted combination: Lexical (40%), Citation (20%), Semantic (40%)
	// If no embedder, Lexical (80%), Citation (20%)
	var finalScore float64
	if embedder != nil {
		finalScore = (lexicalScore * 0.4) + (citationScore * 0.2) + (semanticScore * 0.4)
	} else {
		finalScore = (lexicalScore * 0.8) + (citationScore * 0.2)
	}

	return math.Min(1.0, finalScore)
}

func calculateLexicalOverlap(response string, chunks []corpus.ScoredChunk) float64 {
	responseTokens := VerifierTokenize(response)
	if len(responseTokens) == 0 {
		return 0.0
	}

	corpusTokenSet := make(map[string]bool)
	for _, sc := range chunks {
		for _, t := range VerifierTokenize(sc.Chunk.Text) {
			corpusTokenSet[t] = true
		}
		for _, t := range VerifierTokenize(sc.Chunk.Title) {
			corpusTokenSet[t] = true
		}
	}

	matchCount := 0
	for _, t := range responseTokens {
		if corpusTokenSet[t] {
			matchCount++
		}
	}
	return float64(matchCount) / float64(len(responseTokens))
}

func calculateCitationScore(response string, chunks []corpus.ScoredChunk) float64 {
	// Simple check: how many unique titles from the chunks are mentioned (even partially) in the response
	if len(chunks) == 0 {
		return 0.0
	}
	mentions := 0
	for _, sc := range chunks {
		// If the title is long, use the first few words as a signature
		titleWords := strings.Fields(sc.Chunk.Title)
		if len(titleWords) > 3 {
			signature := strings.Join(titleWords[:3], " ")
			if strings.Contains(strings.ToLower(response), strings.ToLower(signature)) {
				mentions++
			}
		} else if strings.Contains(strings.ToLower(response), strings.ToLower(sc.Chunk.Title)) {
			mentions++
		}
	}
	// We don't expect ALL chunks to be cited, but at least one high-score one should be relevant
	if mentions > 0 {
		return 1.0
	}
	return 0.0
}

func calculateSemanticSimilarity(response string, chunks []corpus.ScoredChunk, embedder corpus.EmbeddingClient, model string) float64 {
	respVec, err := embedder.Embed(model, response)
	if err != nil {
		return 0.0
	}

	// Compare against the best chunk's vector (if available)
	maxSim := 0.0
	for _, sc := range chunks {
		if len(sc.Embedding) == 0 {
			continue
		}
		sim := cosineSimilarity(respVec, sc.Embedding)
		if sim > maxSim {
			maxSim = sim
		}
	}
	return maxSim
}

func cosineSimilarity(a, b []float32) float64 {
	if len(a) != len(b) || len(a) == 0 {
		return 0.0
	}
	var dotProduct, normA, normB float64
	for i := range a {
		dotProduct += float64(a[i]) * float64(b[i])
		normA += float64(a[i]) * float64(a[i])
		normB += float64(b[i]) * float64(b[i])
	}
	if normA == 0 || normB == 0 {
		return 0.0
	}
	return dotProduct / (math.Sqrt(normA) * math.Sqrt(normB))
}

// VerifierTokenize splits text into lowercase tokens, filtering stopwords and short tokens.
func VerifierTokenize(text string) []string {
	text = strings.ToLower(text)
	words := strings.FieldsFunc(text, func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	})

	var tokens []string
	for _, w := range words {
		if len(w) < 3 || verifierStopWords[w] {
			continue
		}
		tokens = append(tokens, w)
	}
	return tokens
}

var verifierStopWords = map[string]bool{
	"the": true, "and": true, "for": true, "are": true, "but": true,
	"not": true, "you": true, "all": true, "can": true, "had": true,
	"her": true, "was": true, "one": true, "our": true, "out": true,
	"has": true, "have": true, "from": true, "been": true, "some": true,
	"them": true, "than": true, "its": true, "over": true, "into": true,
	"that": true, "this": true, "with": true, "will": true, "each": true,
	"make": true, "like": true, "just": true, "your": true, "also": true,
	"about": true, "would": true, "there": true, "their": true, "what": true,
	"which": true, "could": true, "other": true, "were": true, "more": true,
	"after": true, "please": true, "contact": true, "support": true,
	"here": true, "when": true, "where": true, "while": true, "should": true,
	"these": true, "those": true, "whose": true, "because": true, "since": true,
	"until": true, "unless": true, "through": true, "between": true, "against": true,
	"during": true, "without": true, "before": true, "per": true, "get": true, "got": true,
}
