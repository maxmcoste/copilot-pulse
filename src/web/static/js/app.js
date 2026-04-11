// Copilot Pulse Dashboard — Client-side JavaScript
// Translations are loaded from window.T (injected by base.html)

const T = () => window.T || {};

// ── WebSocket Chat ──────────────────────────────────────────

const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const chatSend = document.getElementById('chatSend');

let ws = null;
// Live analysis block that shows logs as they arrive in real-time.
let liveAnalysis = null; // { container, logList, stepCount }

function initChat() {
    if (!chatInput) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);

    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.type === 'log') {
            ensureLiveAnalysis();
            appendLogEntry(data.message);
        } else if (data.type === 'status') {
            ensureLiveAnalysis();
            appendLogEntry(data.message);
        } else if (data.type === 'response') {
            finalizeLiveAnalysis();
            appendBotResponse(data.message);
        } else if (data.type === 'error') {
            finalizeLiveAnalysis();
            appendBotResponse(`${T().error_prefix || 'Error'}: ${data.message}`);
        }
    };

    ws.onclose = function() {
        addMessage(T().chat_conn_lost || 'Connection lost. Reload the page.', 'bot');
    };

    chatSend.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });
}

/**
 * Create the live analysis block immediately when the first log arrives.
 * The block is an open <details> with a streaming list of steps.
 */
function ensureLiveAnalysis() {
    if (liveAnalysis) return;
    removeTyping();

    var container = document.createElement('div');
    container.className = 'message bot-message';
    container.id = 'liveAnalysisContainer';

    var details = document.createElement('details');
    details.className = 'agent-logs';
    details.open = true;

    var summary = document.createElement('summary');
    summary.className = 'live-summary';
    summary.innerHTML = '<span class="analysis-spinner"></span> ' +
        (T().chat_analyzing || 'Analyzing') + '...';
    details.appendChild(summary);

    var logList = document.createElement('ul');
    details.appendChild(logList);
    container.appendChild(details);

    chatMessages.appendChild(container);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    liveAnalysis = { container: container, details: details, summary: summary, logList: logList, stepCount: 0 };
}

/**
 * Append a single log entry to the live analysis block.
 */
function appendLogEntry(text) {
    if (!liveAnalysis) return;
    liveAnalysis.stepCount++;
    var li = document.createElement('li');
    li.textContent = text;
    li.className = 'log-entry-appear';
    liveAnalysis.logList.appendChild(li);

    // Update summary with step count
    var label = T().chat_analyzing || 'Analyzing';
    var stepsWord = liveAnalysis.stepCount === 1 ? 'step' : 'steps';
    liveAnalysis.summary.innerHTML = '<span class="analysis-spinner"></span> ' +
        label + ' (' + liveAnalysis.stepCount + ' ' + stepsWord + ')...';

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Finalize the analysis block: remove spinner, collapse, update label.
 */
function finalizeLiveAnalysis() {
    if (!liveAnalysis) return;
    var la = liveAnalysis;
    var label = T().chat_analyzing || 'Analyzing';
    var stepsWord = la.stepCount === 1 ? 'step' : 'steps';
    la.summary.innerHTML = label + ' (' + la.stepCount + ' ' + stepsWord + ')';
    la.details.open = false;
    liveAnalysis = null;
}

/**
 * Append the final bot response text below the analysis block.
 */
function appendBotResponse(text) {
    // Find the live container or create a new message
    var container = document.getElementById('liveAnalysisContainer');
    if (container) {
        container.removeAttribute('id');
        var content = document.createElement('div');
        content.innerHTML = renderMarkdown(text);
        container.appendChild(content);
    } else {
        addMessage(text, 'bot');
    }
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || !ws) return;

    addMessage(text, 'user');
    ws.send(JSON.stringify({ question: text }));
    chatInput.value = '';
}

