package reporter

import (
	"encoding/json"
	"fmt"
	"html"
	"os"
	"sort"
	"strings"
	"time"

	"support-triage/internal/config"
	"support-triage/internal/output"
	"support-triage/internal/triage"
)

// CompanyStats tracks metrics per company.
type CompanyStats struct {
	Total     int
	Escalated int
	Replied   int
}

// SectionHit tracks which corpus sections are most helpful.
type SectionHit struct {
	Title string
	Hits  int
}

// Anomaly represents a detected pattern of interest.
type Anomaly struct {
	Pattern    string
	Tickets    []int
	Severity   string // low, medium, high
	Suggestion string
}

// DashboardData holds aggregated metrics for the intelligence dashboard.
type DashboardData struct {
	TotalTickets      int
	EscalatedCount    int
	RepliedCount      int
	ByCompany         map[string]*CompanyStats
	RequestTypeDist   map[string]int
	TopCorpusSections []SectionHit
	AnomalyFlags      []Anomaly
	AvgGroundingScore float64
	Metrics           []triage.TicketMetrics
}

// GenerateHTMLReport creates a self-contained, premium HTML dashboard.
func GenerateHTMLReport(path string, data DashboardData, results []output.TriageResult) error {
	file, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create HTML report: %w", err)
	}
	defer file.Close()

	escRate := 0.0
	if data.TotalTickets > 0 {
		escRate = float64(data.EscalatedCount) / float64(data.TotalTickets) * 100
	}

	// Prepare data for Chart.js
	var companyLabels []string
	var companyTotals []int
	var companyEscalated []int
	for c, stats := range data.ByCompany {
		companyLabels = append(companyLabels, c)
		companyTotals = append(companyTotals, stats.Total)
		companyEscalated = append(companyEscalated, stats.Escalated)
	}

	var typeDistLabels []string
	var typeDistData []int
	for t, count := range data.RequestTypeDist {
		typeDistLabels = append(typeDistLabels, t)
		typeDistData = append(typeDistData, count)
	}

	// Prepare Anomaly HTML
	anomalyHTML := ""
	if len(data.AnomalyFlags) == 0 {
		anomalyHTML = `<p class="text-sm text-gray-400 mb-6">No suspicious patterns detected.</p>`
	} else {
		for _, a := range data.AnomalyFlags {
			severityClass := "border-l-yellow-500 bg-yellow-500/5 border-white/5"
			if a.Severity == "high" {
				severityClass = "border-l-red-500 bg-red-500/5 border-white/5"
			}
			anomalyHTML += fmt.Sprintf(`
                <div class="p-4 rounded-xl border-y border-r border-l-4 %s mb-3">
                    <strong class="block mb-1 text-white">%s</strong>
                    <p class="text-sm text-gray-300">%s</p>
                </div>`, severityClass, a.Pattern, a.Suggestion)
		}
	}

	const htmlTemplate = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VeraQX | Support Triage Intelligence</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Outfit', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    },
                    colors: {
                        accent: '#38bdf8',
                        green: '#10b981',
                        red: '#f43f5e',
                        yellow: '#fbbf24',
                        bg: '#030712',
                    }
                }
            }
        }
    </script>
    <style>
        body {
            background-color: #030712;
            background-image: 
                radial-gradient(at 0%% 0%%, rgba(56, 189, 248, 0.05) 0px, transparent 50%%),
                radial-gradient(at 100%% 0%%, rgba(129, 140, 248, 0.05) 0px, transparent 50%%);
        }
        .glass-card {
            background: rgba(17, 24, 39, 0.7);
            backdrop-filter: blur(12px) saturate(180%%);
            -webkit-backdrop-filter: blur(12px) saturate(180%%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .glass-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 24px -8px rgba(0, 0, 0, 0.4);
            border-color: rgba(255, 255, 255, 0.15);
        }
        /* Custom scrollbar */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }
        .anomaly-high { border-left-color: #f43f5e; background: rgba(244, 63, 94, 0.05); }
        .anomaly-medium { border-left-color: #fbbf24; background: rgba(251, 191, 36, 0.05); }
    </style>
</head>
<body class="text-gray-200 font-sans min-h-screen p-8">
    <div class="max-w-[1400px] mx-auto">
        <header class="flex justify-between items-center mb-8 pb-4 border-b border-white/10">
            <div class="text-2xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-indigo-500 flex items-center gap-3">
                <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-500 to-indigo-500 flex items-center justify-center text-white shadow-[0_0_20px_rgba(14,165,233,0.3)]">V</div>
                VeraQX
            </div>
            <div class="text-right text-sm text-gray-400">
                <p>Intelligence Report v%s</p>
                <p>Generated on %s</p>
            </div>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div class="glass-card rounded-2xl p-6 relative overflow-hidden">
                <div class="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4 flex items-center gap-2">Total Processing</div>
                <div class="text-4xl font-bold mb-1">%d</div>
                <div class="text-sm text-gray-400">Tickets Triage Complete</div>
            </div>
            <div class="glass-card rounded-2xl p-6 relative overflow-hidden">
                <div class="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4 flex items-center gap-2">Escalation Rate</div>
                <div class="text-4xl font-bold mb-1 text-red-500">%.1f%%</div>
                <div class="text-sm text-gray-400">%d tickets required humans</div>
            </div>
            <div class="glass-card rounded-2xl p-6 relative overflow-hidden">
                <div class="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4 flex items-center gap-2">Avg Grounding</div>
                <div class="text-4xl font-bold mb-1" style="color:%s">%.2f</div>
                <div class="text-sm text-gray-400">Corpus Confidence Score</div>
            </div>
            <div class="glass-card rounded-2xl p-6 relative overflow-hidden">
                <div class="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4 flex items-center gap-2">Auto-Reply</div>
                <div class="text-4xl font-bold mb-1 text-emerald-500">%d</div>
                <div class="text-sm text-gray-400">Tickets Resolved by Agent</div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <div class="glass-card rounded-2xl p-6 lg:col-span-2">
                <div class="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4">Volume by Company</div>
                <div class="h-64 relative">
                    <canvas id="companyChart"></canvas>
                </div>
            </div>
            <div class="glass-card rounded-2xl p-6">
                <div class="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4">Request Types</div>
                <div class="h-64 relative">
                    <canvas id="typeChart"></canvas>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div class="glass-card rounded-2xl p-6">
                <div class="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4">Grounding Distribution</div>
                <div class="h-64 relative">
                    <canvas id="groundingChart"></canvas>
                </div>
            </div>
            <div class="glass-card rounded-2xl p-6">
                <div class="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4">Processing Time (Scatter)</div>
                <div class="h-64 relative">
                    <canvas id="timeChart"></canvas>
                </div>
            </div>
        </div>

        <div class="mt-12 mb-8">
            <h2 class="text-xl font-semibold mb-4">Anomaly Detection</h2>
            %s
        </div>

        <div class="mt-8">
            <div class="flex justify-between items-center mb-6">
                <h2 class="text-xl font-semibold">Processing Activity</h2>
                <div class="relative w-72">
                    <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
                    <input type="text" class="w-full bg-white/5 border border-white/10 rounded-xl py-2 pl-10 pr-4 text-white focus:outline-none focus:border-sky-400 focus:ring-4 focus:ring-sky-400/20 transition-all" id="ticketSearch" placeholder="Search tickets...">
                </div>
            </div>

            <div class="glass-card rounded-2xl overflow-hidden">
                <table id="ticketTable" class="w-full text-sm text-left">
                    <thead class="text-xs text-gray-400 bg-white/5 uppercase">
                        <tr>
                            <th class="px-6 py-4 font-semibold border-b border-white/10">Ticket</th>
                            <th class="px-6 py-4 font-semibold border-b border-white/10">Domain</th>
                            <th class="px-6 py-4 font-semibold border-b border-white/10">Status</th>
                            <th class="px-6 py-4 font-semibold border-b border-white/10">Grounding</th>
                            <th class="px-6 py-4 font-semibold border-b border-white/10">Area</th>
                            <th class="px-6 py-4 font-semibold border-b border-white/10">Time</th>
                            <th class="px-6 py-4 font-semibold border-b border-white/10 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-white/5">
`

	fmt.Fprintf(file, htmlTemplate, config.Version, time.Now().Format("Jan 02, 2006 15:04 MST"),
		data.TotalTickets,
		escRate, data.EscalatedCount,
		htmlScoreColor(data.AvgGroundingScore), data.AvgGroundingScore,
		data.RepliedCount,
		anomalyHTML)

	for i, r := range results {
		metrics := data.Metrics[i]
		statusClass := "badge-replied"
		if r.Status == "escalated" {
			statusClass = "badge-escalated"
		}
		groundingColor := htmlScoreColor(metrics.GroundingScore)
		if metrics.VerifiedGrounding > 0 && metrics.VerifiedGrounding < metrics.GroundingScore {
			groundingColor = htmlScoreColor(metrics.VerifiedGrounding)
		}

		fmt.Fprintf(file, `
                        <tr class="ticket-row" data-search="%s %s %s">
                            <td>
                                <div style="font-weight: 600;">#%d</div>
                                <div style="font-size: 0.75rem; color: var(--text-dim);" class="truncate">%s</div>
                            </td>
                            <td><span class="company-pill">%s</span></td>
                            <td><span class="badge %s">%s</span></td>
                            <td>
                                <div style="font-size: 0.75rem; margin-bottom: 4px;">%.2f</div>
                                <div class="grounding-bar-bg">
                                    <div class="grounding-bar-fg" style="width: %.0f%%; background: %s;"></div>
                                </div>
                            </td>
                            <td style="font-size: 0.75rem; color: var(--text-dim);">%s</td>
                            <td style="font-family: 'JetBrains Mono'; font-size: 0.75rem;">%v</td>
                            <td>
                                <button class="btn-drilldown" onclick="openEvidence(%d)">Evidence</button>
                            </td>
                        </tr>
`,
			html.EscapeString(strings.ToLower(r.Company)), html.EscapeString(strings.ToLower(r.Subject)), html.EscapeString(strings.ToLower(r.Status)),
			i+1, html.EscapeString(r.Subject),
			html.EscapeString(r.Company),
			statusClass, html.EscapeString(r.Status),
			metrics.GroundingScore, metrics.GroundingScore*100, groundingColor,
			html.EscapeString(r.ProductArea),
			metrics.Duration.Round(time.Millisecond),
			i)
	}

	const scriptTemplate = `
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Evidence Modal -->
    <div id="evidenceModal" class="fixed inset-0 bg-black/80 backdrop-blur-md z-50 hidden items-center justify-center p-4 md:p-8 transition-opacity duration-300 opacity-0 pointer-events-none">
        <div class="bg-[#030712] border border-white/10 rounded-3xl w-full max-w-4xl max-h-[85vh] overflow-y-auto p-8 relative shadow-[0_25px_50px_-12px_rgba(0,0,0,0.5)] transform scale-95 transition-transform duration-300 evidence-modal-content">
            <button class="absolute top-6 right-6 text-gray-400 hover:text-white transition-colors" onclick="closeModal()">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
            <div id="modalBody"></div>
        </div>
    </div>

    <div id="toast" class="fixed bottom-8 right-8 bg-emerald-500 text-white px-6 py-3 rounded-xl font-semibold shadow-lg transform translate-y-20 opacity-0 transition-all duration-300 z-[2000]"></div>

    <style>
        .badge-replied { @apply bg-emerald-500/10 text-emerald-400; }
        .badge-escalated { @apply bg-rose-500/10 text-rose-400; }
        .modal-active { opacity: 1 !important; pointer-events: auto !important; }
        .modal-active .evidence-modal-content { transform: scale(1) !important; }
    </style>

    <script>
        const tickets = %s;
        const metrics = %s;

        function openEvidence(idx) {
            const ticket = tickets[idx];
            const m = metrics[idx];
            const body = document.getElementById('modalBody');
            
            let html = BQT
                <div class="mb-8">
                    <span class="px-3 py-1 rounded-md text-xs bg-sky-400/10 text-sky-400 border border-sky-400/20">${ticket.company}</span>
                    <h2 class="mt-4 text-2xl font-bold">${ticket.subject}</h2>
                    <p class="text-gray-400 text-sm mt-2">${ticket.issue}</p>
                </div>
                
                <div class="bg-sky-400/5 border-l-4 border-sky-400 p-6 my-6 relative rounded-r-xl">
                    <button class="absolute top-4 right-4 bg-white/10 hover:bg-sky-500 hover:border-sky-500 border border-white/10 text-gray-300 hover:text-white px-3 py-1.5 rounded-lg text-xs transition-all" onclick="copyToClipboard(this, BQT${ticket.justification.replace(/BQT/g, '\\BQT').replace(/\$/g, '\\$')}BQT)">Copy</button>
                    <strong class="text-sky-400 text-xs uppercase tracking-widest">Agent Justification</strong>
                    <p class="mt-3 italic text-gray-300">${ticket.justification}</p>
                </div>

                <div class="bg-emerald-500/5 border-l-4 border-emerald-500 p-6 my-6 relative rounded-r-xl">
                    <button class="absolute top-4 right-4 bg-white/10 hover:bg-emerald-500 hover:border-emerald-500 border border-white/10 text-gray-300 hover:text-white px-3 py-1.5 rounded-lg text-xs transition-all" onclick="copyToClipboard(this, BQT${ticket.response.replace(/BQT/g, '\\BQT').replace(/\$/g, '\\$')}BQT)">Copy</button>
                    <strong class="text-emerald-500 text-xs uppercase tracking-widest">Suggested Response</strong>
                    <p class="mt-3 text-gray-300">${ticket.response}</p>
                </div>

                <h3 class="text-lg mt-10 mb-4 text-gray-400 font-semibold border-b border-white/10 pb-2">Grounding Evidence</h3>
                <div class="grid grid-cols-1 gap-4 mt-4">
            BQT;

            if (m.retrieved_chunks && m.retrieved_chunks.length > 0) {
                m.retrieved_chunks.forEach(sc => {
                    html += BQT
                        <div class="bg-white/5 border border-white/10 rounded-xl p-5 hover:border-white/20 transition-colors">
                            <div class="flex justify-between items-center text-xs text-gray-400 mb-3">
                                <span class="font-semibold text-gray-300">${sc.chunk.title}</span>
                                <span class="text-sky-400 bg-sky-400/10 px-2 py-1 rounded">Score: ${sc.score.toFixed(2)}</span>
                            </div>
                            <div class="font-mono text-sm whitespace-pre-wrap text-gray-300">${sc.chunk.text}</div>
                        </div>
                    BQT;
                });
            } else {
                html += '<p class="text-gray-500 italic">No corpus chunks were retrieved for this ticket.</p>';
            }

            html += '</div>';
            body.innerHTML = html;
            
            const modal = document.getElementById('evidenceModal');
            modal.classList.remove('hidden');
            // small delay to allow display:block to apply before animating opacity
            setTimeout(() => {
                modal.classList.add('modal-active');
            }, 10);
        }

        function closeModal() {
            const modal = document.getElementById('evidenceModal');
            modal.classList.remove('modal-active');
            setTimeout(() => {
                modal.classList.add('hidden');
            }, 300);
        }

        function copyToClipboard(btn, text) {
            navigator.clipboard.writeText(text).then(() => {
                const original = btn.innerText;
                btn.innerText = 'Copied!';
                btn.classList.add('!bg-emerald-500', '!border-emerald-500', '!text-white');
                
                showToast('Copied to clipboard');
                
                setTimeout(() => {
                    btn.innerText = original;
                    btn.classList.remove('!bg-emerald-500', '!border-emerald-500', '!text-white');
                }, 2000);
            });
        }

        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.style.transform = 'translateY(0)';
            toast.style.opacity = '1';
            setTimeout(() => {
                toast.style.transform = 'translateY(20px)';
                toast.style.opacity = '0';
            }, 3000);
        }

        // Search logic
        document.getElementById('ticketSearch').addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase();
            document.querySelectorAll('.ticket-row').forEach(row => {
                const searchData = row.getAttribute('data-search');
                row.style.display = searchData.includes(term) ? '' : 'none';
            });
        });

        // Charts
        Chart.defaults.color = '#9ca3af';
        Chart.defaults.font.family = 'Outfit';

        const ctxCompany = document.getElementById('companyChart').getContext('2d');
        new Chart(ctxCompany, {
            type: 'bar',
            data: {
                labels: %s,
                datasets: [
                    {
                        label: 'Total',
                        data: %s,
                        backgroundColor: 'rgba(56, 189, 248, 0.4)',
                        borderColor: '#38bdf8',
                        borderWidth: 1,
                        borderRadius: 4
                    },
                    {
                        label: 'Escalated',
                        data: %s,
                        backgroundColor: 'rgba(244, 63, 94, 0.4)',
                        borderColor: '#f43f5e',
                        borderWidth: 1,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#9ca3af' } } },
                scales: {
                    x: { ticks: { color: '#9ca3af' }, grid: { display: false } },
                    y: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                }
            }
        });

        const ctxType = document.getElementById('typeChart').getContext('2d');
        new Chart(ctxType, {
            type: 'doughnut',
            data: {
                labels: %s,
                datasets: [{
                    data: %s,
                    backgroundColor: [
                        'rgba(56, 189, 248, 0.6)',
                        'rgba(129, 140, 248, 0.6)',
                        'rgba(16, 185, 129, 0.6)',
                        'rgba(244, 63, 94, 0.6)'
                    ],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#9ca3af' } }
                },
                cutout: '70%%'
            }
        });

        // Prepare data for grounding and time charts
        const groundingData = metrics.map(m => m.grounding_score);
        // Create histogram bins
        const bins = Array(10).fill(0);
        groundingData.forEach(s => {
            let idx = Math.floor(s * 10);
            if (idx >= 10) idx = 9;
            bins[idx]++;
        });
        
        const ctxGrounding = document.getElementById('groundingChart').getContext('2d');
        new Chart(ctxGrounding, {
            type: 'bar',
            data: {
                labels: ['0-0.1','0.1-0.2','0.2-0.3','0.3-0.4','0.4-0.5','0.5-0.6','0.6-0.7','0.7-0.8','0.8-0.9','0.9-1.0'],
                datasets: [{
                    label: 'Tickets',
                    data: bins,
                    backgroundColor: 'rgba(16, 185, 129, 0.4)',
                    borderColor: '#10b981',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false } },
                    y: { grid: { color: 'rgba(255,255,255,0.05)' }, beginAtZero: true }
                }
            }
        });

        const timeData = metrics.map((m, i) => ({
            x: m.grounding_score,
            y: m.duration / 1000000000 // Convert nanoseconds to seconds
        }));

        const ctxTime = document.getElementById('timeChart').getContext('2d');
        new Chart(ctxTime, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Processing Time',
                    data: timeData,
                    backgroundColor: 'rgba(129, 140, 248, 0.6)',
                    borderColor: '#818cf8',
                    borderWidth: 1,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { 
                        title: { display: true, text: 'Grounding Score', color: '#9ca3af' },
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        min: 0, max: 1
                    },
                    y: { 
                        title: { display: true, text: 'Duration (s)', color: '#9ca3af' },
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        beginAtZero: true
                    }
                }
            }
        });
    </script>
