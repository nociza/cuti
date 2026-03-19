const cutiState = {
    summary: null,
    providers: null,
    tools: [],
    toolFilter: 'all',
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
        } catch (error) {
            // Ignore JSON parse failures and fall back to status text.
        }
        throw new Error(detail || `Request failed with status ${response.status}`);
    }

    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
        return response.json();
    }
    return null;
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
    } catch (error) {
        showToast('Copy failed', 'Clipboard access was denied.', 'error');
    }
}

function statusClass(value, prefix = 'status') {
    const normalized = String(value || '').toLowerCase().replace(/\s+/g, '_');
    return `${prefix}-${normalized}`;
}

function renderEmptyState(message) {
    return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function promptItem(prompt) {
    return `
        <article class="list-item">
            <div class="list-item-head">
                <div>
                    <h3 class="item-title">${escapeHtml(prompt.content)}</h3>
                    <div class="item-meta">
                        <span class="badge mono">${escapeHtml(prompt.id)}</span>
                        <span class="badge">Priority ${escapeHtml(prompt.priority)}</span>
                    </div>
                </div>
                <span class="status-badge ${statusClass(prompt.status, 'queue')}">${escapeHtml(prompt.status)}</span>
            </div>
        </article>
    `;
}

function todoItem(todo, actions = true) {
    const buttons = actions ? `
        <div class="item-actions">
            <button class="card-action compact-button" type="button" data-action="todo-status" data-id="${escapeHtml(todo.id)}" data-status="in_progress">Start</button>
            <button class="card-action compact-button" type="button" data-action="todo-status" data-id="${escapeHtml(todo.id)}" data-status="completed">Complete</button>
            <button class="card-action compact-button" type="button" data-action="todo-status" data-id="${escapeHtml(todo.id)}" data-status="blocked">Block</button>
            <button class="card-action compact-button" type="button" data-action="todo-convert" data-id="${escapeHtml(todo.id)}">Queue it</button>
        </div>
    ` : '';

    return `
        <article class="list-item">
            <div class="list-item-head">
                <div>
                    <h3 class="item-title">${escapeHtml(todo.content)}</h3>
                    <div class="item-meta">
                        <span class="badge">Priority ${escapeHtml(todo.priority)}</span>
                        <span class="badge mono">${escapeHtml(todo.id)}</span>
                    </div>
                </div>
                <span class="status-badge ${statusClass(todo.status, 'todo')}">${escapeHtml(todo.status)}</span>
            </div>
            ${buttons}
        </article>
    `;
}

function agentCard(agent) {
    const capabilities = (agent.capabilities || []).slice(0, 4).map((value) => `<span class="badge">${escapeHtml(value)}</span>`).join('');
    const tools = (agent.tools || []).slice(0, 4).map((value) => `<span class="badge mono">${escapeHtml(value)}</span>`).join('');
    return `
        <article class="agent-card">
            <div class="card-head">
                <div class="card-title-block">
                    <p class="card-kicker">${agent.is_local ? 'Local agent' : 'Shared agent'}</p>
                    <h3 class="card-title">${escapeHtml(agent.name)}</h3>
                </div>
                <span class="status-badge status-selected">${agent.is_builtin ? 'builtin' : agent.agent_type || 'claude'}</span>
            </div>
            <p class="card-copy">${escapeHtml(agent.description || 'No description')}</p>
            <div class="badge-row">${capabilities || '<span class="badge">No capabilities tagged</span>'}</div>
            <div class="badge-row">${tools || '<span class="badge mono">No tools tagged</span>'}</div>
        </article>
    `;
}

function updateHeader(summary) {
    const primary = document.getElementById('headerPrimaryProvider');
    const queue = document.getElementById('headerQueueState');
    const selected = document.getElementById('headerSelectedProviders');
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
}

async function refreshSummary() {
    cutiState.summary = await fetchJSON('/api/dashboard/summary');
    updateHeader(cutiState.summary);
    return cutiState.summary;
}

function attachPromptForm(form, onSuccess) {
    if (!form || form.dataset.bound === 'true') {
        return;
    }
    form.dataset.bound = 'true';
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(form);
        const content = (formData.get('content') || '').toString().trim();
        if (!content) {
            showToast('Prompt required', 'Write a prompt before submitting.', 'error');
            return;
        }
        const contextFiles = (formData.get('context_files') || '')
            .toString()
            .split(',')
            .map((value) => value.trim())
            .filter(Boolean);

        try {
            await fetchJSON('/api/queue/prompts', {
                method: 'POST',
                body: JSON.stringify({
                    content,
                    priority: Number(formData.get('priority') || 1),
                    working_directory: (formData.get('working_directory') || window.cutiWorkingDirectory || '.').toString(),
                    context_files: contextFiles,
                }),
            });
            form.reset();
            showToast('Queued', 'Prompt added to the queue.', 'success');
            await onSuccess();
        } catch (error) {
            showToast('Queue failed', error.message, 'error');
        }
    });
}