function renderMarkdown(text) {
    // Use marked.js if available, otherwise use a built-in converter
    if (typeof marked !== 'undefined') {
        return marked.parse(text);
    }
    // Built-in lightweight markdown to HTML converter
    let html = text
        // Escape HTML entities first
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Code blocks (``` ... ```)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Headers
    html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    // Horizontal rules
    html = html.replace(/^---$/gm, '<hr>');
    // Unordered lists
    html = html.replace(/^[\s]*[-*] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    // Fix multiple ul groups
    html = html.replace(/<\/ul>\s*<ul>/g, '');
    // Numbered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    // Paragraphs: convert double newlines to paragraph breaks
    html = html.replace(/\n\n+/g, '</p><p>');
    // Single newlines to <br> (except inside tags)
    html = html.replace(/\n/g, '<br>');
    // Wrap in paragraph
    html = '<p>' + html + '</p>';
    // Clean up empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, '');
    // Don't wrap block elements in p tags
    html = html.replace(/<p>\s*(<h[1-4]>)/g, '$1');
    html = html.replace(/(<\/h[1-4]>)\s*<\/p>/g, '$1');
    html = html.replace(/<p>\s*(<ul>)/g, '$1');
    html = html.replace(/(<\/ul>)\s*<\/p>/g, '$1');
    html = html.replace(/<p>\s*(<pre>)/g, '$1');
    html = html.replace(/(<\/pre>)\s*<\/p>/g, '$1');
    html = html.replace(/<p>\s*(<hr>)\s*<\/p>/g, '$1');

    return html;
}

function addMessage(text, type, logs) {
    removeTyping();
    const div = document.createElement('div');
    div.className = `message ${type}-message`;

    if (type === 'bot') {
        // If there are log entries, render a collapsible details block first.
        if (logs && logs.length > 0) {
            const details = document.createElement('details');
            details.className = 'agent-logs';
            const summary = document.createElement('summary');
            summary.textContent = (T().chat_analyzing || 'Analyzing') +
                ` (${logs.length} ${logs.length === 1 ? 'step' : 'steps'})`;
            details.appendChild(summary);
            const logList = document.createElement('ul');
            logs.forEach(function(entry) {
                const li = document.createElement('li');
                li.textContent = entry;
                logList.appendChild(li);
            });
            details.appendChild(logList);
            div.appendChild(details);
        }
        const content = document.createElement('div');
        content.innerHTML = renderMarkdown(text);
        div.appendChild(content);
    } else {
        div.textContent = text;
    }
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping(text) {
    removeTyping();
    const div = document.createElement('div');
    div.className = 'message bot-message typing';
    div.textContent = text || T().chat_analyzing || 'Analyzing...';
    div.id = 'typingIndicator';
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTyping() {
    const typing = document.getElementById('typingIndicator');
    if (typing) typing.remove();
}


// ── Setup Page ──────────────────────────────────────────────

function initSetup() {
    const fileInput = document.getElementById('orgFileInput');
    const uploadArea = document.getElementById('uploadArea');
    if (!fileInput || !uploadArea) return;

    // File input change
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            document.getElementById('uploadFileName').textContent = this.files[0].name;
            uploadOrgFile(this.files[0]);
        }
    });

    // Drag & drop
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('drag-over');
    });
    uploadArea.addEventListener('dragleave', function() {
        this.classList.remove('drag-over');
    });
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) {
            document.getElementById('uploadFileName').textContent = file.name;
            uploadOrgFile(file);
        }
    });

    // Employee search autocomplete
    const searchInput = document.getElementById('employeeSearch');
    if (searchInput) {
        let debounceTimer;
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => searchEmployees(this.value), 300);
        });
        searchInput.addEventListener('blur', function() {
            setTimeout(() => {
                document.getElementById('employeeResults').style.display = 'none';
            }, 200);
        });
    }
}