</body>
</html>`

	script := strings.ReplaceAll(scriptTemplate, "BQT", "`")
	fmt.Fprintf(file, script,
		jsonEscape(results), jsonEscape(data.Metrics),
		jsonEscape(companyLabels), jsonEscape(companyTotals), jsonEscape(companyEscalated),
		jsonEscape(typeDistLabels), jsonEscape(typeDistData))

	return nil
}

func jsonEscape(v interface{}) string {
	b, _ := json.Marshal(v)
	return string(b)
}

// BuildDashboardData aggregates results into dashboard metrics.
func BuildDashboardData(results []output.TriageResult, metrics []triage.TicketMetrics, scores []float64, hits map[string]int, domains map[string]string) DashboardData {
	data := DashboardData{
		TotalTickets:    len(results),
		ByCompany:       make(map[string]*CompanyStats),
		RequestTypeDist: make(map[string]int),
		Metrics:         metrics,
	}

	sumScore := 0.0
	for i, r := range results {
		if r.Status == "escalated" {
			data.EscalatedCount++
		} else {
			data.RepliedCount++
		}

		if _, ok := data.ByCompany[r.Company]; !ok {
			data.ByCompany[r.Company] = &CompanyStats{}
		}
		data.ByCompany[r.Company].Total++
		if r.Status == "escalated" {
			data.ByCompany[r.Company].Escalated++
		} else {
			data.ByCompany[r.Company].Replied++
		}

		data.RequestTypeDist[r.RequestType]++
		if i < len(scores) {
			sumScore += scores[i]
		}
	}

	if len(results) > 0 {
		data.AvgGroundingScore = sumScore / float64(len(results))
	}

	for title, count := range hits {
		data.TopCorpusSections = append(data.TopCorpusSections, SectionHit{Title: title, Hits: count})
	}
	sort.Slice(data.TopCorpusSections, func(i, j int) bool {
		return data.TopCorpusSections[i].Hits > data.TopCorpusSections[j].Hits
	})

	data.AnomalyFlags = detectAnomalies(results)
	return data
}

