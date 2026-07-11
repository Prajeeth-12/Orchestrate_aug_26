package llm

import (
	"encoding/gob"
	"fmt"
	"os"
	"support-triage/internal/config"
	"sync"
)

// CachedResult stores a triage result for semantic caching.
type CachedResult struct {
	Status        string
	ProductArea   string
	RequestType   string
	Response      string
	Justification string
}

// CacheEntry stores a query vector alongside its cached result.
type CacheEntry struct {
	Key         string
	QueryVector []float32
	Result      CachedResult
}

// SemanticCache provides both exact-match and vector-similarity caching.
// When a query vector is provided, it checks cosine similarity against stored entries.
type SemanticCache struct {
	mu        sync.RWMutex
	Exact     map[string]CachedResult
	Entries   []CacheEntry
	Threshold float32 // cosine similarity threshold
	MaxSize   int
}

// CacheFormatVersion is incremented when the cache on-disk format or
// the interpretation of cached results changes in a breaking way.
const CacheFormatVersion = 2

// SaveToDisk persists the cache to a gob file.
func (c *SemanticCache) SaveToDisk(path string) error {
	c.mu.RLock()
	defer c.mu.RUnlock()

	file, err := os.Create(path)
	if err != nil {
		return err
	}
	defer file.Close()

	data := struct {
		Version int
		Exact   map[string]CachedResult
		Entries []CacheEntry
	}{
		Version: CacheFormatVersion,
		Exact:   c.Exact,
		Entries: c.Entries,
	}

	enc := gob.NewEncoder(file)
	return enc.Encode(data)
}

// LoadFromDisk loads the cache from a gob file.
func (c *SemanticCache) LoadFromDisk(path string) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	file, err := os.Open(path)
	if err != nil {
		return err
	}
	defer file.Close()

	var data struct {
		Version int
		Exact   map[string]CachedResult
		Entries []CacheEntry
	}

	dec := gob.NewDecoder(file)
	if err := dec.Decode(&data); err != nil {
		return err
	}

	// If cache versions mismatch, treat as a load failure so caller will
	// regenerate the cache using the current code paths.
	if data.Version != CacheFormatVersion {
		return fmt.Errorf("semantic cache version mismatch: got %d, want %d", data.Version, CacheFormatVersion)
	}

	c.Exact = data.Exact
	c.Entries = data.Entries
	return nil
}

// NewSemanticCache creates a new semantic cache with vector similarity support.
func NewSemanticCache() *SemanticCache {
	return &SemanticCache{
		Exact:     make(map[string]CachedResult),
		Entries:   make([]CacheEntry, 0, 256),
		Threshold: config.CacheSimilarityThreshold,
		MaxSize:   512,
	}
}

// Get retrieves a result from the cache using exact key match.
func (c *SemanticCache) Get(queryKey string) (CachedResult, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	res, ok := c.Exact[queryKey]
	return res, ok
}

// GetSemantic retrieves a result using vector similarity if no exact match exists.
func (c *SemanticCache) GetSemantic(queryKey string, queryVec []float32) (CachedResult, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	// Try exact match first
	if res, ok := c.Exact[queryKey]; ok {
		return res, true
	}
	// Try vector similarity
	if len(queryVec) > 0 {
		bestScore := float32(0.0)
		bestIdx := -1
		for i, entry := range c.Entries {
			if len(entry.QueryVector) != len(queryVec) {
				continue
			}
			sim := CosineSimF32(queryVec, entry.QueryVector)
			if sim > bestScore {
				bestScore = sim
				bestIdx = i
			}
		}
		if bestIdx >= 0 && bestScore >= c.Threshold {
			return c.Entries[bestIdx].Result, true
		}
	}

	return CachedResult{}, false
}

// Set stores a result in both exact and vector caches.
func (c *SemanticCache) Set(queryKey string, res CachedResult) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.Exact[queryKey] = res
}

// SetWithVector stores a result with its associated query vector for semantic matching.
func (c *SemanticCache) SetWithVector(queryKey string, queryVec []float32, res CachedResult) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.Exact[queryKey] = res

	// Evict oldest if at capacity
	if len(c.Entries) >= c.MaxSize {
		c.Entries = c.Entries[1:]
	}

	c.Entries = append(c.Entries, CacheEntry{
		Key:         queryKey,
		QueryVector: queryVec,
		Result:      res,
	})

}

// CosineSimF32 computes cosine similarity between two float32 vectors.
func CosineSimF32(a, b []float32) float32 {

	var dot, normA, normB float32
	for i := range a {
		dot += a[i] * b[i]
		normA += a[i] * a[i]
		normB += b[i] * b[i]
	}
	if normA == 0 || normB == 0 {
		return 0
	}
	return dot / (Sqrt32(normA) * Sqrt32(normB))
}

func Sqrt32(x float32) float32 {
	if x <= 0 {
		return 0
	}
	// Newton's method for float32 sqrt
	z := x / 2
	for i := 0; i < 10; i++ {
		z = (z + x/z) / 2
	}
	return z
}