async function uploadOrgFile(file) {
    const progressDiv = document.getElementById('uploadProgress');
    const resultDiv = document.getElementById('uploadResult');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    progressDiv.style.display = 'block';
    resultDiv.style.display = 'none';
    progressFill.style.width = '30%';
    progressText.textContent = T().import_uploading || 'Uploading file...';

    const formData = new FormData();
    formData.append('file', file);

    try {
        progressFill.style.width = '60%';
        progressText.textContent = T().import_importing || 'Importing...';

        const resp = await fetch('/api/import-org', { method: 'POST', body: formData });
        const data = await resp.json();

        progressFill.style.width = '100%';

        if (data.success) {
            progressText.textContent = T().import_done || 'Done!';
            resultDiv.style.display = 'block';
            resultDiv.className = 'upload-result alert alert-success';
            resultDiv.textContent = (T().import_success || 'Imported {n} employees into the database.').replace('{n}', data.imported);
            updateStats(data.stats);
        } else {
            progressText.textContent = T().import_error || 'Error';
            resultDiv.style.display = 'block';
            resultDiv.className = 'upload-result alert alert-error';
            resultDiv.textContent = data.error || T().import_unknown_error || 'Unknown error';
        }
    } catch (e) {
        progressFill.style.width = '100%';
        progressText.textContent = T().import_error || 'Error';
        resultDiv.style.display = 'block';
        resultDiv.className = 'upload-result alert alert-error';
        resultDiv.textContent = `${T().error_prefix || 'Error'}: ${e.message}`;
    }
}

async function runAutoMap() {
    const btn = document.getElementById('btnAutoMap');
    const resultDiv = document.getElementById('autoMapResult');
    btn.disabled = true;
    btn.textContent = T().map_auto_running || 'Mapping in progress...';
    resultDiv.style.display = 'none';

    // Read selected pattern and duplicate strategy
    const patternEl = document.querySelector('input[name="emailPattern"]:checked');
    const dupEl = document.querySelector('input[name="dupStrategy"]:checked');
    const emailPattern = patternEl ? patternEl.value : '{name}.{surname}';
    const dupStrategy = dupEl ? dupEl.value : 'skip';

    try {
        const resp = await fetch('/api/map-users/auto', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email_pattern: emailPattern,
                duplicate_strategy: dupStrategy,
            }),
        });
        const data = await resp.json();

        resultDiv.style.display = 'block';
        if (data.success) {
            if (data.new_matches === 0) {
                resultDiv.className = 'alert alert-info';
                resultDiv.textContent = T().map_auto_no_match || 'No new matches found. Try manual mapping.';
            } else {
                resultDiv.className = 'alert alert-success';
                let html = `<strong>${(T().map_auto_found || '{n} new matches found:').replace('{n}', data.new_matches)}</strong><br>`;
                data.matches.forEach(m => {
                    html += `${m.github_login} → ${m.employee_id} (${m.email || m.matched_name || ''})<br>`;
                });
                resultDiv.innerHTML = html;
            }
            updateStats(data.stats);
        } else {
            resultDiv.className = 'alert alert-error';
            resultDiv.textContent = data.error;
        }
    } catch (e) {
        resultDiv.style.display = 'block';
        resultDiv.className = 'alert alert-error';
        resultDiv.textContent = `${T().error_prefix || 'Error'}: ${e.message}`;
    } finally {
        btn.disabled = false;
        btn.textContent = T().map_auto_btn || 'Run auto-mapping';
    }
}

async function runManualMap() {
    const employeeId = document.getElementById('selectedEmployeeId').value;
    const githubLogin = document.getElementById('githubLoginInput').value.trim();
    const resultDiv = document.getElementById('manualMapResult');

    if (!employeeId || !githubLogin) {
        resultDiv.style.display = 'block';
        resultDiv.className = 'alert alert-error';
        resultDiv.textContent = T().map_manual_missing || 'Select an employee and enter the GitHub login.';
        return;
    }

    try {
        const formData = new FormData();
        formData.append('employee_id', employeeId);
        formData.append('github_login', githubLogin);

        const resp = await fetch('/api/map-users/manual', { method: 'POST', body: formData });
        const data = await resp.json();

        resultDiv.style.display = 'block';
        if (data.success) {
            resultDiv.className = 'alert alert-success';
            resultDiv.textContent = (T().map_manual_ok || 'Mapped: {v}').replace('{v}', data.mapped);
            document.getElementById('employeeSearch').value = '';
            document.getElementById('selectedEmployeeId').value = '';
            document.getElementById('githubLoginInput').value = '';
            updateStats(data.stats);
        } else {
            resultDiv.className = 'alert alert-error';
            resultDiv.textContent = data.error;
        }
    } catch (e) {
        resultDiv.style.display = 'block';
        resultDiv.className = 'alert alert-error';
        resultDiv.textContent = `${T().error_prefix || 'Error'}: ${e.message}`;
    }
}

