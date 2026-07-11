package corpus

import (
	"encoding/gob"
	"fmt"
	"math"
	"os"
	"sort"
	"sync"
)

// EmbeddingClient is the interface needed to generate embeddings.
type EmbeddingClient interface {
	Embed(model, text string) ([]float32, error)
}

// GenerateEmbeddingsConcurrent generates embeddings for chunks in parallel.
func GenerateEmbeddingsConcurrent(client EmbeddingClient, model string, chunks []Chunk, concurrency int) ([][]float32, error) {
	embeddings := make([][]float32, len(chunks))
	var wg sync.WaitGroup
	var mu sync.Mutex
	var firstErr error

	// Channel to feed chunk indices
	jobs := make(chan int, len(chunks))
	for i := range chunks {
		jobs <- i
	}
	close(jobs)

	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for idx := range jobs {
				mu.Lock()
				if firstErr != nil {
					mu.Unlock()
					return
				}
				mu.Unlock()

				vec, err := client.Embed(model, chunks[idx].Text)
				if err != nil {
					mu.Lock()
					if firstErr == nil {
						firstErr = err
					}
					mu.Unlock()
					return
				}

				mu.Lock()
				embeddings[idx] = vec
				mu.Unlock()
			}
		}()
	}

	wg.Wait()
	return embeddings, firstErr
}

// VectorIndex stores embeddings for chunks and provides semantic search.
type VectorIndex struct {
	Chunks     []Chunk
	Embeddings [][]float32
}

// vectorCache is the serializable form of the vector index.
type vectorCache struct {
	ChunkCount int
	Embeddings [][]float32
}

// NewVectorIndex creates a new vector index.
func NewVectorIndex(chunks []Chunk, embeddings [][]float32) *VectorIndex {
	return &VectorIndex{
		Chunks:     chunks,
		Embeddings: embeddings,
	}
}

// SaveToDisk persists the embedding vectors to a gob file for fast reload.
func (vi *VectorIndex) SaveToDisk(path string) error {
	file, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create cache file: %w", err)
	}
	defer file.Close()

	cache := vectorCache{
		ChunkCount: len(vi.Chunks),
		Embeddings: vi.Embeddings,
	}

	enc := gob.NewEncoder(file)
	if err := enc.Encode(cache); err != nil {
		return fmt.Errorf("encode cache: %w", err)
	}

	return nil
}

// LoadEmbeddingsFromDisk loads cached embeddings if the chunk count matches.
// Returns the embeddings and true if cache is valid, nil and false otherwise.
func LoadEmbeddingsFromDisk(path string, expectedChunkCount int) ([][]float32, bool) {
	file, err := os.Open(path)
	if err != nil {
		return nil, false
	}
	defer file.Close()

	var cache vectorCache
	dec := gob.NewDecoder(file)
	if err := dec.Decode(&cache); err != nil {
		return nil, false
	}

	// Invalidate cache if chunk count changed (corpus was modified)
	if cache.ChunkCount != expectedChunkCount {
		return nil, false
	}

	if len(cache.Embeddings) != expectedChunkCount {
		return nil, false
	}

	return cache.Embeddings, true
}

// Search finds the top K most semantically similar chunks.
func (vi *VectorIndex) Search(queryVector []float32, topK int, domain string) []ScoredChunk {
	if vi == nil || topK <= 0 || len(queryVector) == 0 {
		return nil
	}

	var results []ScoredChunk

	limit := len(vi.Embeddings)
	if len(vi.Chunks) < limit {
		limit = len(vi.Chunks)
	}

	for i := 0; i < limit; i++ {
		emb := vi.Embeddings[i]
		// Filter by domain if specified
		if domain != "" && domain != "all" && vi.Chunks[i].Domain != domain {
			continue
		}

		score := CosineSimilarity(queryVector, emb)
		results = append(results, ScoredChunk{
			Chunk:     vi.Chunks[i],
			Score:     float64(score),
			Embedding: emb,
		})
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Score > results[j].Score
	})

	if len(results) > topK {
		results = results[:topK]
	}

	return results
}

// cosineSimilarity calculates the cosine similarity between two vectors.
func CosineSimilarity(a, b []float32) float32 {
	if len(a) != len(b) {
		return 0
	}

	var dotProduct, normA, normB float32
	for i := 0; i < len(a); i++ {
		dotProduct += a[i] * b[i]
		normA += a[i] * a[i]
		normB += b[i] * b[i]
	}

	if normA == 0 || normB == 0 {
		return 0
	}

	return dotProduct / (float32(math.Sqrt(float64(normA))) * float32(math.Sqrt(float64(normB))))
}