function attachTodoForm(form, onSuccess) {
    if (!form || form.dataset.bound === 'true') {
        return;
    }
    form.dataset.bound = 'true';
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(form);
        const content = (formData.get('content') || '').toString().trim();
        if (!content) {
            showToast('Todo required', 'Write a todo before submitting.', 'error');
            return;
        }
        try {
            await fetchJSON('/api/todos/', {
                method: 'POST',
                body: JSON.stringify({
                    content,
                    priority: (formData.get('priority') || 'medium').toString(),
                }),
            });
            form.reset();
            showToast('Todo added', 'The new work item has been saved.', 'success');
            await onSuccess();
        } catch (error) {
            showToast('Todo failed', error.message, 'error');
        }
    });
}

function renderDashboard(summary) {
    document.getElementById('metricProviders').textContent = `${summary.providers.selected_providers.length}`;
    document.getElementById('metricProvidersDetail').textContent = `${summary.providers.items.filter((item) => item.setup_state === 'ready').length} ready on host`;
    document.getElementById('metricQueue').textContent = `${summary.queue.total_prompts}`;
    document.getElementById('metricQueueDetail').textContent = summary.queue.detail;
    document.getElementById('metricTodos').textContent = `${summary.todos.statistics.completion_percentage}%`;
    document.getElementById('metricTodosDetail').textContent = `${summary.todos.statistics.in_progress} in progress, ${summary.todos.statistics.pending} pending`;
    document.getElementById('metricTools').textContent = `${summary.tools.enabled_count}/${summary.tools.total_count}`;
    document.getElementById('metricToolsDetail').textContent = `${summary.tools.installed_count} installed on host`;

    const commandStrip = document.getElementById('dashboardQuickCommands');
    if (commandStrip) {
        const commands = [summary.quickstart.container, ...summary.quickstart.providers, ...summary.quickstart.refresh];
        commandStrip.innerHTML = commands.map((command) => `
            <button class="command-pill mono" type="button" data-action="copy-command" data-command="${escapeHtml(command)}">${escapeHtml(command)}</button>
        `).join('');
        if (commandStrip.dataset.bound !== 'true') {
            commandStrip.dataset.bound = 'true';
            commandStrip.addEventListener('click', (event) => {
                const button = event.target.closest('[data-action="copy-command"]');
                if (!button) {
                    return;
                }
                copyText(button.dataset.command, 'Command');
            });
        }
    }

    const providerList = document.getElementById('dashboardProviders');
    providerList.innerHTML = summary.providers.items
        .slice(0, 4)
        .map((item) => `
            <article class="list-item">
                <div class="list-item-head">
                    <div>
                        <h3 class="item-title">${escapeHtml(item.title)}</h3>
                        <p class="item-copy">${escapeHtml(item.detail)}</p>
                    </div>
                    <span class="status-badge ${statusClass(item.setup_state)}">${escapeHtml(item.setup_state)}</span>
                </div>
            </article>
        `)
        .join('') || renderEmptyState('No provider data available.');

    const promptList = document.getElementById('dashboardPromptList');
    promptList.innerHTML = summary.queue.recent_prompts.length
        ? summary.queue.recent_prompts.map(promptItem).join('')
        : renderEmptyState('No prompts are queued yet.');

    const todoList = document.getElementById('dashboardTodoList');
    todoList.innerHTML = summary.todos.top_items.length
        ? summary.todos.top_items.slice(0, 5).map((todo) => todoItem(todo, false)).join('')
        : renderEmptyState('No todos captured yet.');

    const instructionList = document.getElementById('instructionFileList');
    instructionList.innerHTML = summary.workspace.instruction_files.map((item) => `
        <article class="list-item">
            <div class="list-item-head">
                <div>
                    <h3 class="item-title mono">${escapeHtml(item.name)}</h3>
                    <p class="item-copy mono">${escapeHtml(item.path)}</p>
                </div>
                <span class="status-badge ${item.exists ? 'status-ready' : 'status-missing'}">${item.exists ? 'present' : 'missing'}</span>
            </div>
        </article>
    `).join('');

    attachPromptForm(document.getElementById('promptForm'), async () => {
        const updated = await refreshSummary();
        renderDashboard(updated);
    });
}

