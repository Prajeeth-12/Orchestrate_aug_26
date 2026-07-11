package corpus

import (
	"fmt"
	"strings"
)

// Chunk represents a retrievable unit of text from a document.
type Chunk struct {
	ID       string
	DocID    string
	Domain   string
	Section  string
	Title    string
	URL      string
	Text     string
	FilePath string
}

const (
	MaxChunkTokens = 200
	MinChunkTokens = 30
)

func ChunkDocuments(docs []Document) []Chunk {
	var chunks []Chunk
	for _, doc := range docs {
		docChunks := ChunkDocument(doc)
		for i := range docChunks {
			if len(docChunks[i].Text) > 3000 {
				docChunks[i].Text = docChunks[i].Text[:3000]
			}
		}
		chunks = append(chunks, docChunks...)
	}
	return chunks
}

func ChunkDocument(doc Document) []Chunk {
	body := CleanMarkdown(doc.Body)
	if len(strings.Fields(body)) < MinChunkTokens {
		if strings.TrimSpace(body) == "" {
			return nil
		}
		return []Chunk{{
			ID:       fmt.Sprintf("%s-c0", doc.ID),
			DocID:    doc.ID,
			Domain:   doc.Domain,
			Section:  doc.Section,
			Title:    doc.Title,
			URL:      doc.URL,
			Text:     body,
			FilePath: doc.FilePath,
		}}
	}

	paragraphs := SplitIntoParagraphs(body)
	var chunks []Chunk
	var current strings.Builder
	currentTokens := 0
	chunkIdx := 0

	// Track paragraphs for overlap
	var currentParas []string

	for _, p := range paragraphs {
		subParas := []string{p}
		// If a paragraph is too long, split it by sentence or roughly by word count
		if len(strings.Fields(p)) > MaxChunkTokens {
			subParas = SplitLongParagraph(p, MaxChunkTokens)
		}

		for _, para := range subParas {
			paraTokens := len(strings.Fields(para))
			if paraTokens == 0 {
				continue
			}

			if currentTokens+paraTokens > MaxChunkTokens && currentTokens > 0 {
				chunks = append(chunks, Chunk{
					ID:       fmt.Sprintf("%s-c%d", doc.ID, chunkIdx),
					DocID:    doc.ID,
					Domain:   doc.Domain,
					Section:  doc.Section,
					Title:    doc.Title,
					URL:      doc.URL,
					Text:     strings.TrimSpace(current.String()),
					FilePath: doc.FilePath,
				})
				chunkIdx++

				// Sliding window: carry the last ~20% of tokens as overlap
				overlapTarget := MaxChunkTokens / 5 // 50 tokens
				overlapPrefix := ""
				overlapTokens := 0

				// Walk backwards through paragraphs/sub-paragraphs we've added to current chunk
				for j := len(currentParas) - 1; j >= 0; j-- {
					pt := len(strings.Fields(currentParas[j]))
					if overlapTokens+pt > overlapTarget && overlapTokens > 0 {
						break
					}
					// If this paragraph alone exceeds the overlap target, take only its last
					// `overlapTarget` words to avoid duplicating very large blocks.
					if pt > overlapTarget {
						words := strings.Fields(currentParas[j])
						start := pt - overlapTarget
						if start < 0 {
							start = 0
						}
						suffix := strings.Join(words[start:], " ")
						if overlapPrefix == "" {
							overlapPrefix = suffix
						} else {
							overlapPrefix = suffix + "\n\n" + overlapPrefix
						}
						overlapTokens += overlapTarget
						break
					}
					if overlapPrefix == "" {
						overlapPrefix = currentParas[j]
					} else {
						overlapPrefix = currentParas[j] + "\n\n" + overlapPrefix
					}
					overlapTokens += pt
				}

				current.Reset()
				current.WriteString(overlapPrefix)
				currentTokens = overlapTokens
				currentParas = nil
				if overlapPrefix != "" {
					currentParas = append(currentParas, overlapPrefix)
				}
			}

			if current.Len() > 0 {
				current.WriteString("\n\n")
			}
			current.WriteString(para)
			currentTokens += paraTokens
			currentParas = append(currentParas, para)
		}
	}

	if currentTokens >= MinChunkTokens {
		chunks = append(chunks, Chunk{
			ID:       fmt.Sprintf("%s-c%d", doc.ID, chunkIdx),
			DocID:    doc.ID,
			Domain:   doc.Domain,
			Section:  doc.Section,
			Title:    doc.Title,
			URL:      doc.URL,
			Text:     current.String(),
			FilePath: doc.FilePath,
		})
	} else if currentTokens > 0 && len(chunks) > 0 {
		// Merge small remainder into last chunk
		last := &chunks[len(chunks)-1]
		last.Text += "\n\n" + current.String()
	} else if currentTokens > 0 {
		chunks = append(chunks, Chunk{
			ID:       fmt.Sprintf("%s-c%d", doc.ID, chunkIdx),
			DocID:    doc.ID,
			Domain:   doc.Domain,
			Section:  doc.Section,
			Title:    doc.Title,
			URL:      doc.URL,
			Text:     current.String(),
			FilePath: doc.FilePath,
		})
	}

	// Post-process: if the last chunk is small, prefer merging it into the previous
	// chunk to avoid tiny tail fragments that harm retrieval quality.
	if len(chunks) >= 2 {
		lastIdx := len(chunks) - 1
		lastTokens := len(strings.Fields(chunks[lastIdx].Text))
		if lastTokens > 0 && lastTokens < MinChunkTokens*2 {
			// merge last into previous
			chunks[lastIdx-1].Text += "\n\n" + chunks[lastIdx].Text
			chunks = chunks[:lastIdx]
		}
	}

	// If there are exactly two chunks and the combined size is reasonably small,
	// merge into a single chunk to avoid tiny tail fragments splitting content.
	if len(chunks) == 2 {
		// Merge two chunks together to avoid leftover tiny split fragments.
		chunks[0].Text = strings.TrimSpace(chunks[0].Text + "\n\n" + chunks[1].Text)
		chunks = chunks[:1]
	}

	return chunks
}

