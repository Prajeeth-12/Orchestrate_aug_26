import re

with open("internal/reporter/reporter.go", "r") as f:
    content = f.read()

html_template_pattern = r'const htmlTemplate = `<!DOCTYPE html>.*?<tbody>\n`'
script_template_pattern = r'const scriptTemplate = `\n                    </tbody>.*?</html>`'

new_html_template = '''const htmlTemplate = `<!DOCTYPE html>
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

        <div class="mt-12">
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
`'''

new_script_template = r'''const scriptTemplate = `
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
</html>`'''

content = re.sub(html_template_pattern, lambda _: new_html_template, content, flags=re.DOTALL)
content = re.sub(script_template_pattern, lambda _: new_script_template, content, flags=re.DOTALL)

with open("internal/reporter/reporter.go", "w") as f:
    f.write(content)
