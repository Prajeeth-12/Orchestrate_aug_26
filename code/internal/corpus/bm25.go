package corpus

import (
	"encoding/gob"
	"math"
	"os"
	"sort"
	"strings"
	"unicode"
)

func (idx *BM25Index) SaveToDisk(path string) error {
	file, err := os.Create(path)
	if err != nil {
		return err
	}
	defer file.Close()
	return gob.NewEncoder(file).Encode(idx)
}

func LoadBM25IndexFromDisk(path string) (*BM25Index, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	var idx BM25Index
	if err := gob.NewDecoder(file).Decode(&idx); err != nil {
		return nil, err
	}
	return &idx, nil
}

// BM25Index is a keyword-based retrieval index using the Okapi BM25 algorithm.
type BM25Index struct {
	Chunks    []Chunk
	K1        float64
	B         float64
	AvgDocLen float64

	// Inverted index: term -> list of (chunkIndex, termFrequency)
	InvertedIndex map[string][]Posting

	// Document lengths (token count per chunk)
	DocLengths []int

	// IDF cache
	IDF map[string]float64

	// Total number of documents
	NumDocs int
}

type Posting struct {
	DocIdx int
	Freq   int
}

// ScoredChunk holds a chunk with its BM25 or semantic relevance score.
type ScoredChunk struct {
	Chunk     Chunk
	Score     float64
	Embedding []float32
}

// NewBM25Index builds a BM25 index from a set of chunks.
func NewBM25Index(chunks []Chunk) *BM25Index {
	idx := &BM25Index{
		Chunks:        chunks,
		K1:            1.5,
		B:             0.75,
		InvertedIndex: make(map[string][]Posting),
		DocLengths:    make([]int, len(chunks)),
		IDF:           make(map[string]float64),
		NumDocs:       len(chunks),
	}

	totalLen := 0
	for i, chunk := range chunks {
		// Include title in the indexed text for better matching
		text := chunk.Title + " " + chunk.Title + " " + chunk.Text // title boosted 2x
		tokens := Tokenize(text)
		idx.DocLengths[i] = len(tokens)
		totalLen += len(tokens)

		// Count term frequencies
		freqs := make(map[string]int)
		for _, t := range tokens {
			freqs[t]++
		}
		for term, freq := range freqs {
			idx.InvertedIndex[term] = append(idx.InvertedIndex[term], Posting{
				DocIdx: i,
				Freq:   freq,
			})
		}
	}

	if len(chunks) > 0 {
		idx.AvgDocLen = float64(totalLen) / float64(len(chunks))
	}

	// Precompute IDF for all terms
	for term, postings := range idx.InvertedIndex {
		df := len(postings)
		idx.IDF[term] = math.Log(1 + (float64(idx.NumDocs)-float64(df)+0.5)/(float64(df)+0.5))
	}

	return idx
}

// Query returns the top-K chunks matching the query, optionally filtered by domain.
func (idx *BM25Index) Query(query string, topK int, domain string) []ScoredChunk {
	if idx == nil || topK <= 0 {
		return nil
	}

	queryTokens := Tokenize(query)
	if len(queryTokens) == 0 {
		return nil
	}

	scores := make([]float64, idx.NumDocs)

	for _, qt := range queryTokens {
		idfVal, ok := idx.IDF[qt]
		if !ok {
			continue
		}

		for _, p := range idx.InvertedIndex[qt] {
			if domain != "" && idx.Chunks[p.DocIdx].Domain != domain {
				continue
			}
			tf := float64(p.Freq)
			dl := float64(idx.DocLengths[p.DocIdx])
			numerator := tf * (idx.K1 + 1)
			denominator := tf + idx.K1*(1-idx.B+idx.B*dl/idx.AvgDocLen)
			scores[p.DocIdx] += idfVal * numerator / denominator
		}
	}

	// Collect scored results
	var results []ScoredChunk
	for i, score := range scores {
		if score > 0 {
			if domain != "" && idx.Chunks[i].Domain != domain {
				continue
			}
			results = append(results, ScoredChunk{
				Chunk: idx.Chunks[i],
				Score: score,
			})
		}
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Score > results[j].Score
	})

	if len(results) > topK {
		results = results[:topK]
	}

	return results
}

// QueryAllDomains returns scored chunks and a domain score map for company inference.
func (idx *BM25Index) QueryAllDomains(query string, topK int) ([]ScoredChunk, map[string]float64) {
	if idx == nil || topK <= 0 {
		return nil, map[string]float64{}
	}

	results := idx.Query(query, topK*3, "")

	domainScores := make(map[string]float64)
	for _, r := range results {
		domainScores[r.Chunk.Domain] += r.Score
	}

	if len(results) > topK {
		results = results[:topK]
	}

	return results, domainScores
}

// stopwords that don't carry retrieval signal
var stopWords = map[string]bool{
	"the": true, "a": true, "an": true, "is": true, "are": true,
	"was": true, "were": true, "be": true, "been": true, "being": true,
	"have": true, "has": true, "had": true, "do": true, "does": true,
	"did": true, "will": true, "would": true, "shall": true, "should": true,
	"may": true, "might": true, "can": true, "could": true, "must": true,
	"i": true, "me": true, "my": true, "we": true, "our": true,
	"you": true, "your": true, "he": true, "she": true, "it": true,
	"they": true, "them": true, "their": true, "this": true, "that": true,
	"these": true, "those": true, "of": true, "in": true, "to": true,
	"for": true, "with": true, "on": true, "at": true, "by": true,
	"from": true, "as": true, "into": true, "about": true, "and": true,
	"but": true, "or": true, "not": true, "no": true, "if": true,
	"so": true, "than": true, "too": true, "very": true, "just": true,
	"also": true, "what": true, "how": true, "when": true, "where": true,
	"which": true, "who": true, "whom": true, "why": true,
	"all": true, "each": true, "every": true, "both": true, "few": true,
	"more": true, "most": true, "some": true, "any": true, "other": true,
	"then": true, "there": true, "here": true, "up": true, "out": true,
}

func Tokenize(text string) []string {
	text = strings.ToLower(text)
	words := strings.FieldsFunc(text, func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	})

	var tokens []string
	for _, w := range words {
		if len(w) < 2 {
			continue
		}
		if stopWords[w] {
			continue
		}
		tokens = append(tokens, w)
	}
	return tokens
}
