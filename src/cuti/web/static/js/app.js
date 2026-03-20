const cutiState = {
    summary: null,
    refreshHandle: null,
};

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

async function fetchJSON(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
        ...options,
    });

    if (!response.ok) {
        let detail = response.statusText;
        try {
            const payload = await response.json();
            detail = payload.detail || payload.message || JSON.stringify(payload);
        } catch (_error) {
            // Ignore JSON parse failures and fall back to status text.
        }
        throw new Error(detail || `Request failed with status ${response.status}`);
    }

    return response.json();
}

function showToast(title, message, tone = 'info') {
    const stack = document.getElementById('toastStack');
    if (!stack) {
        return;
    }

    const toneClass = tone === 'error' ? 'status-missing' : tone === 'success' ? 'status-ready' : 'status-selected';
    const toast = document.createElement('div');
    toast.className = `toast ${toneClass}`;
    toast.innerHTML = `<strong>${escapeHtml(title)}</strong><span>${escapeHtml(message)}</span>`;
    stack.appendChild(toast);
    window.setTimeout(() => toast.remove(), 3600);
}

async function copyText(text, label) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied', `${label} copied to clipboard.`, 'success');
    } catch (_error) {
        showToast('Copy failed', 'Clipboard access was denied.', 'error');
    }
}