async function searchEmployees(query) {
    const resultsDiv = document.getElementById('employeeResults');
    if (query.length < 2) {
        resultsDiv.style.display = 'none';
        return;
    }

    try {
        const resp = await fetch(`/api/employees/search?q=${encodeURIComponent(query)}`);
        const data = await resp.json();

        if (data.results.length === 0) {
            resultsDiv.style.display = 'none';
            return;
        }

        resultsDiv.innerHTML = data.results.map(r => `
            <div class="search-result-item" onclick="selectEmployee('${r.employee_id}', '${r.name} ${r.surname}')">
                <div class="result-name">${r.name} ${r.surname}</div>
                <div class="result-detail">${r.employee_id} · ${r.email || 'no email'}${r.github_id ? ' · GH: ' + r.github_id : ''}</div>
            </div>
        `).join('');
        resultsDiv.style.display = 'block';
    } catch (e) {
        resultsDiv.style.display = 'none';
    }
}

function selectEmployee(id, name) {
    document.getElementById('employeeSearch').value = name;
    document.getElementById('selectedEmployeeId').value = id;
    document.getElementById('employeeResults').style.display = 'none';
}

async function loadUnmatched() {
    const btn = document.getElementById('btnShowUnmatched');
    const listDiv = document.getElementById('unmatchedList');
    btn.disabled = true;

    try {
        const resp = await fetch('/api/unmatched-users');
        const data = await resp.json();

        listDiv.style.display = 'block';
        if (data.count === 0) {
            listDiv.className = 'alert alert-success';
            listDiv.textContent = T().map_unmatched_all_ok || 'All GitHub users are matched!';
        } else {
            listDiv.innerHTML = `
                <p style="color:var(--text-secondary);font-size:13px;margin:12px 0 8px;">
                    ${(T().map_unmatched_count || '{n} unmatched users:').replace('{n}', data.count)}
                </p>
                <div class="unmatched-grid">
                    ${data.unmatched.map(u => `<span class="unmatched-tag">${u}</span>`).join('')}
                </div>
            `;
        }
    } catch (e) {
        listDiv.style.display = 'block';
        listDiv.className = 'alert alert-error';
        listDiv.textContent = `${T().error_prefix || 'Error'}: ${e.message}`;
    } finally {
        btn.disabled = false;
    }
}

function updateStats(stats) {
    const el = (id) => document.getElementById(id);
    if (el('statEmployees')) el('statEmployees').textContent = stats.total_employees;
    if (el('statCopilotUsers')) el('statCopilotUsers').textContent = stats.total_copilot_users;
    if (el('statMatched')) el('statMatched').textContent = stats.matched_copilot_users;
    if (el('statMatchRate')) {
        el('statMatchRate').textContent = stats.match_rate + '%';
        el('statMatchRate').className = 'kpi-value ' + (
            stats.match_rate >= 70 ? 'kpi-green' :
            stats.match_rate >= 40 ? 'kpi-yellow' : 'kpi-red'
        );
    }
}

// ── Chart Help Toggle ────────────────────────────────────────

function toggleChartHelp(btn) {
    var card = btn.closest('.chart-card');
    var helpDiv = card.querySelector('.chart-help-text');
    if (helpDiv.style.display === 'none' || !helpDiv.style.display) {
        helpDiv.style.display = 'block';
        btn.classList.add('active');
    } else {
        helpDiv.style.display = 'none';
        btn.classList.remove('active');
    }
}

// ── Dashboard Charts (Plotly) ────────────────────────────────

