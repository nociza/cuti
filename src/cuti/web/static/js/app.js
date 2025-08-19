/**
 * cuti - Main JavaScript Application
 * Unified functionality for all interfaces
 */

// Global utilities
window.cutiUtils = {
    formatTime(timestamp) {
        return new Date(timestamp).toLocaleTimeString('en-US', {hour12: false});
    },
    
    getCurrentTime() {
        return new Date().toLocaleTimeString('en-US', {hour12: false});
    },
    
    formatUptime() {
        const startTime = window.startTime || new Date();
        const now = new Date();
        const diff = now - startTime;
        const hours = Math.floor(diff / 3600000);
        const minutes = Math.floor((diff % 3600000) / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds}s`;
        } else {
            return `${seconds}s`;
        }
    },

    formatMessage(content) {
        // Basic markdown-like formatting
        return content
            .replace(/`([^`]+)`/g, '<span style="background: rgba(96, 165, 250, 0.2); padding: 2px 6px; border-radius: 4px; color: #60a5fa;">$1</span>')
            .replace(/```([\\s\\S]*?)```/g, '<div style="background: rgba(16, 185, 129, 0.1); padding: 12px; margin: 8px 0; border-left: 3px solid #10b981; border-radius: 4px; font-family: JetBrains Mono, monospace;">$1</div>')
            .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong style="color: #10b981;">$1</strong>')
            .replace(/\\*([^*]+)\\*/g, '<em style="color: #f59e0b;">$1</em>')
            .replace(/\\n/g, '<br>');
    },

    formatTerminalMessage(content) {
        // Use the enhanced markdown renderer if available
        if (!content) return '';
        
        if (window.MarkdownRenderer) {
            const renderer = new MarkdownRenderer();
            return renderer.render(content);
        }
        
        // Fallback to basic styling
        return content
            .replace(/`([^`]+)`/g, '<span style="background: rgba(96, 165, 250, 0.2); padding: 2px 6px; border-radius: 4px; color: #60a5fa;">$1</span>')
            .replace(/```([\\s\\S]*?)```/g, '<div style="background: rgba(16, 185, 129, 0.1); padding: 12px; margin: 8px 0; border-left: 3px solid #10b981; border-radius: 4px; font-family: JetBrains Mono, monospace;">$1</div>')
            .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong style="color: #10b981;">$1</strong>')
            .replace(/\\*([^*]+)\\*/g, '<em style="color: #f59e0b;">$1</em>')
            .replace(/\\n/g, '<br>');
    },
    
    // Symphony Mode management
    symphonyMode: false,
    
    toggleSymphonyMode(event) {
        this.symphonyMode = event.target.checked;
        localStorage.setItem('symphonyMode', this.symphonyMode);
        
        // Update UI state
        if (this.symphonyMode) {
            document.body.classList.add('symphony-mode-active');
            this.showNotification('Symphony Mode activated - Agent orchestration enabled', 'success');
        } else {
            document.body.classList.remove('symphony-mode-active');
            this.showNotification('Solo Mode activated - Single agent mode', 'info');
        }
        
        // Notify backend about mode change
        if (window.ws && window.ws.readyState === WebSocket.OPEN) {
            window.ws.send(JSON.stringify({
                type: 'symphony_mode_changed',
                enabled: this.symphonyMode
            }));
        }
    },
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => notification.classList.add('show'), 10);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
};

// Terminal Interface Component
function terminalInterface() {
    return {
        activeTab: 'chat',
        showTodos: true,
        symphonyMode: localStorage.getItem('symphonyMode') === 'true',
        
        // Chat functionality
        chatMessages: JSON.parse(localStorage.getItem('cuti_chat_messages') || '[]'),
        chatInput: '',
        isStreaming: false,
        chatWs: null,
        currentStreamingMessage: null,
        currentThinkingMessage: null,
        todos: [],
        nextTodoId: 1,
        
        // Token counting
        tokenCount: 0,
        inputTokens: 0,
        outputTokens: 0,
        tokenRate: 0,
        totalCost: '$0.0000',
        sessionCost: '$0.0000',
        tokenAnimationTimer: null,
        targetTokenCount: 0,
        
        // History functionality
        commandHistory: [],
        filteredHistory: [],
        historySearch: '',
        historyFilter: 'all',
        successCount: 0,
        todayCount: 0,
        
        // Settings
        settings: {
            claudeCommand: 'claude',
            timeout: 3600,
            checkInterval: 30,
            maxRetries: 3,
            concurrentTasks: 2,
            showTimestamps: true,
            enableSound: false,
            autoScroll: true,
            darkMode: true,
            debugMode: false,
            verboseLogging: false,
            experimentalFeatures: false,
            collectAnalytics: false,
            storagePath: '~/.cuti/',
            model: 'claude-3-opus'
        },
        settingsSection: 'general',
        settingsSaved: true,
        
        // Agent suggestions
        showAgentSuggestions: false,
        agentSuggestions: [],
        selectedSuggestionIndex: 0,
        selectedAgent: null,
        
        // Claude settings
        claudeSettings: {
            model: 'opus',
            cleanupPeriodDays: 180,
            includeCoAuthoredBy: false,
            forceLoginMethod: 'claudeai',
            telemetry: false,
            autoInstall: true,
            maintainWorkingDir: true,
            costWarnings: true,
            errorReporting: true,
            autoUpdater: true
        },
        
        async init() {
            this.connectChatWebSocket();
            this.loadHistory();
            this.loadSettings();
            this.loadClaudeSettings();
            this.loadGroundTruthData();
            
            // Initialize Symphony Mode state
            const symphonyToggle = document.getElementById('symphonyModeToggle');
            if (symphonyToggle) {
                symphonyToggle.checked = this.symphonyMode;
                if (this.symphonyMode) {
                    document.body.classList.add('symphony-mode-active');
                }
            }
            
            // Check if an agent was selected from the agent manager
            const selectedAgent = sessionStorage.getItem('selectedAgent');
            if (selectedAgent) {
                this.chatInput = selectedAgent + ' ';
                sessionStorage.removeItem('selectedAgent');
            }
            
            // Focus input after Alpine initializes
            this.$nextTick(() => {
                if (this.$refs.promptInput) {
                    this.$refs.promptInput.focus();
                }
            });
            // Refresh ground truth data periodically
            setInterval(() => this.loadGroundTruthData(), 5000);
        },
        
        toggleSymphonyMode(event) {
            this.symphonyMode = event.target.checked;
            window.cutiUtils.toggleSymphonyMode(event);
        },
        
        // Method to animate token count
        animateTokenCount(targetValue) {
            if (this.tokenAnimationTimer) {
                clearInterval(this.tokenAnimationTimer);
            }
            
            const startValue = this.tokenCount;
            const difference = targetValue - startValue;
            const duration = 500; // milliseconds
            const steps = 20;
            const increment = difference / steps;
            let currentStep = 0;
            
            this.tokenAnimationTimer = setInterval(() => {
                currentStep++;
                if (currentStep >= steps) {
                    this.tokenCount = targetValue;
                    clearInterval(this.tokenAnimationTimer);
                } else {
                    this.tokenCount = Math.round(startValue + (increment * currentStep));
                }
            }, duration / steps);
        },
        
        connectChatWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            // Use the streaming WebSocket for token tracking
            this.chatWs = new WebSocket(`${protocol}//${window.location.host}/streaming-chat-ws`);
            
            this.chatWs.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                // Handle different message types
                if (data.type === 'connected') {
                    console.log('Connected to streaming chat:', data.session_id);
                } else if (data.type === 'stream_start') {
                    this.isStreaming = true;
                    this.tokenCount = 0;
                    this.inputTokens = data.input_tokens || 0;
                    this.currentStreamingMessage = {
                        id: Date.now(),
                        role: 'assistant',
                        content: '',
                        timestamp: new Date()
                    };
                    // Show input tokens immediately
                    if (data.input_tokens) {
                        this.animateTokenCount(data.input_tokens);
                    }
                } else if (data.type === 'thinking') {
                    // Handle thought process
                    if (!this.currentThinkingMessage) {
                        this.currentThinkingMessage = {
                            id: Date.now() + 1,
                            role: 'thinking',
                            content: '',
                            timestamp: new Date()
                        };
                        this.chatMessages.push(this.currentThinkingMessage);
                    }
                    this.currentThinkingMessage.content += data.content;
                    this.persistChatMessages();
                    this.scrollToBottom();
                } else if (data.type === 'tool_start') {
                    // Show tool usage
                    this.chatMessages.push({
                        id: Date.now(),
                        role: 'system',
                        content: `🔧 Using tool: ${data.tool}`,
                        timestamp: new Date()
                    });
                    this.scrollToBottom();
                } else if (data.type === 'file_operation') {
                    // Show file operations
                    const icon = data.operation === 'read' ? '📖' : '✏️';
                    this.chatMessages.push({
                        id: Date.now(),
                        role: 'system',
                        content: `${icon} ${data.operation === 'read' ? 'Reading' : 'Writing'} file: ${data.file}`,
                        timestamp: new Date()
                    });
                    this.scrollToBottom();
                } else if (data.type === 'command') {
                    // Show command execution
                    this.chatMessages.push({
                        id: Date.now(),
                        role: 'system',
                        content: `💻 Running: ${data.command}`,
                        timestamp: new Date()
                    });
                    this.scrollToBottom();
                } else if (data.type === 'command_output') {
                    // Show command output
                    this.chatMessages.push({
                        id: Date.now(),
                        role: 'system',
                        content: `📋 Output:\n${data.content}`,
                        timestamp: new Date()
                    });
                    this.scrollToBottom();
                } else if (data.type === 'progress') {
                    // Show progress updates
                    this.chatMessages.push({
                        id: Date.now(),
                        role: 'system',
                        content: `⏳ ${data.content}`,
                        timestamp: new Date()
                    });
                    this.scrollToBottom();
                } else if (data.type === 'token_update') {
                    // Update token count with animation
                    if (data.output_tokens) {
                        const totalTokens = (this.inputTokens || 0) + data.output_tokens;
                        this.animateTokenCount(totalTokens);
                        this.outputTokens = data.output_tokens;
                        this.tokenRate = data.token_rate || 0;
                        this.totalCost = data.total_cost || '$0.0000';
                    }
                } else if (data.type === 'text' && this.currentStreamingMessage) {
                    // Clear thinking message when actual response starts
                    if (this.currentThinkingMessage) {
                        this.currentThinkingMessage = null;
                    }
                    this.currentStreamingMessage.content += data.content;
                    this.extractTodosFromContent(data.content);
                    this.scrollToBottom();
                } else if (data.type === 'stream_complete') {
                    if (this.currentStreamingMessage) {
                        this.chatMessages.push(this.currentStreamingMessage);
                        this.currentStreamingMessage = null;
                        this.persistChatMessages();
                        this.scrollToBottom();
                    }
                    // Update final token metrics
                    if (data.token_metrics) {
                        this.tokenCount = data.token_metrics.total_tokens || 0;
                        this.inputTokens = data.token_metrics.input_tokens || 0;
                        this.outputTokens = data.token_metrics.output_tokens || 0;
                        this.totalCost = data.token_metrics.total_cost || '$0.0000';
                        this.sessionCost = data.session_totals?.total_cost || '$0.0000';
                    }
                    this.isStreaming = false;
                    // Keep token count visible for 10 seconds after completion
                    setTimeout(() => {
                        this.tokenCount = 0;
                        this.inputTokens = 0;
                        this.outputTokens = 0;
                    }, 10000);
                    if (this.$refs.promptInput) {
                        this.$refs.promptInput.focus();
                    }
                } else if (data.type === 'error') {
                    this.chatMessages.push({
                        id: Date.now(),
                        role: 'error',
                        content: data.content,
                        timestamp: new Date()
                    });
                    this.persistChatMessages();
                    this.isStreaming = false;
                    if (this.$refs.promptInput) {
                        this.$refs.promptInput.focus();
                    }
                }
            };
            
            this.chatWs.onclose = () => {
                setTimeout(() => this.connectChatWebSocket(), 3000);
            };
        },
        
        sendChatMessage() {
            if (!this.chatInput.trim() || this.isStreaming || !this.chatWs) return;
            
            const messageContent = this.chatInput;
            
            // Add user message
            this.chatMessages.push({
                id: Date.now(),
                role: 'user',
                content: messageContent,
                timestamp: new Date()
            });
            
            // Persist messages immediately
            this.persistChatMessages();
            
            // Add to history
            this.addToHistory(messageContent);
            
            // Send to server
            this.chatWs.send(JSON.stringify({
                type: 'message',
                content: messageContent
            }));
            
            this.chatInput = '';
            this.scrollToBottom();
        },
        
        persistChatMessages() {
            // Keep only last 100 messages to avoid localStorage limits
            const messagesToStore = this.chatMessages.slice(-100);
            localStorage.setItem('cuti_chat_messages', JSON.stringify(messagesToStore));
        },
        
        clearTerminal() {
            this.chatMessages = [];
            this.todos = [];
            this.chatInput = '';
            localStorage.removeItem('cuti_chat_messages');
        },
        
        extractTodosFromContent(content) {
            // Only extract actual TODO items, not random lists
            const todoPatterns = [
                /TODO:\s*(.+)$/gim,
                /\\[\\s*\\]\\s*(.+)$/gm,
                /TASK:\s*(.+)$/gim,
                /FIX:\s*(.+)$/gim,
                /FIXME:\s*(.+)$/gim
            ];
            
            for (const pattern of todoPatterns) {
                const matches = content.matchAll(pattern);
                for (const match of matches) {
                    const todoText = match[1].trim();
                    if (todoText.length > 5 && !this.todos.find(t => t.text === todoText)) {
                        this.todos.push({
                            id: this.nextTodoId++,
                            text: todoText,
                            completed: false,
                            timestamp: new Date()
                        });
                    }
                }
            }
        },
        
        toggleTodo(todoId) {
            const todo = this.todos.find(t => t.id === todoId);
            if (todo) {
                todo.completed = !todo.completed;
            }
        },
        
        formatTerminalMessage(content, role) {
            // Special formatting for thinking messages
            if (role === 'thinking') {
                return '<div style="opacity: 0.7; font-style: italic; color: #94a3b8;">💭 ' + window.cutiUtils.formatTerminalMessage(content) + '</div>';
            }
            return window.cutiUtils.formatTerminalMessage(content);
        },
        
        formatTime(timestamp) {
            return window.cutiUtils.formatTime(timestamp);
        },
        
        scrollToBottom() {
            this.$nextTick(() => {
                const output = document.getElementById('terminalOutput');
                if (output) {
                    output.scrollTop = output.scrollHeight;
                }
            });
        },
        
        // Agent suggestion methods
        async checkForAgentSuggestion() {
            const input = this.chatInput;
            const atIndex = input.lastIndexOf('@');
            console.log('checkForAgentSuggestion:', { input, atIndex });
            
            if (atIndex >= 0 && (atIndex === 0 || input[atIndex - 1] === ' ')) {
                const prefix = input.substring(atIndex + 1);
                console.log('Found @ at position', atIndex, 'prefix:', prefix);
                // Always fetch suggestions, using _all for empty prefix
                await this.fetchAgentSuggestions(prefix);
            } else {
                this.closeSuggestions();
            }
        },
        
        async fetchAgentSuggestions(prefix) {
            try {
                // Use _all for empty prefix to avoid URL issues
                const pathParam = (!prefix || prefix === '') ? '_all' : prefix;
                const url = `/api/claude-code-agents/suggestions/${pathParam}`;
                console.log('Fetching suggestions from:', url, 'prefix:', prefix);
                const response = await fetch(url);
                if (response.ok) {
                    this.agentSuggestions = await response.json();
                    this.showAgentSuggestions = this.agentSuggestions.length > 0;
                    this.selectedSuggestionIndex = 0;
                    console.log('Got suggestions:', this.agentSuggestions.length, 'showAgentSuggestions:', this.showAgentSuggestions);
                } else {
                    console.error('Failed to fetch suggestions:', response.status);
                }
            } catch (error) {
                console.error('Error fetching agent suggestions:', error);
            }
        },
        
        selectAgent(agent) {
            const input = this.chatInput;
            const atIndex = input.lastIndexOf('@');
            this.chatInput = input.substring(0, atIndex) + agent.command + ' ';
            this.selectedAgent = agent;
            this.closeSuggestions();
            this.$refs.promptInput.focus();
        },
        
        acceptSuggestion() {
            if (this.showAgentSuggestions && this.agentSuggestions.length > 0) {
                this.selectAgent(this.agentSuggestions[this.selectedSuggestionIndex]);
            }
        },
        
        closeSuggestions() {
            this.showAgentSuggestions = false;
            this.agentSuggestions = [];
            this.selectedSuggestionIndex = 0;
        },
        
        navigateSuggestions(direction) {
            if (!this.showAgentSuggestions || this.agentSuggestions.length === 0) return;
            
            this.selectedSuggestionIndex += direction;
            
            // Wrap around
            if (this.selectedSuggestionIndex < 0) {
                this.selectedSuggestionIndex = this.agentSuggestions.length - 1;
            } else if (this.selectedSuggestionIndex >= this.agentSuggestions.length) {
                this.selectedSuggestionIndex = 0;
            }
        },
        
        // History methods
        async loadHistory() {
            // Load from Claude's ground truth logs instead of localStorage
            try {
                const response = await fetch('/api/claude-logs/history?limit=100');
                if (response.ok) {
                    const data = await response.json();
                    // Transform Claude log format to our UI format
                    this.commandHistory = data.prompts
                        .filter(p => p.type === 'user')
                        .map(prompt => ({
                            id: prompt.id,
                            content: prompt.content,
                            timestamp: prompt.timestamp,
                            status: 'success',
                            cwd: prompt.cwd,
                            git_branch: prompt.git_branch
                        }));
                    
                    // Calculate stats
                    this.successCount = this.commandHistory.length;
                    const today = new Date().toDateString();
                    this.todayCount = this.commandHistory.filter(item => 
                        new Date(item.timestamp).toDateString() === today
                    ).length;
                    
                    this.filterHistory();
                }
            } catch (error) {
                console.error('Error loading history from Claude logs:', error);
                // Fallback to localStorage if needed
                const saved = localStorage.getItem('cuti_command_history');
                if (saved) {
                    this.commandHistory = JSON.parse(saved);
                } else {
                    this.commandHistory = [];
                }
                this.filterHistory();
            }
        },
        
        filterHistory() {
            let filtered = this.commandHistory;
            
            // Apply status filter
            if (this.historyFilter !== 'all') {
                if (this.historyFilter === 'today') {
                    const today = new Date().toDateString();
                    filtered = filtered.filter(item => 
                        new Date(item.timestamp).toDateString() === today
                    );
                } else {
                    filtered = filtered.filter(item => item.status === this.historyFilter);
                }
            }
            
            // Apply search filter
            if (this.historySearch) {
                const search = this.historySearch.toLowerCase();
                filtered = filtered.filter(item => 
                    item.content.toLowerCase().includes(search) ||
                    (item.status && item.status.toLowerCase().includes(search))
                );
            }
            
            this.filteredHistory = filtered;
        },
        
        copyCommand(content) {
            navigator.clipboard.writeText(content).then(() => {
                // Optional: Show a toast notification
                console.log('Command copied to clipboard');
            });
        },
        
        addToHistory(content) {
            const historyItem = {
                id: Date.now(),
                content: content,
                timestamp: new Date(),
                status: 'success',
                duration: Math.random() * 5 + 's', // Mock duration
                tokens: Math.floor(Math.random() * 1000), // Mock tokens
                cost: (Math.random() * 0.5).toFixed(2) // Mock cost
            };
            this.commandHistory.unshift(historyItem);
            // Keep only last 100 items
            this.commandHistory = this.commandHistory.slice(0, 100);
            localStorage.setItem('cuti_command_history', JSON.stringify(this.commandHistory));
            
            // Update stats
            this.successCount = this.commandHistory.filter(item => item.status === 'success').length;
            const today = new Date().toDateString();
            this.todayCount = this.commandHistory.filter(item => 
                new Date(item.timestamp).toDateString() === today
            ).length;
            
            this.filterHistory();
        },
        
        clearHistory() {
            if (confirm('Are you sure you want to clear all command history?')) {
                this.commandHistory = [];
                this.filteredHistory = [];
                localStorage.removeItem('cuti_command_history');
            }
        },
        
        rerunCommand(content) {
            this.chatInput = content;
            this.activeTab = 'chat';
            this.$nextTick(() => {
                if (this.$refs.promptInput) {
                    this.$refs.promptInput.focus();
                }
            });
        },
        
        // Settings methods
        loadSettings() {
            const saved = localStorage.getItem('cuti_settings');
            if (saved) {
                this.settings = { ...this.settings, ...JSON.parse(saved) };
            }
        },
        
        saveSettings() {
            localStorage.setItem('cuti_settings', JSON.stringify(this.settings));
            this.saveClaudeSettings(); // Also save Claude settings
            this.settingsSaved = true;
            // Show success for 3 seconds
            setTimeout(() => {
                this.settingsSaved = false;
            }, 3000);
        },
        
        // Claude settings methods
        async loadClaudeSettings() {
            try {
                const response = await fetch('/api/claude-settings/essential');
                if (response.ok) {
                    this.claudeSettings = await response.json();
                }
            } catch (error) {
                console.error('Error loading Claude settings:', error);
            }
        },
        
        async saveClaudeSettings() {
            try {
                const response = await fetch('/api/claude-settings/essential', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.claudeSettings)
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    console.error('Error saving Claude settings:', error);
                }
            } catch (error) {
                console.error('Error saving Claude settings:', error);
            }
        },
        
        exportSettings() {
            const settingsData = JSON.stringify(this.settings, null, 2);
            const blob = new Blob([settingsData], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `cuti-settings-${new Date().toISOString().split('T')[0]}.json`;
            a.click();
            URL.revokeObjectURL(url);
        },
        
        resetSettings() {
            if (confirm('Are you sure you want to reset all settings to defaults?')) {
                this.settings = {
                    claudeCommand: 'claude',
                    timeout: 3600,
                    checkInterval: 30,
                    maxRetries: 3,
                    concurrentTasks: 2,
                    showTimestamps: true,
                    enableSound: false,
                    autoScroll: true,
                    darkMode: true,
                    debugMode: false,
                    verboseLogging: false,
                    experimentalFeatures: false,
                    collectAnalytics: false,
                    storagePath: '~/.cuti/',
                    model: 'claude-3-opus'
                };
                this.saveSettings();
            }
        },
        
        // Load ground truth data from Claude logs
        async loadGroundTruthData() {
            try {
                // Load todos from Claude logs
                const todosResponse = await fetch('/api/claude-logs/todos');
                if (todosResponse.ok) {
                    const todosData = await todosResponse.json();
                    if (todosData.todos && todosData.todos.length > 0) {
                        // Update todos from ground truth
                        this.todos = todosData.todos.map((todo, index) => ({
                            id: todo.id || index + 1,
                            text: todo.content,
                            completed: todo.status === 'completed',
                            timestamp: new Date()
                        }));
                    }
                }
                
                // Load session stats
                const statsResponse = await fetch('/api/claude-logs/stats');
                if (statsResponse.ok) {
                    const stats = await statsResponse.json();
                    // Store stats for display if needed
                    this.sessionStats = stats;
                }
            } catch (error) {
                console.error('Error loading ground truth data:', error);
            }
        }
    }
}