function renderEmptyState(message) {
    return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function formatDate(value) {
    if (!value) {
        return 'unknown';
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return escapeHtml(value);
    }
    return parsed.toLocaleString();
}

function statusClass(value, prefix = 'status') {
    const normalized = String(value || '').toLowerCase().replace(/\s+/g, '_');
    return `${prefix}-${normalized}`;
}

function summarizeProviderDetail(status) {
    const paths = status.existing_state_paths || [];
    return `${status.detail} ${paths.length ? `Detected ${paths.length} state path${paths.length === 1 ? '' : 's'}.` : 'No state paths detected.'}`;
}

function updateHeader(summary) {
    const primary = document.getElementById('headerPrimaryProvider');
    const queue = document.getElementById('headerQueueState');
    const selected = document.getElementById('headerSelectedProviders');
    const refreshed = document.getElementById('headerLastRefresh');
    const selectedProviders = summary?.providers?.selected_providers || [];

    if (primary) {
        primary.textContent = summary?.providers?.primary_provider ? `primary ${summary.providers.primary_provider}` : 'no provider selected';
    }
    if (queue) {
        const queued = summary?.queue?.status_counts?.queued || 0;
        queue.textContent = summary?.queue?.available ? `${queued} queued` : 'queue unavailable';
    }
    if (selected) {
        selected.textContent = selectedProviders.length ? selectedProviders.join(', ') : 'No providers selected';
    }
    if (refreshed) {
        refreshed.textContent = formatDate(summary?.generated_at);
    }
}

function renderMetrics(summary) {
    document.getElementById('metricProviders').textContent = `${summary.providers.selected_count}`;
    document.getElementById('metricProvidersDetail').textContent = `${summary.providers.ready_count} ready on host`;

    document.getElementById('metricAttention').textContent = `${summary.attention_items.length}`;
    document.getElementById('metricAttentionDetail').textContent = summary.attention_items[0]?.title || 'No immediate drift detected';

    document.getElementById('metricQueue').textContent = `${summary.queue.total_prompts}`;
    document.getElementById('metricQueueDetail').textContent = summary.queue.detail;

    document.getElementById('metricSessions').textContent = `${summary.sessions.recent_sessions.length}`;
    document.getElementById('metricSessionsDetail').textContent = summary.sessions.current_session_id ? `current ${summary.sessions.current_session_id.slice(0, 12)}...` : 'No current Claude session';
}

function renderAttention(summary) {
    const node = document.getElementById('attentionList');
    const items = summary.attention_items || [];
    node.innerHTML = items.length ? items.map((item) => `
        <article class="list-item">
            <div class="list-item-head">
                <div>
                    <h3 class="item-title">${escapeHtml(item.title)}</h3>
                    <p class="item-copy">${escapeHtml(item.detail)}</p>
                </div>
                <span class="status-badge ${statusClass(item.severity)}">${escapeHtml(item.severity)}</span>
            </div>
            ${item.command ? `<div class="list-item-footer"><button class="command-pill mono" type="button" data-action="copy-command" data-command="${escapeHtml(item.command)}">${escapeHtml(item.command)}</button></div>` : ''}
        </article>
    `).join('') : renderEmptyState('No action items.');
}

function renderProviders(summary) {
    const node = document.getElementById('providerMatrix');
    const items = summary.providers.items || [];
    node.innerHTML = items.length ? items.map((item) => `
        <article class="list-item">
            <div class="list-item-head">
                <div>
                    <h3 class="item-title">${escapeHtml(item.title)}</h3>
                    <p class="item-copy">${escapeHtml(summarizeProviderDetail(item))}</p>
                    <div class="badge-row">
                        <span class="badge mono">${escapeHtml(item.provider)}</span>
                        <span class="badge">${item.enabled ? 'selected' : 'available'}</span>
                        ${item.host_command_path ? `<span class="badge mono">${escapeHtml(item.host_command_path)}</span>` : ''}
                    </div>
                </div>
                <span class="status-badge ${statusClass(item.setup_state)}">${escapeHtml(item.setup_state)}</span>
            </div>
        </article>
    `).join('') : renderEmptyState('No provider data available.');
}

function renderHistory(summary) {
    const node = document.getElementById('historyList');
    const items = summary.history.recent || [];
    node.innerHTML = items.length ? items.map((item) => {
        const status = item.success === true ? 'ready' : item.success === false ? 'missing' : 'selected';
        return `
            <article class="list-item">
                <div class="list-item-head">
                    <div>
                        <h3 class="item-title">${escapeHtml(item.content)}</h3>
                        <p class="item-copy mono">${escapeHtml(item.working_directory || '.')}
                        </p>
                        <div class="badge-row">
                            <span class="badge mono">${escapeHtml(formatDate(item.timestamp))}</span>
                            ${(item.context_files || []).slice(0, 3).map((file) => `<span class="badge mono">${escapeHtml(file)}</span>`).join('')}
                        </div>
                    </div>
                    <span class="status-badge status-${status}">${item.success === true ? 'success' : item.success === false ? 'failed' : 'recorded'}</span>
                </div>
            </article>
        `;
    }).join('') : renderEmptyState('No prompt history recorded yet.');
}

function renderSessions(summary) {
    const node = document.getElementById('sessionList');
    const items = summary.sessions.recent_sessions || [];
    const currentStats = summary.sessions.current_stats;
    const currentSession = summary.sessions.current_session_id;
    const statsCard = currentStats ? `
        <article class="list-item">
            <div class="list-item-head">
                <div>
                    <h3 class="item-title">Current session</h3>
                    <p class="item-copy mono">${escapeHtml(currentSession)}</p>
                    <div class="badge-row">
                        <span class="badge">${escapeHtml(currentStats.total_prompts || 0)} prompts</span>
                        <span class="badge">${escapeHtml(currentStats.total_responses || 0)} responses</span>
                        <span class="badge">${escapeHtml(currentStats.total_tokens || 0)} tokens</span>
                    </div>
                </div>
                <span class="status-badge status-ready">live</span>
            </div>
        </article>
    ` : '';

    const sessions = items.map((item) => `
        <article class="list-item">
            <div class="list-item-head">
                <div>
                    <h3 class="item-title mono">${escapeHtml(item.session_id.slice(0, 12))}...</h3>
                    <p class="item-copy">Started ${escapeHtml(formatDate(item.start_time))}</p>
                    <div class="badge-row">
                        <span class="badge">${escapeHtml(item.prompt_count)} prompts</span>
                        <span class="badge mono">last ${escapeHtml(formatDate(item.last_activity))}</span>
                    </div>
                </div>
                <span class="status-badge status-selected">session</span>
            </div>
        </article>
    `).join('');

    node.innerHTML = (statsCard || sessions) ? `${statsCard}${sessions}` : renderEmptyState('No Claude session logs for this workspace yet.');
}

function renderWorkspace(summary) {
    const node = document.getElementById('workspaceList');
    const items = summary.workspace.instruction_files || [];
    node.innerHTML = items.length ? items.map((item) => {
        let badge = 'status-selected';
        let label = item.selected ? 'selected' : 'unselected';
        if (item.selected && !item.exists) {
            badge = 'status-missing';
            label = 'missing';
        } else if (item.exists && item.selected) {
            badge = 'status-ready';
            label = 'present';
        }
        return `
            <article class="list-item">
                <div class="list-item-head">
                    <div>
                        <h3 class="item-title mono">${escapeHtml(item.name)}</h3>
                        <p class="item-copy mono">${escapeHtml(item.path)}</p>
                        <div class="badge-row">
                            <span class="badge">${item.selected ? 'selected by providers' : 'not selected'}</span>
                            ${item.exists ? `<span class="badge">${item.has_tools_section ? 'has tool section' : 'no tool section'}</span>` : ''}
                        </div>
                    </div>
                    <span class="status-badge ${badge}">${label}</span>
                </div>
            </article>
        `;
    }).join('') : renderEmptyState('No workspace instruction data.');
}

function renderTools(summary) {
    const node = document.getElementById('toolList');
    const items = summary.tools.missing_enabled || [];
    node.innerHTML = items.length ? items.map((item) => `
        <article class="list-item">
            <div class="list-item-head">
                <div>
                    <h3 class="item-title">${escapeHtml(item.display_name)}</h3>
                    <p class="item-copy">Enabled in workspace state, but not installed on this machine.</p>
                    <div class="badge-row">
                        <span class="badge">${escapeHtml(item.category)}</span>
                        ${item.auto_install ? '<span class="badge">auto-install</span>' : ''}
                    </div>
                </div>
                <span class="status-badge status-missing">missing</span>
            </div>
        </article>
    `).join('') : renderEmptyState('Enabled tools and installed tools are aligned.');
}

function renderCommands(summary) {
    const node = document.getElementById('commandStrip');
    const commands = summary.recommended_commands || [];
    node.innerHTML = commands.length ? commands.map((command) => `
        <button class="command-pill mono" type="button" data-action="copy-command" data-command="${escapeHtml(command)}">${escapeHtml(command)}</button>
    `).join('') : renderEmptyState('No suggested commands.');
}

function bindCopyActions() {
    document.querySelectorAll('[data-action="copy-command"]').forEach((button) => {
        if (button.dataset.bound === 'true') {
            return;
        }
        button.dataset.bound = 'true';
        button.addEventListener('click', () => copyText(button.dataset.command, 'Command'));
    });
}

function renderOps(summary) {
    updateHeader(summary);
    renderMetrics(summary);
    renderAttention(summary);
    renderProviders(summary);
    renderHistory(summary);
    renderSessions(summary);
    renderWorkspace(summary);
    renderTools(summary);
    renderCommands(summary);
    bindCopyActions();
}

async function refreshOps() {
    const summary = await fetchJSON('/api/ops/summary');
    cutiState.summary = summary;
    renderOps(summary);
}

async function initializeOpsPage() {
    try {
        await refreshOps();
    } catch (error) {
        showToast('Ops console unavailable', error.message, 'error');
        return;
    }

    if (cutiState.refreshHandle !== null) {
        window.clearInterval(cutiState.refreshHandle);
    }
    cutiState.refreshHandle = window.setInterval(async () => {
        try {
            await refreshOps();
        } catch (error) {
            showToast('Refresh failed', error.message, 'error');
        }
    }, 15000);
}

document.addEventListener('DOMContentLoaded', () => {
    if (window.cutiPage === 'ops') {
        initializeOpsPage();
    }
});