function initDashboardCharts() {
    const adoptionEl = document.getElementById('adoptionChart');
    const featureEl = document.getElementById('featureChart');
    const topUsersEl = document.getElementById('topUsersChart');
    const sugAccEl = document.getElementById('suggestedAcceptedChart');
    const usageTrendEl = document.getElementById('usageTrendChart');
    const agentWowEl = document.getElementById('agentEditsWowChart');
    if (!adoptionEl && !featureEl && !topUsersEl && !sugAccEl && !usageTrendEl && !agentWowEl) return;

    const darkLayout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { color: '#c9d1d9', size: 12 },
        margin: { t: 10, r: 20, b: 40, l: 50 },
        xaxis: { gridcolor: '#30363d' },
        yaxis: { gridcolor: '#30363d' },
        legend: { orientation: 'h', y: -0.2 },
    };

    if (adoptionEl) {
        fetch('/api/charts/adoption')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) {
                    adoptionEl.textContent = data.error;
                    return;
                }
                var traces = [
                    {
                        x: data.dates,
                        y: data.active_users,
                        name: T().dash_active_users || 'Active Users',
                        type: 'scatter',
                        mode: 'lines+markers',
                        line: { color: '#58a6ff', width: 2 },
                        marker: { size: 4 },
                    },
                    {
                        x: data.dates,
                        y: data.engaged_users,
                        name: T().dash_engaged_users || 'Engaged Users',
                        type: 'scatter',
                        mode: 'lines+markers',
                        line: { color: '#3fb950', width: 2 },
                        marker: { size: 4 },
                    },
                ];
                adoptionEl.textContent = '';
                Plotly.newPlot(adoptionEl, traces, darkLayout, { responsive: true, displayModeBar: false });
            })
            .catch(function(e) { adoptionEl.textContent = 'Error: ' + e.message; });
    }

    if (featureEl) {
        fetch('/api/charts/features')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) {
                    featureEl.textContent = data.error;
                    return;
                }
                var colors = [
                    '#58a6ff', '#6c63ff', '#3fb950', '#d29922', '#f85149',
                    '#a371f7', '#79c0ff', '#f0883e', '#56d364', '#ff7b72',
                    '#ffa657', '#7ee787',
                ];
                var traces = [{
                    labels: data.labels,
                    values: data.values,
                    type: 'pie',
                    hole: 0.45,
                    marker: { colors: colors.slice(0, data.labels.length) },
                    textinfo: 'percent',
                    textfont: { color: '#c9d1d9', size: 11 },
                    hovertemplate: '%{label}<br>%{value:,}<br>%{percent}<extra></extra>',
                    sort: false,
                }];
                featureEl.textContent = '';
                Plotly.newPlot(featureEl, traces,
                    Object.assign({}, darkLayout, {
                        showlegend: true,
                        legend: { font: { size: 11, color: '#c9d1d9' }, orientation: 'v', x: 1.02, y: 0.5 },
                        margin: { t: 10, r: 160, b: 10, l: 10 },
                    }),
                    { responsive: true, displayModeBar: false });
            })
            .catch(function(e) { featureEl.textContent = 'Error: ' + e.message; });
    }

    // ── Top 10 Active Users (horizontal bar) ──
    if (topUsersEl) {
        fetch('/api/charts/top-users')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) { topUsersEl.textContent = data.error; return; }
                if (!data.logins || data.logins.length === 0) {
                    topUsersEl.textContent = 'No user data available';
                    return;
                }
                var traces = [{
                    y: data.logins,
                    x: data.scores,
                    type: 'bar',
                    orientation: 'h',
                    marker: { color: '#6c63ff' },
                    text: data.scores.map(String),
                    textposition: 'outside',
                    textfont: { color: '#c9d1d9', size: 11 },
                }];
                topUsersEl.textContent = '';
                Plotly.newPlot(topUsersEl, traces,
                    Object.assign({}, darkLayout, {
                        margin: { t: 10, r: 60, b: 30, l: 120 },
                        xaxis: { gridcolor: '#30363d', title: '' },
                        yaxis: { gridcolor: '#30363d', automargin: true },
                    }),
                    { responsive: true, displayModeBar: false });
            })
            .catch(function(e) { topUsersEl.textContent = 'Error: ' + e.message; });
    }

    // ── Suggested vs Accepted Code (14 days) ──
    if (sugAccEl) {
        fetch('/api/charts/suggested-accepted')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) { sugAccEl.textContent = data.error; return; }
                if (!data.dates || data.dates.length === 0) {
                    sugAccEl.textContent = 'No data available';
                    return;
                }
                var traces = [
                    {
                        x: data.dates,
                        y: data.suggested,
                        name: T().dash_suggested || 'Suggested',
                        type: 'scatter',
                        mode: 'lines+markers',
                        line: { color: '#58a6ff', width: 2 },
                        marker: { size: 4 },
                        fill: 'tozeroy',
                        fillcolor: 'rgba(88,166,255,0.1)',
                    },
                    {
                        x: data.dates,
                        y: data.accepted,
                        name: T().dash_accepted || 'Accepted',
                        type: 'scatter',
                        mode: 'lines+markers',
                        line: { color: '#3fb950', width: 2 },
                        marker: { size: 4 },
                        fill: 'tozeroy',
                        fillcolor: 'rgba(63,185,80,0.1)',
                    },
                ];
                sugAccEl.textContent = '';
                Plotly.newPlot(sugAccEl, traces, darkLayout, { responsive: true, displayModeBar: false });
            })
            .catch(function(e) { sugAccEl.textContent = 'Error: ' + e.message; });
    }

    // ── 28-Day Usage Trend (composite score) ──
    if (usageTrendEl) {
        fetch('/api/charts/usage-trend')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) { usageTrendEl.textContent = data.error; return; }
                if (!data.dates || data.dates.length === 0) {
                    usageTrendEl.textContent = 'No data available';
                    return;
                }
                var traces = [{
                    x: data.dates,
                    y: data.scores,
                    name: 'Usage Score',
                    type: 'scatter',
                    mode: 'lines+markers',
                    line: { color: '#d29922', width: 2.5 },
                    marker: { size: 5 },
                    fill: 'tozeroy',
                    fillcolor: 'rgba(210,153,34,0.1)',
                }];
                usageTrendEl.textContent = '';
                Plotly.newPlot(usageTrendEl, traces,
                    Object.assign({}, darkLayout, {
                        yaxis: { gridcolor: '#30363d', title: 'Usage Score' },
                    }),
                    { responsive: true, displayModeBar: false });
            })
            .catch(function(e) { usageTrendEl.textContent = 'Error: ' + e.message; });
    }

    // ── Agent Edits / User — Week over Week (bar chart) ──
    if (agentWowEl) {
        fetch('/api/charts/agent-edits-wow')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) { agentWowEl.textContent = data.error; return; }
                if (!data.labels || data.labels.length === 0) {
                    agentWowEl.textContent = 'No data available';
                    return;
                }
                // Reference bands
                // Weekly thresholds = monthly / 4
                var shapes = [
                    { type: 'line', y0: 2.5, y1: 2.5, x0: -0.5, x1: data.labels.length - 0.5,
                      xref: 'x', yref: 'y', line: { color: '#f85149', width: 1, dash: 'dot' } },
                    { type: 'line', y0: 12.5, y1: 12.5, x0: -0.5, x1: data.labels.length - 0.5,
                      xref: 'x', yref: 'y', line: { color: '#d29922', width: 1, dash: 'dot' } },
                    { type: 'line', y0: 25, y1: 25, x0: -0.5, x1: data.labels.length - 0.5,
                      xref: 'x', yref: 'y', line: { color: '#58a6ff', width: 1, dash: 'dot' } },
                ];
                var annotations = [
                    { x: data.labels.length - 0.6, y: 2.5, xref: 'x', yref: 'y', text: 'Cautious',
                      showarrow: false, font: { size: 9, color: '#f85149' }, xanchor: 'right' },
                    { x: data.labels.length - 0.6, y: 12.5, xref: 'x', yref: 'y', text: 'Standard',
                      showarrow: false, font: { size: 9, color: '#d29922' }, xanchor: 'right' },
                    { x: data.labels.length - 0.6, y: 25, xref: 'x', yref: 'y', text: 'Agent-First',
                      showarrow: false, font: { size: 9, color: '#58a6ff' }, xanchor: 'right' },
                ];
                var traces = [{
                    x: data.labels,
                    y: data.values,
                    type: 'bar',
                    marker: { color: data.colors },
                    text: data.values.map(function(v) { return v.toFixed(1); }),
                    textposition: 'outside',
                    textfont: { color: '#c9d1d9', size: 11 },
                    hovertemplate: '%{x}<br>%{y:.1f} edits/user<extra></extra>',
                }];
                agentWowEl.textContent = '';
                Plotly.newPlot(agentWowEl, traces,
                    Object.assign({}, darkLayout, {
                        shapes: shapes,
                        annotations: annotations,
                        xaxis: { type: 'category', gridcolor: '#30363d' },
                        yaxis: { gridcolor: '#30363d', title: 'Edits / User' },
                        margin: { t: 20, r: 20, b: 60, l: 50 },
                    }),
                    { responsive: true, displayModeBar: false });
            })
            .catch(function(e) { agentWowEl.textContent = 'Error: ' + e.message; });
    }
}