// RenderDashboard prints the terminal intelligence dashboard.
func RenderDashboard(data DashboardData) {
	w := 60
	bar := strings.Repeat("─", w)

	fmt.Printf("\n%s%s%s\n", config.ColorBold+config.ColorCyan, bar, config.ColorReset)
	fmt.Printf("%s  VeraQX │ Intelligence Dashboard%s\n", config.ColorBold, config.ColorReset)
	fmt.Printf("%s%s%s\n\n", config.ColorBold+config.ColorCyan, bar, config.ColorReset)

	// KPI Row
	fmt.Printf("  %-22s %s%d%s\n", "Total Tickets:", config.ColorBold, data.TotalTickets, config.ColorReset)
	escRate := 0.0
	if data.TotalTickets > 0 {
		escRate = float64(data.EscalatedCount) / float64(data.TotalTickets) * 100
	}
	escColor := config.ColorGreen
	if escRate > 30 {
		escColor = config.ColorRed
	} else if escRate > 15 {
		escColor = config.ColorYellow
	}
	fmt.Printf("  %-22s %s%.1f%%%s (%d escalated)\n", "Escalation Rate:", escColor, escRate, config.ColorReset, data.EscalatedCount)
	fmt.Printf("  %-22s %s%d%s\n", "Auto-Replied:", config.ColorGreen, data.RepliedCount, config.ColorReset)
	fmt.Printf("  %-22s %s%.3f%s\n", "Avg Grounding Score:", ScoreColor(data.AvgGroundingScore), data.AvgGroundingScore, config.ColorReset)

	// Company breakdown
	if len(data.ByCompany) > 0 {
		fmt.Printf("\n%s  By Company:%s\n", config.ColorBold, config.ColorReset)

		// Sort companies for stable output
		var companies []string
		for c := range data.ByCompany {
			companies = append(companies, c)
		}
		sort.Strings(companies)

		for _, company := range companies {
			stats := data.ByCompany[company]
			barStr := RenderBar(stats.Replied, stats.Total, 20)
			fmt.Printf("    %-18s %s  %d/%d replied\n", limitStr(company, 18), barStr, stats.Replied, stats.Total)
		}
	}

	// Request type distribution
	if len(data.RequestTypeDist) > 0 {
		fmt.Printf("\n%s  Request Types:%s\n", config.ColorBold, config.ColorReset)
		var types []string
		for t := range data.RequestTypeDist {
			types = append(types, t)
		}
		sort.Strings(types)
		for _, t := range types {
			count := data.RequestTypeDist[t]
			barStr := RenderBar(count, data.TotalTickets, 20)
			fmt.Printf("    %-22s %s  %d\n", limitStr(t, 22), barStr, count)
		}
	}

	// Top Corpus Sections
	if len(data.TopCorpusSections) > 0 {
		fmt.Printf("\n%s  Top Corpus Sections:%s\n", config.ColorBold, config.ColorReset)
		max := 5
		if len(data.TopCorpusSections) < max {
			max = len(data.TopCorpusSections)
		}
		for i := 0; i < max; i++ {
			s := data.TopCorpusSections[i]
			fmt.Printf("    %d. %-35s %s%d hits%s\n", i+1, limitStr(s.Title, 35), config.ColorCyan, s.Hits, config.ColorReset)
		}
	}

	// Anomaly Flags
	if len(data.AnomalyFlags) > 0 {
		fmt.Printf("\n%s%s  ⚠ Intelligence Alerts:%s\n", config.ColorBold, config.ColorRed, config.ColorReset)
		for _, a := range data.AnomalyFlags {
			color := config.ColorYellow
			if a.Severity == "high" {
				color = config.ColorRed
			}
			fmt.Printf("    %s[%s]%s %s\n", color, strings.ToUpper(a.Severity), config.ColorReset, a.Pattern)
			fmt.Printf("         %s%s%s\n", config.ColorDim, a.Suggestion, config.ColorReset)
		}
	}

	fmt.Printf("\n%s%s%s\n\n", config.ColorBold+config.ColorCyan, bar, config.ColorReset)
}

