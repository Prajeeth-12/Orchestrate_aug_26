package llm

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// Client is the Ollama HTTP client.
type Client struct {
	BaseURL     string
	Model       string
	BackupModel string
	HTTPClient  *http.Client
}

// OllamaRequest is the request body for the Ollama generate API.
type OllamaRequest struct {
	Model   string         `json:"model"`
	Prompt  string         `json:"prompt"`
	System  string         `json:"system,omitempty"`
	Stream  bool           `json:"stream"`
	Options map[string]any `json:"options,omitempty"`
}

// OllamaResponse is the response from the Ollama generate API.
type OllamaResponse struct {
	Model    string `json:"model"`
	Response string `json:"response"`
	Thinking string `json:"thinking,omitempty"`
	Done     bool   `json:"done"`
}

// OllamaEmbedRequest is the request body for the Ollama embedding API.
type OllamaEmbedRequest struct {
	Model string `json:"model"`
	Input string `json:"input"`
}

// OllamaEmbedResponse is the response from the Ollama embedding API.
type OllamaEmbedResponse struct {
	Model      string      `json:"model"`
	Embeddings [][]float32 `json:"embeddings"`
}

var RetrySleep = time.Sleep

// NewClient creates a new Ollama client with a backup model.
func NewClient(baseURL, model, backupModel string) *Client {
	return &Client{
		BaseURL:     baseURL,
		Model:       model,
		BackupModel: backupModel,
		HTTPClient: &http.Client{
			Timeout: 600 * time.Second, // 10 minutes for very large model responses
		},
	}
}

// Generate calls the Ollama generate API with the given system and user prompts.
func (c *Client) Generate(systemPrompt, userPrompt string) (string, error) {
	var lastErr error
	for attempt := 0; attempt < 3; attempt++ {
		if attempt > 0 {
			RetrySleep(time.Duration(attempt*2) * time.Second)
		}

		rawResp, err := c.GenerateWithModel(c.Model, systemPrompt, userPrompt)
		if err == nil {
			return rawResp, nil
		}
		lastErr = fmt.Errorf("attempt %d: %w", attempt+1, err)
	}

	// If primary failed, try backup
	if c.BackupModel != "" && c.BackupModel != c.Model {
		fmt.Printf("\n[LLM] Primary model %s failed, falling back to backup %s...\n", c.Model, c.BackupModel)
		return c.GenerateWithModel(c.BackupModel, systemPrompt, userPrompt)
	}

	return "", fmt.Errorf("all retries failed: %w", lastErr)
}

// GenerateStream calls the Ollama API and streams the response via a callback.
func (c *Client) GenerateStream(systemPrompt, userPrompt string, callback func(string)) (string, error) {
	req := OllamaRequest{
		Model:  c.Model,
		Prompt: userPrompt,
		System: systemPrompt,
		Stream: true,
		Options: map[string]any{
			"temperature": 0.0,
			"top_p":       0.95,
			// Increase generation and context sizes to reduce truncation of long outputs
			"num_predict": 8192,
			"num_ctx":     32768,
			"seed":        42, // deterministic
		},
	}

	body, err := json.Marshal(req)
	if err != nil {
		return "", fmt.Errorf("marshal request: %w", err)
	}

	url := c.BaseURL + "/api/generate"
	resp, err := c.HTTPClient.Post(url, "application/json", bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("HTTP request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("Ollama returned status %d: %s", resp.StatusCode, string(respBody))
	}

	decoder := json.NewDecoder(resp.Body)
	var fullResponse strings.Builder

	for {
		var ollamaResp OllamaResponse
		err := decoder.Decode(&ollamaResp)
		if err == io.EOF {
			break
		}
		if err != nil {
			return fullResponse.String(), fmt.Errorf("decode stream: %w", err)
		}

		// Ollama streams back fragments in the Response field (or Thinking)
		token := ollamaResp.Response
		if token == "" && ollamaResp.Thinking != "" {
			// For models that output thinking blocks separately
			token = ollamaResp.Thinking
		}

		if token != "" {
			fullResponse.WriteString(token)
			if callback != nil {
				callback(token)
			}
		}

		if ollamaResp.Done {
			break
		}
	}

	return fullResponse.String(), nil
}

// GenerateWithModel is a helper for the core generation logic
func (c *Client) GenerateWithModel(model, systemPrompt, userPrompt string) (string, error) {
	req := OllamaRequest{
		Model:  model,
		Prompt: userPrompt,
		System: systemPrompt,
		Stream: false,
		Options: map[string]any{
			"temperature": 0.0,
			"top_p":       0.95,
			// Increase generation and context sizes to reduce truncation of long outputs
			"num_predict": 8192,
			"num_ctx":     32768,
			"seed":        42,
		},
	}

	body, err := json.Marshal(req)
	if err != nil {
		return "", fmt.Errorf("marshal request: %w", err)
	}

	url := c.BaseURL + "/api/generate"
	resp, err := c.HTTPClient.Post(url, "application/json", bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("HTTP request: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("Ollama returned status %d: %s", resp.StatusCode, string(respBody))
	}

	var ollamaResp OllamaResponse
	if err := json.Unmarshal(respBody, &ollamaResp); err != nil {
		return "", fmt.Errorf("unmarshal response: %w", err)
	}

	// Use Response when available; Thinking is only a fallback.
	// Never concatenate them: Thinking traces pollute downstream JSON parsing.
	rawResp := strings.TrimSpace(ollamaResp.Response)
	if rawResp == "" {
		rawResp = ollamaResp.Thinking
	}
	return rawResp, nil
}

// Ping checks if the Ollama server is reachable.
func (c *Client) Ping() error {
	resp, err := c.HTTPClient.Get(c.BaseURL + "/api/tags")
	if err != nil {
		return fmt.Errorf("cannot reach Ollama at %s: %w", c.BaseURL, err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("Ollama returned status %d", resp.StatusCode)
	}
	return nil
}

// GenerateWithBackup uses the backup (lighter) model for fast utility tasks
// like query rewriting. Falls back to primary if no backup is configured.
func (c *Client) GenerateWithBackup(systemPrompt, userPrompt string) (string, error) {
	model := c.BackupModel
	if model == "" {
		model = c.Model
	}
	return c.GenerateWithModel(model, systemPrompt, userPrompt)
}

// Embed generates a vector embedding for the given text.
func (c *Client) Embed(model, input string) ([]float32, error) {
	// Truncate input to avoid context length errors in Ollama
	if len(input) > 1000 {
		input = input[:1000]
	}

	req := OllamaEmbedRequest{
		Model: model,
		Input: input,
	}

	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	url := c.BaseURL + "/api/embed"
	resp, err := c.HTTPClient.Post(url, "application/json", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("HTTP request: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("Ollama returned status %d: %s", resp.StatusCode, string(respBody))
	}

	var embedResp OllamaEmbedResponse
	if err := json.Unmarshal(respBody, &embedResp); err != nil {
		return nil, fmt.Errorf("unmarshal response: %w", err)
	}

	if len(embedResp.Embeddings) == 0 {
		return nil, fmt.Errorf("no embeddings returned")
	}

	return embedResp.Embeddings[0], nil
}