// ── ROI Calculator ───────────────────────────────────────────

function initROI() {
    var widget = document.getElementById('roiWidget');
    if (!widget) return;

    var roiData = null;

    function fmt(n) {
        if (Math.abs(n) >= 1000000) return (n / 1000000).toFixed(1) + 'M €';
        if (Math.abs(n) >= 1000) return Math.round(n).toLocaleString('it-IT') + ' €';
        return n.toFixed(0) + ' €';
    }

    function recalc() {
        if (!roiData) return;
        var rate = parseFloat(document.getElementById('roiHourlyRate').value) || 60;
        var license = parseFloat(document.getElementById('roiLicenseCost').value) || 39;
        var minPerEdit = parseFloat(document.getElementById('roiMinPerEdit').value) || 10;
        var reviewPct = parseFloat(document.getElementById('roiReviewFactor').value) || 20;

        var edits = roiData.agent_edits;
        var seats = roiData.total_seats;
        var days = roiData.days || 28;

        // Value = edits × (min/60) × (1 - review%) × hourly_rate
        var valuePerEdit = (minPerEdit / 60) * (1 - reviewPct / 100) * rate;
        var totalValue = edits * valuePerEdit;

        // License cost for the period (days / 30 ≈ months)
        var months = days / 30;
        var licenseCost = seats * license * months;

        var net = totalValue - licenseCost;
        var multiplier = licenseCost > 0 ? totalValue / licenseCost : 0;
        var valuePerSeat = seats > 0 ? totalValue / seats : 0;

        document.getElementById('roiMultiplier').textContent = multiplier.toFixed(1) + 'x';
        document.getElementById('roiMultiplier').className = 'roi-kpi-value ' + (multiplier >= 1 ? 'roi-positive' : 'roi-negative');
        document.getElementById('roiValue').textContent = fmt(totalValue);
        document.getElementById('roiLicenseTotal').textContent = fmt(licenseCost);
        document.getElementById('roiNet').textContent = fmt(net);
        document.getElementById('roiNet').className = 'roi-kpi-value ' + (net >= 0 ? 'roi-positive' : 'roi-negative');
        document.getElementById('roiValuePerSeat').textContent = fmt(valuePerSeat) + '/seat';
        document.getElementById('roiEditsTotal').textContent = edits.toLocaleString('it-IT');
    }

    // Bind inputs
    ['roiHourlyRate', 'roiLicenseCost', 'roiMinPerEdit', 'roiReviewFactor'].forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.addEventListener('input', recalc);
    });

    // Fetch data
    fetch('/api/roi-data')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) return;
            roiData = data;
            recalc();
        });
}

// ── Initialize ──────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
    initChat();
    initSetup();
    initDashboardCharts();
    initROI();
});