// Dashboard Interface Component
function dashboard() {
    return {
        activeTab: 'chat',
        // Chat functionality
        chatMessages: [],
        chatInput: '',
        isStreaming: false,
        chatWs: null,
        currentStreamingMessage: null,
        todos: [],
        nextTodoId: 1,
        
        // Dashboard data
        stats: {},
        prompts: [],
        aliases: [],
        historyEntries: [],
        systemStatus: {},
        performanceMetrics: {},
        queueRunning: true,
        showAddPromptModal: false,
        showCreateAliasModal: false,
        showTaskExpansionModal: false,
        historySearch: '',
        newPrompt: {
            content: '',
            priority: 0,
            working_directory: '.',
            max_retries: 3
        },
        
        async init() {
            await this.loadStats();
            await this.loadPrompts();
            await this.loadAliases();
            await this.loadHistory();
            await this.loadSystemStatus();
            
            // Set up WebSocket connections
            this.connectWebSocket();
            this.connectChatWebSocket();
            
            // Refresh data periodically
            setInterval(() => {
                this.loadStats();
                this.loadPrompts();
                this.loadSystemStatus();
            }, 5000);
        },
        
        // Chat functionality
        connectChatWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            this.chatWs = new WebSocket(`${protocol}//${window.location.host}/chat-ws`);
            
            this.chatWs.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'start') {
                    this.isStreaming = true;
                    this.currentStreamingMessage = {
                        id: Date.now(),
                        role: 'assistant',
                        content: '',
                        timestamp: new Date()
                    };
                } else if (data.type === 'stream' && this.currentStreamingMessage) {
                    this.currentStreamingMessage.content += data.content;
                    this.extractTodosFromContent(data.content);
                } else if (data.type === 'end') {
                    if (this.currentStreamingMessage) {
                        this.chatMessages.push(this.currentStreamingMessage);
                        this.currentStreamingMessage = null;
                        this.scrollChatToBottom();
                    }
                    this.isStreaming = false;
                } else if (data.type === 'error') {
                    this.chatMessages.push({
                        id: Date.now(),
                        role: 'system',
                        content: 'Error: ' + data.content,
                        timestamp: new Date()
                    });
                    this.isStreaming = false;
                }
            };
            
            this.chatWs.onclose = () => {
                setTimeout(() => this.connectChatWebSocket(), 3000);
            };
        },
        
        sendChatMessage() {
            if (!this.chatInput.trim() || this.isStreaming || !this.chatWs) return;
            
            // Add user message
            this.chatMessages.push({
                id: Date.now(),
                role: 'user',
                content: this.chatInput,
                timestamp: new Date()
            });
            
            // Send to server
            this.chatWs.send(JSON.stringify({
                type: 'message',
                content: this.chatInput
            }));
            
            this.chatInput = '';
            this.scrollChatToBottom();
        },
        
        extractTodosFromContent(content) {
            // Extract todos from Claude's output using regex patterns
            const todoPatterns = [
                /^\d+\.\s*(.+)$/gm,  // Numbered lists
                /^[-*]\s*(.+)$/gm,   // Bullet points
                /TODO:\s*(.+)$/gim,  // Explicit TODO
                /\\[\\s*\\]\\s*(.+)$/gm // Checkbox format
            ];
            
            for (const pattern of todoPatterns) {
                const matches = content.matchAll(pattern);
                for (const match of matches) {
                    const todoText = match[1].trim();
                    if (todoText.length > 10 && !this.todos.find(t => t.text === todoText)) {
                        this.todos.push({
                            id: this.nextTodoId++,
                            text: todoText,
                            completed: false,
                            timestamp: new Date()
                        });
                    }
                }
            }
        },
        
        toggleTodo(todoId) {
            const todo = this.todos.find(t => t.id === todoId);
            if (todo) {
                todo.completed = !todo.completed;
            }
        },
        
        formatMessage(content) {
            return window.cutiUtils.formatMessage(content);
        },
        
        formatTime(timestamp) {
            return window.cutiUtils.formatTime(timestamp);
        },
        
        scrollChatToBottom() {
            this.$nextTick(() => {
                const chatMessages = document.getElementById('chatMessages');
                if (chatMessages) {
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            });
        },
        
        // History methods
        async loadHistory() {
            // Load from Claude's ground truth logs instead of localStorage
            try {
                const response = await fetch('/api/claude-logs/history?limit=100');
                if (response.ok) {
                    const data = await response.json();
                    // Transform Claude log format to our UI format
                    this.commandHistory = data.prompts
                        .filter(p => p.type === 'user')
                        .map(prompt => ({
                            id: prompt.id,
                            content: prompt.content,
                            timestamp: prompt.timestamp,
                            status: 'success',
                            cwd: prompt.cwd,
                            git_branch: prompt.git_branch
                        }));
                    
                    // Calculate stats
                    this.successCount = this.commandHistory.length;
                    const today = new Date().toDateString();
                    this.todayCount = this.commandHistory.filter(item => 
                        new Date(item.timestamp).toDateString() === today
                    ).length;
                    
                    this.filterHistory();
                }
            } catch (error) {
                console.error('Error loading history from Claude logs:', error);
                // Fallback to localStorage if needed
                const saved = localStorage.getItem('cuti_command_history');
                if (saved) {
                    this.commandHistory = JSON.parse(saved);
                } else {
                    this.commandHistory = [];
                }
                this.filterHistory();
            }
        },
        
        filterHistory() {
            let filtered = this.commandHistory;
            
            // Apply status filter
            if (this.historyFilter !== 'all') {
                if (this.historyFilter === 'today') {
                    const today = new Date().toDateString();
                    filtered = filtered.filter(item => 
                        new Date(item.timestamp).toDateString() === today
                    );
                } else {
                    filtered = filtered.filter(item => item.status === this.historyFilter);
                }
            }
            
            // Apply search filter
            if (this.historySearch) {
                const search = this.historySearch.toLowerCase();
                filtered = filtered.filter(item => 
                    item.content.toLowerCase().includes(search) ||
                    (item.status && item.status.toLowerCase().includes(search))
                );
            }
            
            this.filteredHistory = filtered;
        },
        
        copyCommand(content) {
            navigator.clipboard.writeText(content).then(() => {
                // Optional: Show a toast notification
                console.log('Command copied to clipboard');
            });
        },
        
        addToHistory(content) {
            const historyItem = {
                id: Date.now(),
                content: content,
                timestamp: new Date(),
                status: 'success',
                duration: Math.random() * 5 + 's', // Mock duration
                tokens: Math.floor(Math.random() * 1000), // Mock tokens
                cost: (Math.random() * 0.5).toFixed(2) // Mock cost
            };
            this.commandHistory.unshift(historyItem);
            // Keep only last 100 items
            this.commandHistory = this.commandHistory.slice(0, 100);
            localStorage.setItem('cuti_command_history', JSON.stringify(this.commandHistory));
            
            // Update stats
            this.successCount = this.commandHistory.filter(item => item.status === 'success').length;
            const today = new Date().toDateString();
            this.todayCount = this.commandHistory.filter(item => 
                new Date(item.timestamp).toDateString() === today
            ).length;
            
            this.filterHistory();
        },
        
        clearHistory() {
            if (confirm('Are you sure you want to clear all command history?')) {
                this.commandHistory = [];
                this.filteredHistory = [];
                localStorage.removeItem('cuti_command_history');
            }
        },
        
        rerunCommand(content) {
            this.chatInput = content;
            this.activeTab = 'chat';
            this.$nextTick(() => {
                if (this.$refs.promptInput) {
                    this.$refs.promptInput.focus();
                }
            });
        },
        
        clearTerminal() {
            this.chatMessages = [];
        },
        
        // Settings methods
        loadSettings() {
            const saved = localStorage.getItem('cuti_settings');
            if (saved) {
                this.settings = { ...this.settings, ...JSON.parse(saved) };
            }
        },
        
        saveSettings() {
            localStorage.setItem('cuti_settings', JSON.stringify(this.settings));
            this.saveClaudeSettings(); // Also save Claude settings
            this.settingsSaved = true;
            // Show success for 3 seconds
            setTimeout(() => {
                this.settingsSaved = false;
            }, 3000);
        },
        
        // Claude settings methods
        async loadClaudeSettings() {
            try {
                const response = await fetch('/api/claude-settings/essential');
                if (response.ok) {
                    this.claudeSettings = await response.json();
                }
            } catch (error) {
                console.error('Error loading Claude settings:', error);
            }
        },
        
        async saveClaudeSettings() {
            try {
                const response = await fetch('/api/claude-settings/essential', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.claudeSettings)
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    console.error('Error saving Claude settings:', error);
                }
            } catch (error) {
                console.error('Error saving Claude settings:', error);
            }
        },
        
        exportSettings() {
            const settingsData = JSON.stringify(this.settings, null, 2);
            const blob = new Blob([settingsData], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `cuti-settings-${new Date().toISOString().split('T')[0]}.json`;
            a.click();
            URL.revokeObjectURL(url);
        },
        
        resetSettings() {
            if (confirm('Are you sure you want to reset all settings to defaults?')) {
                this.settings = {
                    claudeCommand: 'claude',
                    timeout: 3600,
                    checkInterval: 30,
                    maxRetries: 3,
                    concurrentTasks: 2,
                    showTimestamps: true,
                    enableSound: false,
                    autoScroll: true,
                    darkMode: true,
                    debugMode: false,
                    verboseLogging: false,
                    experimentalFeatures: false,
                    collectAnalytics: false,
                    storagePath: '~/.cuti/',
                    model: 'claude-3-opus'
                };
                this.saveSettings();
            }
        },
        
        async loadStats() {
            try {
                const response = await fetch('/api/queue/status');
                this.stats = await response.json();
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        },
        
        async loadPrompts() {
            try {
                const response = await fetch('/api/queue/prompts');
                this.prompts = await response.json();
            } catch (error) {
                console.error('Error loading prompts:', error);
            }
        },
        
        async loadAliases() {
            try {
                const response = await fetch('/api/aliases');
                this.aliases = await response.json();
            } catch (error) {
                console.error('Error loading aliases:', error);
            }
        },
        
        async loadHistory() {
            try {
                const response = await fetch('/api/history?limit=20');
                this.historyEntries = await response.json();
            } catch (error) {
                console.error('Error loading history:', error);
            }
        },
        
        async loadSystemStatus() {
            try {
                const response = await fetch('/api/monitoring/system');
                this.systemStatus = await response.json();
            } catch (error) {
                console.error('Error loading system status:', error);
            }
        },
        
        async addPrompt() {
            try {
                const response = await fetch('/api/queue/prompts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.newPrompt)
                });
                
                if (response.ok) {
                    this.showAddPromptModal = false;
                    this.newPrompt = { content: '', priority: 0, working_directory: '.', max_retries: 3 };
                    await this.loadPrompts();
                }
            } catch (error) {
                console.error('Error adding prompt:', error);
            }
        },
        
        async cancelPrompt(promptId) {
            try {
                const response = await fetch(`/api/queue/prompts/${promptId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    await this.loadPrompts();
                }
            } catch (error) {
                console.error('Error canceling prompt:', error);
            }
        },
        
        getStatusColor(status) {
            const colors = {
                'queued': 'bg-yellow-100 text-yellow-800',
                'executing': 'bg-blue-100 text-blue-800',
                'completed': 'bg-green-100 text-green-800',
                'failed': 'bg-red-100 text-red-800',
                'cancelled': 'bg-gray-100 text-gray-800',
                'rate_limited': 'bg-orange-100 text-orange-800'
            };
            return colors[status] || 'bg-gray-100 text-gray-800';
        },
        
        getStatusIcon(status) {
            const icons = {
                'queued': 'fas fa-clock',
                'executing': 'fas fa-play',
                'completed': 'fas fa-check',
                'failed': 'fas fa-times',
                'cancelled': 'fas fa-ban',
                'rate_limited': 'fas fa-exclamation-triangle'
            };
            return icons[status] || 'fas fa-question';
        },
        
        connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'status_update') {
                    this.loadStats();
                    this.loadPrompts();
                }
            };
            
            ws.onclose = () => {
                // Reconnect after 5 seconds
                setTimeout(() => this.connectWebSocket(), 5000);
            };
        }
    }
}

// Agent Status Page Functions
function initAgentStatus() {
    // Track start time for uptime calculation
    window.startTime = new Date();
    
    // Fetch and display real data
    async function fetchData() {
        try {
            // Update uptime
            const uptimeEl = document.getElementById('uptime');
            if (uptimeEl) {
                uptimeEl.textContent = window.cutiUtils.formatUptime();
            }
            
            // Fetch queue status
            const queueRes = await fetch('/api/queue/status');
            if (queueRes.ok) {
                const queueData = await queueRes.json();
                const queueCountEl = document.getElementById('queueCount');
                if (queueCountEl) {
                    queueCountEl.textContent = `${queueData.queued || 0}`;
                }
                
                const total = queueData.total_prompts || 0;
                const completed = queueData.completed || 0;
                const successRate = total > 0 ? Math.round((completed / total) * 100) : 0;
                const successRateEl = document.getElementById('successRate');
                if (successRateEl) {
                    successRateEl.textContent = `${successRate}%`;
                }
            }
            
            // Fetch agents
            const agentsRes = await fetch('/api/agents');
            if (agentsRes.ok) {
                const agents = await agentsRes.json();
                displayAgents(agents);
                
                const activeCount = agents.filter(a => a.status === 'available' || a.status === 'busy').length;
                const activeAgentsEl = document.getElementById('activeAgents');
                if (activeAgentsEl) {
                    activeAgentsEl.textContent = activeCount;
                }
            }
            
            // Fetch token usage
            const tokenRes = await fetch('/api/monitoring/tokens');
            if (tokenRes.ok) {
                const tokenData = await tokenRes.json();
                displayTokenUsage(tokenData);
            }
        } catch (error) {
            console.error('Error fetching data:', error);
        }
    }
    
    function displayAgents(agents) {
        const grid = document.getElementById('agentsGrid');
        
        if (!agents || agents.length === 0) {
            grid.innerHTML = '<div class="loading">No agents available</div>';
            return;
        }
        
        grid.innerHTML = agents.map(agent => `
            <div class="agent-card">
                <div class="agent-header">
                    <div class="agent-name">${agent.name}</div>
                    <div class="agent-status status-${agent.status}">${agent.status}</div>
                </div>
                <div class="agent-details">
                    <div class="detail-row">
                        <span class="detail-label">Type:</span>
                        <span class="detail-value">${agent.type}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Load:</span>
                        <span class="detail-value">${Math.round((agent.current_load || 0) * 100)}%</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Capabilities:</span>
                        <span class="detail-value">${agent.capabilities || 0}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    function displayTokenUsage(data) {
        if (!data || !data.current_stats) return;
        
        const stats = data.current_stats;
        
        const todayTokensEl = document.getElementById('todayTokens');
        if (todayTokensEl) {
            todayTokensEl.textContent = (stats.tokens_today || 0).toLocaleString();
        }
        
        const todayCostEl = document.getElementById('todayCost');
        if (todayCostEl) {
            todayCostEl.textContent = `$${(stats.cost_today || 0).toFixed(4)}`;
        }
        
        const totalRequestsEl = document.getElementById('totalRequests');
        if (totalRequestsEl) {
            totalRequestsEl.textContent = (stats.total_requests || 0).toLocaleString();
        }
        
        const avgTokensEl = document.getElementById('avgTokens');
        if (avgTokensEl) {
            const avgTokens = stats.total_requests > 0 ? Math.round(stats.total_tokens / stats.total_requests) : 0;
            avgTokensEl.textContent = avgTokens.toLocaleString();
        }
    }
    
    // Initial load
    fetchData();
    
    // Refresh every 5 seconds
    setInterval(fetchData, 5000);
}

// Claude status checking function
function claudeStatus() {
    return {
        claude: {
            installed: false,
            authorized: false,
            version: null,
            subscription_plan: null,
            error: null
        },
        showDetails: false,
        statusText: 'Checking...',
        statusClass: 'pending',
        statusDetails: false,
        
        async checkStatus() {
            try {
                const response = await fetch('/api/claude-status');
                const data = await response.json();
                
                this.claude = data;
                
                // Update status display
                if (!data.installed) {
                    this.statusText = 'Claude Not Installed';
                    this.statusClass = 'error';
                } else if (!data.authorized) {
                    this.statusText = 'Claude Not Authorized';
                    this.statusClass = 'warning';
                } else {
                    this.statusText = 'Claude Ready';
                    this.statusClass = 'active';
                }
                
                this.statusDetails = true;
            } catch (error) {
                console.error('Failed to check Claude status:', error);
                this.statusText = 'Status Unknown';
                this.statusClass = 'error';
                this.claude.error = error.message;
            }
            
            // Recheck every 30 seconds
            setTimeout(() => this.checkStatus(), 30000);
        }
    };
}

// Export functions for global use
window.terminalInterface = terminalInterface;
window.dashboard = dashboard;
window.claudeStatus = claudeStatus;
window.initAgentStatus = initAgentStatus;