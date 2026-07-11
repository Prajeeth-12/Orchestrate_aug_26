package output

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"strings"
)

// Ticket represents an input support ticket.
type Ticket struct {
	Issue               string
	Subject             string
	Company             string
	ExpectedProductArea string
	ExpectedStatus      string
	ExpectedRequestType string
}

// TriageResult represents the output for a single ticket.
type TriageResult struct {
	Issue         string
	Subject       string
	Company       string
	Response      string
	ProductArea   string
	Status        string
	RequestType   string
	Justification string
	Citations     []string
}

// ReadTickets reads the input CSV file.
func ReadTickets(path string) ([]Ticket, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open input CSV: %w", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.LazyQuotes = true
	reader.FieldsPerRecord = -1 // variable fields

	// Read header
	header, err := reader.Read()
	if err != nil {
		return nil, fmt.Errorf("read CSV header: %w", err)
	}

	// Map column indices
	colIdx := make(map[string]int)
	for i, h := range header {
		colIdx[strings.ToLower(strings.TrimSpace(h))] = i
	}

	issueIdx, ok := colIdx["issue"]
	if !ok {
		return nil, fmt.Errorf("missing 'issue' column in CSV")
	}

	var tickets []Ticket
	for {
		record, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("read CSV row: %w", err)
		}

		t := Ticket{}
		if issueIdx < len(record) {
			t.Issue = strings.TrimSpace(record[issueIdx])
		}
		if idx, ok := colIdx["subject"]; ok && idx < len(record) {
			t.Subject = strings.TrimSpace(record[idx])
		}
		if idx, ok := colIdx["company"]; ok && idx < len(record) {
			t.Company = strings.TrimSpace(record[idx])
		}
		if idx, ok := colIdx["product area"]; ok && idx < len(record) {
			t.ExpectedProductArea = strings.TrimSpace(record[idx])
		}
		if idx, ok := colIdx["status"]; ok && idx < len(record) {
			t.ExpectedStatus = strings.TrimSpace(record[idx])
		}
		if idx, ok := colIdx["request type"]; ok && idx < len(record) {
			t.ExpectedRequestType = strings.TrimSpace(record[idx])
		}

		tickets = append(tickets, t)
	}

	return tickets, nil
}

// WriteResults writes the output CSV file.
func WriteResults(path string, results []TriageResult) error {
	file, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create output CSV: %w", err)
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// Write header
	if err := writer.Write([]string{
		"issue", "subject", "company", "response", "product_area",
		"status", "request_type", "justification", "citations",
	}); err != nil {
		return fmt.Errorf("write header: %w", err)
	}

	for _, r := range results {
		citations := strings.Join(r.Citations, "; ")
		if err := writer.Write([]string{
			r.Issue, r.Subject, r.Company, r.Response, r.ProductArea,
			r.Status, r.RequestType, r.Justification, citations,
		}); err != nil {
			return fmt.Errorf("write row: %w", err)
		}
	}

	return nil
}