func detectAnomalies(results []output.TriageResult) []Anomaly {
	var anomalies []Anomaly
	patterns := map[string][]int{
		"unauthorized": {},
		"fraud":        {},
		"not working":  {},
		"refund":       {},
		"access":       {},
		"payment":      {},
	}

	for i, r := range results {
		combined := strings.ToLower(r.Issue + " " + r.Subject)
		for pattern := range patterns {
			if strings.Contains(combined, pattern) {
				patterns[pattern] = append(patterns[pattern], i+1)
			}
		}
	}

	for pattern, tickets := range patterns {
		if len(tickets) >= 2 {
			severity := "medium"
			suggestion := fmt.Sprintf("Multiple tickets match pattern '%s' — review for systemic issue", pattern)

			if pattern == "unauthorized" || pattern == "fraud" {
				severity = "high"
				suggestion = fmt.Sprintf("Possible coordinated fraud pattern — alert security team. Tickets: %v", tickets)
			}

			anomalies = append(anomalies, Anomaly{
				Pattern:    fmt.Sprintf("%d tickets mention \"%s\"", len(tickets), pattern),
				Tickets:    tickets,
				Severity:   severity,
				Suggestion: suggestion,
			})
		}
	}

	sort.Slice(anomalies, func(i, j int) bool {
		if anomalies[i].Severity == "high" && anomalies[j].Severity != "high" {
			return true
		}
		return false
	})

	return anomalies
}

func RenderBar(value, total, width int) string {
	if total == 0 {
		return strings.Repeat("░", width)
	}
	filled := int(float64(value) / float64(total) * float64(width))
	if filled > width {
		filled = width
	}
	return config.ColorGreen + strings.Repeat("█", filled) + config.ColorDim + strings.Repeat("░", width-filled) + config.ColorReset
}

func ScoreColor(score float64) string {
	if score >= 0.7 {
		return config.ColorGreen
	} else if score >= 0.4 {
		return config.ColorYellow
	}
	return config.ColorRed
}

func htmlScoreColor(score float64) string {
	if score >= 0.7 {
		return "var(--green)"
	} else if score >= 0.4 {
		return "var(--yellow)"
	}
	return "var(--red)"
}

func centerPrint(text string, width int) {
	pad := (width - len(text)) / 2
	if pad < 0 {
		pad = 0
	}
	fmt.Printf("%s%s%s%s%s\n", config.ColorBold, config.ColorReset, strings.Repeat(" ", pad), text, config.ColorReset)
}

func padPrint(text string, _ int) {
	fmt.Printf("%s\n", text)
}

func limitStr(s string, max int) string {
	if len(s) > max {
		return s[:max-3] + "..."
	}
	return s
}