async function loadProvidersPage(summary) {
    const data = await fetchJSON('/api/providers');
    cutiState.providers = data;
    const summaryNode = document.getElementById('providerSelectionSummary');
    summaryNode.innerHTML = [
        `<span class="badge">Primary ${escapeHtml(data.primary_provider || 'none')}</span>`,
        ...data.selected_providers.map((item) => `<span class="badge mono">${escapeHtml(item)}</span>`),
    ].join('') || '<span class="badge">No providers selected</span>';

    const grid = document.getElementById('providersGrid');
    grid.innerHTML = data.items.map((item) => {
        const setupCommand = item.setup_command || '';
        const updateCommand = item.update_command || '';
        const statePaths = (item.state_paths || []).map((path) => `<span class="badge mono">${escapeHtml(path)}</span>`).join('');
        const existingPaths = (item.existing_state_paths || []).map((path) => `<span class="badge mono">${escapeHtml(path)}</span>`).join('');
        return `
            <article class="provider-card">
                <div class="card-head">
                    <div class="card-title-block">
                        <p class="card-kicker">${item.enabled ? 'Selected for container' : 'Available on demand'}</p>
                        <h2 class="card-title">${escapeHtml(item.title)}</h2>
                    </div>
                    <span class="status-badge ${statusClass(item.setup_state)}">${escapeHtml(item.setup_state)}</span>
                </div>
                <p class="card-copy">${escapeHtml(item.detail)}</p>
                <div class="kv-list">
                    <div class="kv-row"><span>Container command</span><span class="mono">${escapeHtml((item.commands || []).join(', ') || 'n/a')}</span></div>
                    <div class="kv-row"><span>Host CLI</span><span class="mono">${escapeHtml(item.host_command_path || 'container-managed')}</span></div>
                    <div class="kv-row"><span>Setup</span><span>${escapeHtml(item.setup_hint || 'No setup flow documented')}</span></div>
                    <div class="kv-row"><span>Update</span><span>${escapeHtml(item.update_hint || 'No update flow documented')}</span></div>
                </div>
                <div class="badge-row">${statePaths || '<span class="badge mono">No state paths</span>'}</div>
                <div class="badge-row">${existingPaths || '<span class="badge">No detected state files</span>'}</div>
                <div class="card-actions">
                    <button class="primary-button compact-button" type="button" data-action="toggle-provider" data-provider="${escapeHtml(item.provider)}" data-enabled="${item.enabled ? 'true' : 'false'}">${item.enabled ? 'Disable' : 'Enable'}</button>
                    ${setupCommand ? `<button class="card-action compact-button mono" type="button" data-action="copy-command" data-command="${escapeHtml(`cuti providers auth ${item.provider} --login`)}">Copy auth command</button>` : ''}
                    ${updateCommand ? `<button class="card-action compact-button mono" type="button" data-action="copy-command" data-command="${escapeHtml(`cuti providers update ${item.provider}`)}">Copy update command</button>` : ''}
                </div>
            </article>
        `;
    }).join('');

    grid.addEventListener('click', async (event) => {
        const button = event.target.closest('button');
        if (!button) {
            return;
        }
        if (button.dataset.action === 'copy-command') {
            return copyText(button.dataset.command, 'Command');
        }
        if (button.dataset.action !== 'toggle-provider') {
            return;
        }

        const nextEnabled = button.dataset.enabled !== 'true';
        try {
            await fetchJSON(`/api/providers/${button.dataset.provider}/selection`, {
                method: 'PUT',
                body: JSON.stringify({ enabled: nextEnabled }),
            });
            showToast('Provider updated', `${button.dataset.provider} ${nextEnabled ? 'enabled' : 'disabled'}.`, 'success');
            const updatedSummary = await refreshSummary();
            await loadProvidersPage(updatedSummary);
        } catch (error) {
            showToast('Provider update failed', error.message, 'error');
        }
    }, { once: true });
}

