package corpus

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
)

// Document represents a single support article from the corpus.
type Document struct {
	ID       string
	Domain   string // "hackerrank", "claude", "visa"
	Section  string // e.g., "screen", "pro-and-max-plans/pro-plan"
	Title    string
	URL      string
	Body     string
	FilePath string
}

// LoadCorpus recursively loads all .md files from the data directory in parallel.
func LoadCorpus(dataDir string) ([]Document, error) {
	var files []string
	err := filepath.Walk(dataDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() || !strings.HasSuffix(info.Name(), ".md") {
			return nil
		}
		files = append(files, path)
		return nil
	})
	if err != nil {
		return nil, err
	}

	// Sort files for deterministic document IDs across runs.
	sort.Strings(files)

	type indexedFile struct {
		index int
		path  string
	}

	docChan := make(chan Document, len(files))
	errChan := make(chan error, len(files))
	var wg sync.WaitGroup

	// Use a reasonable number of workers (CPU count or fixed)
	workerCount := runtime.NumCPU()
	if workerCount < 4 {
		workerCount = 4 // Minimum baseline
	}
	if len(files) < workerCount {
		workerCount = len(files)
	}

	// Send (sortedIndex, path) pairs so each file gets a stable ID.
	fileChan := make(chan indexedFile, len(files))
	for i, f := range files {
		fileChan <- indexedFile{index: i, path: f}
	}
	close(fileChan)

	for i := 0; i < workerCount; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for item := range fileChan {
				doc, err := ParseMarkdownFile(item.path, dataDir, item.index)
				if err != nil {
					errChan <- fmt.Errorf("parsing %s: %w", item.path, err)
					continue
				}
				docChan <- doc
			}
		}()
	}

	wg.Wait()
	close(docChan)
	close(errChan)

	var docs []Document
	for d := range docChan {
		docs = append(docs, d)
	}

	// Collect parse errors and log them, but do not fail the whole corpus load
	// on a single bad file — return all successfully-loaded documents.
	if len(errChan) > 0 {
		fmt.Fprintf(os.Stderr, "corpus: %d file(s) failed to parse:\n", len(errChan))
		for e := range errChan {
			fmt.Fprintf(os.Stderr, "  - %v\n", e)
		}
	}

	return docs, nil
}

// ParseMarkdownFile parses a single markdown file into a Document.
func ParseMarkdownFile(path, dataDir string, counter int) (Document, error) {
	file, err := os.Open(path)
	if err != nil {
		return Document{}, err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	scanner.Buffer(make([]byte, 1024*1024), 1024*1024) // 1MB buffer

	var (
		inFrontmatter bool
		frontmatter   []string
		bodyLines     []string
		lineNum       int
	)

	for scanner.Scan() {
		line := scanner.Text()
		lineNum++

		if lineNum == 1 && strings.TrimSpace(line) == "---" {
			inFrontmatter = true
			continue
		}
		if inFrontmatter {
			if strings.TrimSpace(line) == "---" {
				inFrontmatter = false
				continue
			}
			frontmatter = append(frontmatter, line)
			continue
		}
		bodyLines = append(bodyLines, line)
	}

	if err := scanner.Err(); err != nil {
		return Document{}, err
	}

	// Determine domain from path
	relPath, _ := filepath.Rel(dataDir, path)
	parts := strings.Split(filepath.ToSlash(relPath), "/")
	domain := ""
	section := ""
	if len(parts) > 0 {
		domain = parts[0]
	}
	if len(parts) > 2 {
		section = strings.Join(parts[1:len(parts)-1], "/")
	} else if len(parts) > 1 {
		section = parts[0]
	}

	// Parse frontmatter
	title := ExtractFrontmatterValue(frontmatter, "title")
	url := ExtractFrontmatterValue(frontmatter, "source_url")

	// Fallback title from first heading
	body := strings.Join(bodyLines, "\n")
	if title == "" {
		title = ExtractFirstHeading(body)
	}

	id := fmt.Sprintf("%s-%04d", domain, counter)

	return Document{
		ID:       id,
		Domain:   domain,
		Section:  section,
		Title:    title,
		URL:      url,
		Body:     body,
		FilePath: relPath,
	}, nil
}

// ExtractFrontmatterValue extracts a value for a given key from frontmatter lines.
func ExtractFrontmatterValue(lines []string, key string) string {
	prefix := key + ":"
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, prefix) {
			val := strings.TrimPrefix(trimmed, prefix)
			val = strings.TrimSpace(val)
			val = strings.Trim(val, "\"'")
			return val
		}
	}
	return ""
}

// ExtractFirstHeading returns the text of the first H1 heading in the markdown body.
func ExtractFirstHeading(body string) string {
	for _, line := range strings.Split(body, "\n") {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "# ") {
			return strings.TrimPrefix(trimmed, "# ")
		}
	}
	return ""
}
