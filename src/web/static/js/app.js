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

var _pendingOrgFile = null;
var _uploadSessionId = null;
var _previewColumns = [];

function initSetup() {
    var fileInput = document.getElementById('orgFileInput');
    var uploadArea = document.getElementById('uploadArea');
    if (!fileInput || !uploadArea) return;

    // File input change — stage file, don't upload yet
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            _pendingOrgFile = this.files[0];
            document.getElementById('uploadFileName').textContent = this.files[0].name;
            document.getElementById('importActions').style.display = '';
            document.getElementById('uploadResult').style.display = 'none';
        }
    });

    // Drag & drop — stage file
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
        var file = e.dataTransfer.files[0];
        if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) {
            _pendingOrgFile = file;
            document.getElementById('uploadFileName').textContent = file.name;
            document.getElementById('importActions').style.display = '';
            document.getElementById('uploadResult').style.display = 'none';
        }
    });

    // Toggle warning visibility when checkbox changes
    var refreshAllCb = document.getElementById('refreshAll');
    if (refreshAllCb) {
        refreshAllCb.addEventListener('change', function() {
            var hint = document.getElementById('refreshAllHint');
            if (hint) hint.style.display = this.checked ? '' : 'none';
        });
    }

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

async function openImportPreview() {
    if (!_pendingOrgFile) return;

    var btn = document.getElementById('btnAnalyze');
    if (btn) btn.disabled = true;

    var progressDiv = document.getElementById('uploadProgress');
    var progressFill = document.getElementById('progressFill');
    var progressText = document.getElementById('progressText');
    progressDiv.style.display = 'block';
    progressFill.style.width = '40%';
    progressText.textContent = T().import_analyzing || 'Analyzing structure...';

    try {
        var formData = new FormData();
        formData.append('file', _pendingOrgFile);
        var resp = await fetch('/api/preview-org', { method: 'POST', body: formData });
        var data = await resp.json();

        if (data.error) {
            progressText.textContent = T().import_error || 'Error';
            progressFill.style.width = '100%';
            var resultDiv = document.getElementById('uploadResult');
            resultDiv.style.display = 'block';
            resultDiv.className = 'upload-result alert alert-error';
            resultDiv.textContent = data.error;
            return;
        }

        progressDiv.style.display = 'none';
        _uploadSessionId = data.session_id;
        _previewColumns = data.columns;
        _renderPreviewOverlay(data);
        document.getElementById('importPreviewOverlay').classList.remove('hidden');
    } catch (e) {
        progressFill.style.width = '100%';
        progressText.textContent = T().import_error || 'Error';
        var resultDiv = document.getElementById('uploadResult');
        resultDiv.style.display = 'block';
        resultDiv.className = 'upload-result alert alert-error';
        resultDiv.textContent = e.message;
    } finally {
        if (btn) btn.disabled = false;
    }
}

function closeImportPreview() {
    document.getElementById('importPreviewOverlay').classList.add('hidden');
}