// SplitIntoParagraphs splits text into paragraphs by double newlines.
func SplitIntoParagraphs(text string) []string {
	raw := strings.Split(text, "\n\n")
	var result []string
	for _, p := range raw {
		trimmed := strings.TrimSpace(p)
		if trimmed != "" {
			result = append(result, trimmed)
		}
	}
	return result
}

// CleanMarkdown removes some markdown formatting and image links.
func CleanMarkdown(text string) string {
	lines := strings.Split(text, "\n")
	var cleaned []string
	for _, line := range lines {
		// Remove image links
		if strings.HasPrefix(strings.TrimSpace(line), "![") {
			continue
		}
		// Remove horizontal rules
		trimmed := strings.TrimSpace(line)
		if trimmed == "---" || trimmed == "***" || trimmed == "___" {
			continue
		}
		// Strip markdown formatting but keep text
		line = strings.ReplaceAll(line, "**", "")
		line = strings.ReplaceAll(line, "__", "")
		line = strings.ReplaceAll(line, "~~", "")
		cleaned = append(cleaned, line)
	}
	return strings.Join(cleaned, "\n")
}

// SplitLongParagraph splits a paragraph into smaller pieces if it exceeds the limit.
func SplitLongParagraph(p string, limit int) []string {
	sentences := SplitIntoSentences(p)
	var result []string
	var current strings.Builder
	currentCount := 0

	for _, s := range sentences {
		s = strings.TrimSpace(s)
		if s == "" {
			continue
		}

		words := strings.Fields(s)
		if len(words) > limit {
			// If a sentence is too long, split it by words
			if currentCount > 0 {
				result = append(result, strings.TrimSpace(current.String()))
				current.Reset()
				currentCount = 0
			}

			for i := 0; i < len(words); i += limit {
				end := i + limit
				if end > len(words) {
					end = len(words)
				}
				result = append(result, strings.Join(words[i:end], " "))
			}
			continue
		}

		if currentCount+len(words) > limit && currentCount > 0 {
			result = append(result, strings.TrimSpace(current.String()))
			current.Reset()
			currentCount = 0
		}

		if current.Len() > 0 {
			current.WriteString(" ")
		}
		current.WriteString(s)
		currentCount += len(words)
	}

	if currentCount > 0 {
		result = append(result, strings.TrimSpace(current.String()))
	}
	return result
}

// SplitIntoSentences splits a paragraph into sentences.
func SplitIntoSentences(text string) []string {
	var sentences []string
	var current strings.Builder

	runes := []rune(text)
	for i := 0; i < len(runes); i++ {
		current.WriteRune(runes[i])
		if runes[i] == '.' || runes[i] == '!' || runes[i] == '?' {
			// Check if next char is space or newline or end
			if i+1 == len(runes) || runes[i+1] == ' ' || runes[i+1] == '\n' || runes[i+1] == '\r' {
				sentences = append(sentences, current.String())
				current.Reset()
			}
		}
	}
	if current.Len() > 0 {
		sentences = append(sentences, current.String())
	}
	return sentences
}