async function loadTasksPage() {
    attachPromptForm(document.getElementById('tasksPromptForm'), loadTasksPage);
    attachTodoForm(document.getElementById('todoForm'), loadTasksPage);

    let prompts = [];
    try {
        prompts = await fetchJSON('/api/queue/prompts?limit=12');
    } catch (error) {
        showToast('Queue unavailable', error.message, 'error');
    }

    let todosPayload = { master_todos: [] };
    try {
        todosPayload = await fetchJSON('/api/todos/');
    } catch (error) {
        showToast('Todos unavailable', error.message, 'error');
    }

    const promptsNode = document.getElementById('tasksPromptList');
    promptsNode.innerHTML = prompts.length ? prompts.map(promptItem).join('') : renderEmptyState('No queued prompts yet.');

    const todos = (todosPayload.master_todos || []).map((entry) => entry.todo);
    const todoNode = document.getElementById('tasksTodoList');
    todoNode.innerHTML = todos.length ? todos.map((todo) => todoItem(todo, true)).join('') : renderEmptyState('No todo items yet.');

    todoNode.addEventListener('click', async (event) => {
        const button = event.target.closest('button');
        if (!button) {
            return;
        }
        try {
            if (button.dataset.action === 'todo-status') {
                await fetchJSON(`/api/todos/${button.dataset.id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ status: button.dataset.status }),
                });
                showToast('Todo updated', `Marked ${button.dataset.id} as ${button.dataset.status}.`, 'success');
            }
            if (button.dataset.action === 'todo-convert') {
                await fetchJSON(`/api/todos/${button.dataset.id}/convert-to-prompt`, { method: 'POST' });
                showToast('Queued from todo', `Todo ${button.dataset.id} converted into a prompt.`, 'success');
            }
            await refreshSummary();
            await loadTasksPage();
        } catch (error) {
            showToast('Todo action failed', error.message, 'error');
        }
    }, { once: true });
}

function toolCard(tool) {
    return `
        <article class="tool-card" data-tool-card="${escapeHtml(tool.name)}" data-enabled="${tool.enabled ? 'true' : 'false'}" data-installed="${tool.installed ? 'true' : 'false'}" data-auto="${tool.auto_install ? 'true' : 'false'}">
            <div class="card-head">
                <div class="card-title-block">
                    <p class="card-kicker">${escapeHtml(tool.category)}</p>
                    <h2 class="card-title">${escapeHtml(tool.display_name)}</h2>
                </div>
                <span class="status-badge ${tool.installed ? 'status-ready' : 'status-missing'}">${tool.installed ? 'installed' : 'missing'}</span>
            </div>
            <p class="card-copy">${escapeHtml(tool.description)}</p>
            <div class="badge-row">
                <span class="badge ${tool.enabled ? 'status-selected' : ''}">${tool.enabled ? 'enabled' : 'disabled'}</span>
                <span class="badge">${tool.auto_install ? 'auto-install on' : 'manual install'}</span>
            </div>
            <div class="card-actions">
                <button class="primary-button compact-button" type="button" data-action="toggle-tool" data-tool="${escapeHtml(tool.name)}">${tool.enabled ? 'Disable' : 'Enable'}</button>
                <button class="card-action compact-button" type="button" data-action="toggle-auto" data-tool="${escapeHtml(tool.name)}">${tool.auto_install ? 'Disable auto-install' : 'Enable auto-install'}</button>
                <button class="card-action compact-button" type="button" data-action="install-tool" data-tool="${escapeHtml(tool.name)}">Install now</button>
            </div>
        </article>
    `;
}

function renderToolSummary(tools) {
    const summary = document.getElementById('toolSummaryBadges');
    if (!summary) {
        return;
    }
    const enabled = tools.filter((tool) => tool.enabled).length;
    const installed = tools.filter((tool) => tool.installed).length;
    const autoInstall = tools.filter((tool) => tool.auto_install).length;
    summary.innerHTML = `
        <span class="badge">${enabled} enabled</span>
        <span class="badge">${installed} installed</span>
        <span class="badge">${autoInstall} auto-install</span>
    `;
}

function renderToolsGrid() {
    const grid = document.getElementById('toolsGrid');
    if (!grid) {
        return;
    }

    let tools = [...cutiState.tools];
    if (cutiState.toolFilter === 'enabled') {
        tools = tools.filter((tool) => tool.enabled);
    } else if (cutiState.toolFilter === 'missing') {
        tools = tools.filter((tool) => !tool.installed);
    } else if (cutiState.toolFilter === 'auto') {
        tools = tools.filter((tool) => tool.auto_install);
    }

    grid.innerHTML = tools.length ? tools.map(toolCard).join('') : renderEmptyState('No tools match the selected filter.');
}

async function loadToolsPage() {
    cutiState.tools = await fetchJSON('/api/tools/list');
    renderToolSummary(cutiState.tools);
    renderToolsGrid();

    document.querySelectorAll('[data-tool-filter]').forEach((button) => {
        button.onclick = () => {
            document.querySelectorAll('[data-tool-filter]').forEach((item) => item.classList.remove('is-active'));
            button.classList.add('is-active');
            cutiState.toolFilter = button.dataset.toolFilter;
            renderToolsGrid();
        };
    });

    const grid = document.getElementById('toolsGrid');
    grid.addEventListener('click', async (event) => {
        const button = event.target.closest('button');
        if (!button) {
            return;
        }
        const tool = cutiState.tools.find((item) => item.name === button.dataset.tool);
        if (!tool) {
            return;
        }

        try {
            if (button.dataset.action === 'toggle-tool') {
                const result = await fetchJSON('/api/tools/toggle', {
                    method: 'POST',
                    body: JSON.stringify({
                        name: tool.name,
                        enabled: !tool.enabled,
                        auto_install: tool.auto_install,
                    }),
                });
                if (result && result.needs_install) {
                    showToast('Install required', `${tool.display_name} is enabled but not installed yet.`, 'info');
                } else {
                    showToast('Tool updated', `${tool.display_name} ${tool.enabled ? 'disabled' : 'enabled'}.`, 'success');
                }
            }

            if (button.dataset.action === 'toggle-auto') {
                await fetchJSON('/api/tools/toggle', {
                    method: 'POST',
                    body: JSON.stringify({
                        name: tool.name,
                        enabled: tool.enabled,
                        auto_install: !tool.auto_install,
                    }),
                });
                showToast('Auto-install updated', `${tool.display_name} auto-install setting changed.`, 'success');
            }

            if (button.dataset.action === 'install-tool') {
                const result = await fetchJSON(`/api/tools/install?tool_name=${encodeURIComponent(tool.name)}&auto_install=${tool.auto_install ? 'true' : 'false'}`, {
                    method: 'POST',
                });
                if (result && result.success === false) {
                    throw new Error(result.message || `Failed to install ${tool.display_name}.`);
                }
                showToast('Tool install started', `${tool.display_name} install command completed.`, 'success');
            }

            await refreshSummary();
            await loadToolsPage();
        } catch (error) {
            showToast('Tool action failed', error.message, 'error');
        }
    }, { once: true });
}

async function loadAgentsPage(summary) {
    const [agentStatus, agents, orchestration] = await Promise.all([
        fetchJSON('/api/claude-code-agents/status'),
        fetchJSON('/api/claude-code-agents/'),
        fetchJSON('/api/agents/orchestration/status'),
    ]);

    document.getElementById('metricAgentTotal').textContent = `${agentStatus.total_agents}`;
    document.getElementById('metricAgentLocal').textContent = `${agentStatus.local_agents}`;
    document.getElementById('metricAgentBuiltin').textContent = `${agentStatus.builtin_agents}`;
    document.getElementById('metricAgentGemini').textContent = agentStatus.gemini_available ? 'ready' : 'missing';

    const orchestrationPanel = document.getElementById('agentOrchestrationPanel');
    orchestrationPanel.innerHTML = `
        <article class="list-item">
            <div class="list-item-head">
                <div>
                    <h3 class="item-title mono">${escapeHtml(orchestration.claude_md_path || summary.agents.claude_md_path)}</h3>
                    <p class="item-copy">${orchestration.active_agents} active of ${orchestration.total_agents} orchestrated agents</p>
                </div>
                <span class="status-badge ${orchestration.claude_md_exists ? 'status-ready' : 'status-missing'}">${orchestration.claude_md_exists ? 'present' : 'missing'}</span>
            </div>
        </article>
    `;

    const grid = document.getElementById('agentsGrid');
    grid.innerHTML = agents.length ? agents.map(agentCard).join('') : renderEmptyState('No agent definitions found.');

    const reloadButton = document.getElementById('reloadAgentsButton');
    reloadButton.onclick = async () => {
        try {
            await fetchJSON('/api/claude-code-agents/reload', { method: 'POST' });
            showToast('Agents reloaded', 'Agent files were re-read from disk.', 'success');
            await refreshSummary();
            await loadAgentsPage(cutiState.summary || summary);
        } catch (error) {
            showToast('Reload failed', error.message, 'error');
        }
    };
}

async function init() {
    try {
        const summary = await refreshSummary();
        const page = window.cutiPage;

        if (page === 'dashboard') {
            renderDashboard(summary);
        }
        if (page === 'providers') {
            await loadProvidersPage(summary);
        }
        if (page === 'tasks') {
            await loadTasksPage();
        }
        if (page === 'tools') {
            await loadToolsPage();
        }
        if (page === 'agents') {
            await loadAgentsPage(summary);
        }
    } catch (error) {
        showToast('Interface failed to load', error.message, 'error');
    }
}

document.addEventListener('DOMContentLoaded', init);