function _renderPreviewOverlay(data) {
    var t = T();
    // Title
    document.getElementById('previewTitle').textContent =
        (t.import_preview_title || 'Column preview') + ': ' + (_pendingOrgFile ? _pendingOrgFile.name : '');

    // Missing required fields alert
    var alertEl = document.getElementById('previewMissingAlert');
    if (data.missing_required && data.missing_required.length > 0) {
        alertEl.classList.remove('hidden');
        alertEl.textContent = (t.import_missing_required || 'Required fields missing: ') + data.missing_required.join(', ');
        document.getElementById('btnProceedImport').disabled = true;
    } else {
        alertEl.classList.add('hidden');
        document.getElementById('btnProceedImport').disabled = false;
    }

    // Column list
    var listEl = document.getElementById('previewColList');
    listEl.innerHTML = '';
    data.columns.forEach(function(col, i) {
        var row = document.createElement('div');
        row.className = 'import-col-row';

        var cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.id = 'prevcol_' + i;
        cb.checked = col.status !== 'unmapped';
        cb.disabled = col.status === 'required' || col.status === 'unmapped';
        cb.dataset.colIndex = i;
        row.appendChild(cb);

        var label = document.createElement('label');
        label.htmlFor = cb.id;
        label.className = 'import-col-name';
        label.textContent = col.header;
        row.appendChild(label);

        if (col.field) {
            var fieldBadge = document.createElement('span');
            fieldBadge.className = 'import-col-fieldname';
            fieldBadge.textContent = col.field;
            row.appendChild(fieldBadge);
        }

        var badge = document.createElement('span');
        badge.className = 'import-col-badge badge-' + col.status;
        if (col.status === 'required') badge.textContent = t.import_col_required || 'Required';
        else if (col.status === 'mapped') badge.textContent = t.import_col_mapped || 'Mapped';
        else badge.textContent = t.import_col_unmapped || 'Not recognised';
        row.appendChild(badge);

        listEl.appendChild(row);
    });

    // Sample table
    var sampleCount = document.getElementById('previewSampleCount');
    sampleCount.textContent = '(' + data.sample_rows.length + ' ' + (t.import_sample_rows || 'rows') + ')';

    var tbl = document.getElementById('previewSampleTable');
    tbl.innerHTML = '';

    var thead = document.createElement('thead');
    var hrow = document.createElement('tr');
    data.columns.forEach(function(col) {
        var th = document.createElement('th');
        th.textContent = col.header;
        if (col.status === 'unmapped') th.className = 'col-unmapped';
        hrow.appendChild(th);
    });
    thead.appendChild(hrow);
    tbl.appendChild(thead);

    var tbody = document.createElement('tbody');
    data.sample_rows.forEach(function(row) {
        var tr = document.createElement('tr');
        row.forEach(function(val, i) {
            var td = document.createElement('td');
            td.textContent = val;
            if (data.columns[i] && data.columns[i].status === 'unmapped') td.className = 'col-unmapped';
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
}

async function confirmImport() {
    if (!_uploadSessionId) return;

    var refreshAll = document.getElementById('refreshAll');
    var isRefreshAll = refreshAll && refreshAll.checked;

    if (isRefreshAll) {
        var warningMsg = T().import_refresh_warning ||
            'This will delete the entire existing organization structure. Continue?';
        if (!confirm(warningMsg)) return;
    }

    var selected = _previewColumns
        .filter(function(col, i) {
            if (col.status === 'unmapped') return false;
            var cb = document.getElementById('prevcol_' + i);
            return cb ? cb.checked : false;
        })
        .map(function(col) { return col.header; });

    closeImportPreview();

    var progressDiv = document.getElementById('uploadProgress');
    var resultDiv = document.getElementById('uploadResult');
    var progressFill = document.getElementById('progressFill');
    var progressText = document.getElementById('progressText');
    progressDiv.style.display = 'block';
    resultDiv.style.display = 'none';
    progressFill.style.width = '30%';
    progressText.textContent = T().import_importing || 'Importing...';

    try {
        progressFill.style.width = '70%';
        var resp = await fetch('/api/import-org', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: _uploadSessionId,
                selected_columns: selected,
                refresh_all: isRefreshAll,
            }),
        });
        var data = await resp.json();
        progressFill.style.width = '100%';

        if (data.success) {
            progressText.textContent = T().import_done || 'Done!';
            resultDiv.style.display = 'block';
            resultDiv.className = 'upload-result alert alert-success';
            var msg = (T().import_success || 'Imported {n} employees.').replace('{n}', data.imported);
            if (data.preserved_mappings > 0) {
                msg += ' ' + (T().import_preserved || '{n} GitHub mappings preserved.').replace('{n}', data.preserved_mappings);
            }
            resultDiv.textContent = msg;
            updateStats(data.stats);
            _pendingOrgFile = null;
            _uploadSessionId = null;
            document.getElementById('importActions').style.display = 'none';
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
        resultDiv.textContent = e.message;
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
                    <button class="btn" style="margin-left:12px;padding:4px 12px;font-size:12px;" onclick="downloadUnmatched()">
                        ${T().map_unmatched_download || 'Download list'}
                    </button>
                </p>
                <div class="unmatched-grid">
                    ${data.unmatched.map(u => `<span class="unmatched-tag">${u}</span>`).join('')}
                </div>
            `;
            window._unmatchedUsers = data.unmatched;
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
    var card = btn.closest('.chart-card, .productivity-chart-card');
    var helpDiv = card.querySelector('.chart-help-text');
    if (helpDiv.style.display === 'none' || !helpDiv.style.display) {
        helpDiv.style.display = 'block';
        btn.classList.add('active');
    } else {
        helpDiv.style.display = 'none';
        btn.classList.remove('active');
    }
}

// ── Productivity Chart Helpers ───────────────────────────────

function _buildThresholdShapes(thresholds, seriesLength) {
    var lineColors = ['#f85149', '#d29922', '#58a6ff'];
    return thresholds.map(function(t, i) {
        return {
            type: 'line', y0: t, y1: t,
            x0: -0.5, x1: seriesLength - 0.5,
            xref: 'x', yref: 'y',
            line: { color: lineColors[i], width: 1, dash: 'dot' },
        };
    });
}

function _renderProductivityLegend(containerId, thresholds) {
    var el = document.getElementById(containerId);
    if (!el) return;
    var t = T();
    var labels = [
        t.product_scale_cautious    || 'Cautious / Legacy',
        t.product_scale_standard    || 'Standard Adopters',
        t.product_scale_advanced    || 'Advanced',
        t.product_scale_agent_first || 'Agent-First / Power Users',
    ];
    var dotColors = ['#f85149', '#d29922', '#3fb950', '#58a6ff'];
    var fmt = function(v) { return v % 1 === 0 ? String(v) : v.toFixed(1); };
    var th = thresholds;
    var bands = [
        '< ' + fmt(th[0]),
        fmt(th[0]) + '\u2013' + fmt(th[1]),
        fmt(th[1]) + '\u2013' + fmt(th[2]),
        '> ' + fmt(th[2]),
    ];
    el.innerHTML = labels.map(function(lbl, i) {
        return '<div class="productivity-scale-item">'
            + '<span class="agent-dot" style="background:' + dotColors[i] + '"></span>'
            + '<span>' + bands[i] + ' \u2014 ' + lbl + '</span>'
            + '</div>';
    }).join('');
}

// ── Dashboard Charts (Plotly) ────────────────────────────────

function initDashboardCharts() {
    const adoptionEl = document.getElementById('adoptionChart');
    const featureEl = document.getElementById('featureChart');
    const topUsersEl = document.getElementById('topUsersChart');
    const sugAccEl = document.getElementById('suggestedAcceptedChart');
    const usageTrendEl = document.getElementById('usageTrendChart');
    const productivityTrendEl = document.getElementById('productivityTrendChart');
    const productivityTrendSeatsEl = document.getElementById('productivityTrendSeatsChart');
    if (!adoptionEl && !featureEl && !topUsersEl && !sugAccEl && !usageTrendEl && !productivityTrendEl && !productivityTrendSeatsEl) return;

    const darkLayout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { color: '#c9d1d9', size: 12 },
        margin: { t: 10, r: 20, b: 40, l: 50 },
        xaxis: { gridcolor: '#30363d' },
        yaxis: { gridcolor: '#30363d' },
        legend: { orientation: 'h', y: -0.2 },
    };

    var qs = (typeof filterQueryString === 'function') ? filterQueryString() : '';

    if (adoptionEl) {
        fetch('/api/charts/adoption' + qs)
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
        fetch('/api/charts/features' + qs)
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
                    hovertemplate: '%{label}<br>%{value:,} users<br>%{percent}<extra></extra>',
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
        fetch('/api/charts/top-users' + qs)
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
        fetch('/api/charts/suggested-accepted' + qs)
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
        fetch('/api/charts/usage-trend' + qs)
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

    // ── Weekly Productivity Trend (Agent Edits / User) ──
    if (productivityTrendEl) {
        fetch('/api/charts/productivity-trend' + qs)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) { productivityTrendEl.textContent = data.error; return; }
                if (!data.labels || data.labels.length === 0) {
                    productivityTrendEl.textContent = 'No data available';
                    return;
                }
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
                var thresholds = data.thresholds || [0.36, 1.79, 3.57];
                var shapes = _buildThresholdShapes(thresholds, data.labels.length);
                var annotations = [];
                if (data.average != null) {
                    shapes.push({
                        type: 'line', y0: data.average, y1: data.average,
                        x0: -0.5, x1: data.labels.length - 0.5,
                        xref: 'x', yref: 'y',
                        line: { color: '#bc8cff', width: 1.5, dash: 'dashdot' },
                    });
                    annotations.push({
                        x: data.labels.length - 0.5, y: data.average,
                        xref: 'x', yref: 'y',
                        text: (T().product_weekly_average || '13w avg') + ': ' + data.average.toFixed(1),
                        showarrow: false,
                        xanchor: 'right',
                        font: { color: '#bc8cff', size: 11 },
                        bgcolor: 'rgba(13,17,23,0.7)',
                        borderpad: 3,
                    });
                }
                productivityTrendEl.textContent = '';
                Plotly.newPlot(productivityTrendEl, traces,
                    Object.assign({}, darkLayout, {
                        shapes: shapes,
                        annotations: annotations,
                        xaxis: { type: 'category', gridcolor: '#30363d' },
                        yaxis: { gridcolor: '#30363d', title: 'Edits / User' },
                        margin: { t: 20, r: 20, b: 60, l: 50 },
                    }),
                    { responsive: true, displayModeBar: false });
                _renderProductivityLegend('productivityTrendLegend', thresholds);
            })
            .catch(function(e) { productivityTrendEl.textContent = 'Error: ' + e.message; });
    }

    // ── Weekly Productivity Trend (Agent Edits / Total Seats) ──
    if (productivityTrendSeatsEl) {
        fetch('/api/charts/productivity-trend-seats' + qs)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) { productivityTrendSeatsEl.textContent = data.error; return; }
                if (!data.labels || data.labels.length === 0) {
                    productivityTrendSeatsEl.textContent = 'No data available';
                    return;
                }
                var traces = [{
                    x: data.labels,
                    y: data.values,
                    type: 'bar',
                    marker: { color: data.colors },
                    text: data.values.map(function(v) { return v.toFixed(1); }),
                    textposition: 'outside',
                    textfont: { color: '#c9d1d9', size: 11 },
                    hovertemplate: data.total_seats
                        ? '%{x}<br>%{y:.1f} edits/seat (' + data.total_seats + ' seats)<extra></extra>'
                        : '%{x}<br>%{y:.1f} edits/seat<extra></extra>',
                }];
                var thresholds = data.thresholds || [0.36, 1.79, 3.57];
                var shapes = _buildThresholdShapes(thresholds, data.labels.length);
                var annotations = [];
                if (data.average != null) {
                    shapes.push({
                        type: 'line', y0: data.average, y1: data.average,
                        x0: -0.5, x1: data.labels.length - 0.5,
                        xref: 'x', yref: 'y',
                        line: { color: '#bc8cff', width: 1.5, dash: 'dashdot' },
                    });
                    annotations.push({
                        x: data.labels.length - 0.5, y: data.average,
                        xref: 'x', yref: 'y',
                        text: (T().product_weekly_average || '13w avg') + ': ' + data.average.toFixed(1),
                        showarrow: false,
                        xanchor: 'right',
                        font: { color: '#bc8cff', size: 11 },
                        bgcolor: 'rgba(13,17,23,0.7)',
                        borderpad: 3,
                    });
                }
                productivityTrendSeatsEl.textContent = '';
                Plotly.newPlot(productivityTrendSeatsEl, traces,
                    Object.assign({}, darkLayout, {
                        shapes: shapes,
                        annotations: annotations,
                        xaxis: { type: 'category', gridcolor: '#30363d' },
                        yaxis: { gridcolor: '#30363d', title: 'Edits / Seat' },
                        margin: { t: 20, r: 20, b: 60, l: 50 },
                    }),
                    { responsive: true, displayModeBar: false });
                _renderProductivityLegend('productivityTrendSeatsLegend', thresholds);
            })
            .catch(function(e) { productivityTrendSeatsEl.textContent = 'Error: ' + e.message; });
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
        var rate = parseFloat(document.getElementById('roiHourlyRate').value) || 33;
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
    var qs = (typeof filterQueryString === 'function') ? filterQueryString() : '';
    fetch('/api/roi-data' + qs)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) return;
            roiData = data;
            recalc();
        });
}

// ── Org Filters ─────────────────────────────────────────────

var _orgFilterData = null; // cached from /api/org-filters
var _activeFilter  = { level: null, value: null };  // current dropdown selection
var _appliedFilter = { level: null, value: null };  // last filter sent to the dashboard

function initOrgFilters() {
    var bar = document.getElementById('orgFilterBar');
    if (!bar) return;

    var sel4 = document.getElementById('filterLevel4');
    var sel5 = document.getElementById('filterLevel5');
    var sel6 = document.getElementById('filterLevel6');
    var sel7 = document.getElementById('filterLevel7');
    var sel8 = document.getElementById('filterLevel8');
    var resetBtn = document.getElementById('filterReset');
    var applyBtn = document.getElementById('filterApply');

    function resetFrom(level) {
        var chain = [
            { sel: sel5, placeholder: '— Level 5 —' },
            { sel: sel6, placeholder: '— Level 6 —' },
            { sel: sel7, placeholder: '— Level 7 —' },
            { sel: sel8, placeholder: '— Level 8 —' }
        ];
        var startIdx = { '5': 0, '6': 1, '7': 2, '8': 3 }[level];
        if (startIdx === undefined) return;
        for (var i = startIdx; i < chain.length; i++) {
            chain[i].sel.innerHTML = '<option value="">' + chain[i].placeholder + '</option>';
            chain[i].sel.disabled = true;
        }
    }

    function populateChildren(parentLevel, parentValue, childSel) {
        var kids = ((_orgFilterData.children[parentLevel] || {})[parentValue]) || [];
        if (kids.length > 0) {
            childSel.disabled = false;
            kids.forEach(function(v) {
                var opt = document.createElement('option');
                opt.value = v; opt.textContent = v;
                childSel.appendChild(opt);
            });
        }
    }

    // Highlight the Apply button when the dropdown selection differs from what's applied.
    function updateApplyBtn() {
        if (!applyBtn) return;
        var pending = _activeFilter.level + ':' + _activeFilter.value;
        var applied = _appliedFilter.level + ':' + _appliedFilter.value;
        if (pending !== applied) {
            applyBtn.classList.add('filter-apply-btn--pending');
        } else {
            applyBtn.classList.remove('filter-apply-btn--pending');
        }
    }

    fetch('/api/org-filters')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.enabled) { bar.style.display = 'none'; return; }
            _orgFilterData = data;
            data.levels['4'].forEach(function(v) {
                var opt = document.createElement('option');
                opt.value = v; opt.textContent = v;
                sel4.appendChild(opt);
            });
        });

    sel4.addEventListener('change', function() {
        resetFrom('5');
        if (!this.value) {
            _activeFilter = { level: null, value: null };
            resetBtn.style.display = 'none';
        } else {
            _activeFilter = { level: '4', value: this.value };
            resetBtn.style.display = '';
            populateChildren('4', this.value, sel5);
        }
        updateApplyBtn();
    });

    sel5.addEventListener('change', function() {
        resetFrom('6');
        if (!this.value) {
            _activeFilter = { level: '4', value: sel4.value };
        } else {
            _activeFilter = { level: '5', value: this.value };
            populateChildren('5', this.value, sel6);
        }
        updateApplyBtn();
    });

    sel6.addEventListener('change', function() {
        resetFrom('7');
        if (!this.value) {
            _activeFilter = { level: '5', value: sel5.value };
        } else {
            _activeFilter = { level: '6', value: this.value };
            populateChildren('6', this.value, sel7);
        }
        updateApplyBtn();
    });

    sel7.addEventListener('change', function() {
        resetFrom('8');
        if (!this.value) {
            _activeFilter = { level: '6', value: sel6.value };
        } else {
            _activeFilter = { level: '7', value: this.value };
            populateChildren('7', this.value, sel8);
        }
        updateApplyBtn();
    });

    sel8.addEventListener('change', function() {
        _activeFilter = this.value
            ? { level: '8', value: this.value }
            : { level: '7', value: sel7.value };
        updateApplyBtn();
    });

    if (applyBtn) {
        applyBtn.addEventListener('click', function() {
            _appliedFilter = { level: _activeFilter.level, value: _activeFilter.value };
            updateApplyBtn();
            refreshDashboard();
        });
    }

    resetBtn.addEventListener('click', function() {
        sel4.value = '';
        resetFrom('5');
        _activeFilter  = { level: null, value: null };
        _appliedFilter = { level: null, value: null };
        resetBtn.style.display = 'none';
        updateApplyBtn();
        refreshDashboard();
    });
}

function filterQueryString() {
    if (!_activeFilter.level || !_activeFilter.value) return '';
    return '?filter_level=' + encodeURIComponent(_activeFilter.level) +
           '&filter_value=' + encodeURIComponent(_activeFilter.value);
}

function refreshDashboard() {
    var qs = filterQueryString();

    // Refresh KPIs via HTMX
    var kpiEl = document.getElementById('kpiCards');
    if (kpiEl) {
        kpiEl.innerHTML = '<div class="kpi-card"><div class="kpi-value">…</div><div class="kpi-label">Loading</div></div>';
        fetch('/api/metrics' + qs).then(function(r) { return r.text(); }).then(function(html) {
            kpiEl.innerHTML = html;
        });
    }

    // Refresh HTMX widgets
    var adoptionEl = document.getElementById('adoptionWidget');
    if (adoptionEl) {
        fetch('/api/adoption-kpis' + qs).then(function(r) { return r.text(); }).then(function(html) {
            adoptionEl.innerHTML = html;
        });
    }
    var productivityEl = document.getElementById('productivityCards');
    if (productivityEl) {
        productivityEl.innerHTML = '<div class="productivity-card"><div class="productivity-value">…</div><div class="productivity-label">Loading</div></div>';
        fetch('/api/productivity-insights' + qs).then(function(r) { return r.text(); }).then(function(html) {
            productivityEl.innerHTML = html;
        });
    }
    var insightsEl = document.getElementById('quickInsights');
    if (insightsEl) {
        fetch('/api/insights' + qs).then(function(r) { return r.text(); }).then(function(html) {
            insightsEl.innerHTML = html;
        });
    }

    // Refresh all charts
    initDashboardCharts();
    // Refresh ROI
    initROI();
    // Refresh Virtual FTE
    loadVirtualFTE();
}

// ── Virtual FTE Analysis ─────────────────────────────────────

function loadVirtualFTE() {
    var resultsEl = document.getElementById('vfteResults');
    if (!resultsEl) return;

    var linesPerDay        = parseInt(document.getElementById('vfteLinesPerDay')?.value)        || 50;
    var workingDays        = parseInt(document.getElementById('vfteWorkingDays')?.value)        || 20;
    var reviewPct          = parseFloat(document.getElementById('vfteReviewOverhead')?.value)   || 20;
    var hourlyRate         = parseFloat(document.getElementById('vfteHourlyRate')?.value)        || 33;
    var dailyHours         = parseInt(document.getElementById('vfteDailyHours')?.value)         || 8;
    var linesPerAgentEdit  = parseInt(document.getElementById('vfteLinesPerAgentEdit')?.value)  || 17;

    var qs = (typeof filterQueryString === 'function') ? filterQueryString() : '';
    var sep = qs ? '&' : '?';
    var params = qs +
        sep + 'lines_per_day=' + linesPerDay +
        '&working_days=' + workingDays +
        '&review_overhead=' + (reviewPct / 100) +
        '&hourly_rate=' + hourlyRate +
        '&daily_hours=' + dailyHours +
        '&lines_per_agent_edit=' + linesPerAgentEdit;

    resultsEl.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;">' + (T().dash_loading || 'Loading...') + '</p>';

    fetch('/api/virtual-fte' + params)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) {
                resultsEl.innerHTML = '<p style="color:#f85149">' + data.error + '</p>';
                return;
            }
            if (!data.periods || data.periods.length === 0) {
                resultsEl.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;">' +
                    (T().vfte_no_data || 'No line data available yet.') + '</p>';
                return;
            }

            var t = T();
            var fmt = function(n) {
                if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
                if (n >= 1000) return (n/1000).toFixed(1) + 'K';
                return n.toLocaleString();
            };
            var fmtEur = function(n) { return '€' + Math.round(n).toLocaleString(); };

            // Table — shows full breakdown: IDE lines, Agent lines, Total, FTE, Value
            var rows = data.periods.map(function(p) {
                return '<tr>' +
                    '<td>' + p.period + '</td>' +
                    '<td>' + fmt(p.volume_ide) + '</td>' +
                    '<td>' + fmt(p.volume_agent) + '</td>' +
                    '<td><strong>' + fmt(p.total_lines) + '</strong></td>' +
                    '<td>' + fmt(p.human_capacity) + '</td>' +
                    '<td class="vfte-fte-cell">' + p.fte.toFixed(2) + '</td>' +
                    '<td>' + fmtEur(p.monthly_value) + '</td>' +
                    '</tr>';
            }).join('');

            var table = '<div class="vfte-table-wrap"><table class="vfte-table">' +
                '<thead><tr>' +
                '<th>' + (t.vfte_col_period     || 'Period')              + '</th>' +
                '<th>' + (t.vfte_col_vol_ide    || 'IDE Lines')           + '</th>' +
                '<th>' + (t.vfte_col_vol_agent  || 'Agent Lines')         + '</th>' +
                '<th>' + (t.vfte_col_total_lines|| 'Total Lines (net)')   + '</th>' +
                '<th>' + (t.vfte_col_capacity   || 'Human Capacity')      + '</th>' +
                '<th>' + (t.vfte_col_fte        || 'Virtual FTE')         + '</th>' +
                '<th>' + (t.vfte_col_value      || 'Monthly Value')       + '</th>' +
                '</tr></thead><tbody>' + rows + '</tbody></table></div>';

            // KPI summary
            var latestPeriod = data.periods[data.periods.length - 1];
            var capacityPct = data.total_seats > 0
                ? ' (+' + (data.avg_fte / data.total_seats * 100).toFixed(0) + '% capacity)'
                : '';
            var kpis = '<div class="vfte-kpi-row">' +
                '<div class="vfte-kpi">' +
                '  <div class="vfte-kpi-value">' + data.avg_fte.toFixed(2) + '</div>' +
                '  <div class="vfte-kpi-label">' + (t.vfte_avg_fte || 'Avg. Virtual FTE (13w)') + '</div>' +
                '</div>' +
                '<div class="vfte-kpi">' +
                '  <div class="vfte-kpi-value">' + fmtEur(latestPeriod.monthly_value) + '</div>' +
                '  <div class="vfte-kpi-label">' + (t.vfte_monthly_roi || 'Monthly ROI (latest period)') + '</div>' +
                '</div>' +
                '<div class="vfte-kpi">' +
                '  <div class="vfte-kpi-value">' + latestPeriod.fte.toFixed(2) + '</div>' +
                '  <div class="vfte-kpi-label">' + (t.vfte_col_fte || 'Virtual FTE') + ' — ' + latestPeriod.period + '</div>' +
                '</div>' +
                '</div>';

            // Insight
            var insight = '<div class="vfte-insight">' +
                '<span class="vfte-insight-icon">💡</span>' +
                '<span>' +
                (t.vfte_insight_prefix || 'Thanks to Copilot adoption, the organisation operated as if it had added') +
                ' <strong>' + data.avg_fte.toFixed(1) + '</strong> ' +
                (t.vfte_insight_suffix || 'developers to the team, increasing productive capacity without changes to actual headcount.') +
                (capacityPct ? ' <em>' + capacityPct + '</em>' : '') +
                '</span></div>';

            resultsEl.innerHTML = kpis + table + insight;
        })
        .catch(function(e) {
            resultsEl.innerHTML = '<p style="color:#f85149">Error: ' + e.message + '</p>';
        });
}

// ── Inactive Users CSV download ──────────────────────────────

function downloadInactiveUsers() {
    var params = new URLSearchParams();
    if (_appliedFilter && _appliedFilter.level) params.set('level', _appliedFilter.level);
    if (_appliedFilter && _appliedFilter.value) params.set('value', _appliedFilter.value);
    var btn = document.getElementById('inactiveUsersBtn');
    if (btn) { btn.disabled = true; btn.textContent = '…'; }
    var url = '/api/inactive-users/csv' + (params.toString() ? '?' + params.toString() : '');
    // Use a hidden anchor so the browser triggers a file download
    var a = document.createElement('a');
    a.href = url;
    a.download = '';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function() {
        if (btn) { btn.disabled = false; btn.innerHTML = '&#x2913; ' + (window.T && window.T.inactive_users_csv || 'Inactive Users'); }
    }, 2000);
}

// ── Export Snapshot ─────────────────────────────────────────

async function exportSnapshot() {
    var btn = document.getElementById('exportSnapshotBtn');
    var originalText = btn ? btn.textContent.trim() : 'Export Snapshot';
    if (btn) { btn.textContent = '⏳ Exporting…'; btn.disabled = true; }

    try {
        // 1. Inline CSS
        var cssText = '';
        try {
            var cssResp = await fetch('/static/css/dashboard.css');
            cssText = await cssResp.text();
        } catch(e) {}

        // 2. Convert Plotly charts to PNG images
        var CHART_IDS = [
            'adoptionChart', 'featureChart', 'topUsersChart',
            'suggestedAcceptedChart', 'usageTrendChart',
            'productivityTrendChart', 'productivityTrendSeatsChart',
        ];
        var chartImages = {};
        await Promise.all(CHART_IDS.map(async function(id) {
            var el = document.getElementById(id);
            if (!el || !el.data || !el.data.length) return;
            try {
                var w = Math.max(el.clientWidth || 0, 600);
                var h = Math.max(el.clientHeight || 0, 320);
                chartImages[id] = await Plotly.toImage(el, { format: 'png', width: w, height: h });
            } catch(e) {}
        }));

        // 3. Clone main content, strip interactivity
        var main = document.querySelector('main.container');
        if (!main) throw new Error('Could not find dashboard content');
        var clone = main.cloneNode(true);

        // Replace each Plotly chart div with a static <img>
        CHART_IDS.forEach(function(id) {
            var div = clone.querySelector('#' + id);
            if (!div) return;
            if (chartImages[id]) {
                div.innerHTML = '<img src="' + chartImages[id] + '" style="width:100%;height:auto;display:block;">';
            } else {
                div.innerHTML = '<p style="color:#8b949e;padding:16px">Chart not available</p>';
            }
            div.style.height = 'auto';
            div.style.minHeight = '0';
        });

        // Remove interactive / noisy elements
        var removeSelectors = [
            '.org-filter-bar',
            '.btn-export-snapshot',
            '.chart-help-btn',
            '.chart-help-text',
            '.filter-reset-btn',
            '.dashboard-header-right',   // whole right cluster (filters + button)
        ];
        removeSelectors.forEach(function(sel) {
            clone.querySelectorAll(sel).forEach(function(el) { el.remove(); });
        });

        // Replace ROI inputs with plain values so the snapshot still shows the numbers
        ['roiHourlyRate', 'roiLicenseCost', 'roiMinPerEdit', 'roiReviewFactor'].forEach(function(id) {
            var inp = clone.querySelector('#' + id);
            if (!inp) return;
            var wrap = inp.closest('.roi-input-wrap');
            if (wrap) {
                var unit = wrap.querySelector('.roi-unit');
                var unitText = unit ? unit.textContent : '';
                var span = document.createElement('span');
                span.style.cssText = 'font-weight:600;color:var(--text-primary)';
                span.textContent = inp.value + ' ' + unitText;
                wrap.replaceWith(span);
            }
        });

        // Strip HTMX attributes
        clone.querySelectorAll('[hx-get],[hx-post],[hx-trigger],[hx-swap]').forEach(function(el) {
            ['hx-get','hx-post','hx-trigger','hx-swap','hx-target'].forEach(function(a) { el.removeAttribute(a); });
        });

        // 4. Build filter label for the banner
        var filterLabel = '';
        if (typeof _activeFilter !== 'undefined' && _activeFilter.level && _activeFilter.value) {
            filterLabel = ' · Filter: ' + _activeFilter.value;
        } else {
            filterLabel = ' · All Users';
        }
        var now = new Date();
        var ts = now.getUTCFullYear() + '-' +
            String(now.getUTCMonth() + 1).padStart(2, '0') + '-' +
            String(now.getUTCDate()).padStart(2, '0') + ' ' +
            String(now.getUTCHours()).padStart(2, '0') + ':' +
            String(now.getUTCMinutes()).padStart(2, '0');
        var fileName = 'copilot-pulse-' + ts.replace(/[: ]/g, '-') + '.html';

        // 5. Assemble the static HTML document
        var html = '<!DOCTYPE html>\n' +
            '<html lang="en">\n<head>\n' +
            '<meta charset="UTF-8">\n' +
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n' +
            '<title>Copilot Pulse Snapshot \u2014 ' + ts + '</title>\n' +
            '<style>\n' +
            '*, *::before, *::after { box-sizing: border-box; }\n' +
            'body { margin: 0; background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }\n' +
            '.snapshot-banner { background: #161b22; border-bottom: 2px solid #58a6ff; padding: 12px 24px; display: flex; justify-content: space-between; align-items: center; }\n' +
            '.snapshot-title { color: #58a6ff; font-weight: 600; font-size: 15px; }\n' +
            '.snapshot-meta { color: #8b949e; font-size: 12px; }\n' +
            cssText + '\n' +
            '</style>\n</head>\n<body>\n' +
            '<div class="snapshot-banner">\n' +
            '  <span class="snapshot-title">&#9672; Copilot Pulse \u2014 Dashboard Snapshot</span>\n' +
            '  <span class="snapshot-meta">Exported: ' + ts + ' UTC' + filterLabel + '</span>\n' +
            '</div>\n' +
            clone.outerHTML + '\n' +
            '</body>\n</html>';

        // 6. Trigger download
        var blob = new Blob([html], { type: 'text/html;charset=utf-8' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(function() { URL.revokeObjectURL(url); }, 2000);

    } catch(e) {
        alert('Export failed: ' + e.message);
    } finally {
        if (btn) { btn.textContent = originalText; btn.disabled = false; }
    }
}

// ── Initialize ──────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
    initChat();
    initSetup();
    initOrgFilters();
    initDashboardCharts();
    initROI();
    loadVirtualFTE();
});
