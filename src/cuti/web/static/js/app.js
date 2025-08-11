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
        return content
            .replace(/`([^`]+)`/g, '<span style="background: rgba(96, 165, 250, 0.2); padding: 2px 6px; border-radius: 4px; color: #60a5fa;">$1</span>')
            .replace(/```([\\s\\S]*?)```/g, '<div style="background: rgba(16, 185, 129, 0.1); padding: 12px; margin: 8px 0; border-left: 3px solid #10b981; border-radius: 4px; font-family: JetBrains Mono, monospace;">$1</div>')
            .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong style="color: #10b981;">$1</strong>')
            .replace(/\\*([^*]+)\\*/g, '<em style="color: #f59e0b;">$1</em>')
            .replace(/\\n/g, '<br>');
    }
};

// Terminal Interface Component
function terminalInterface() {
    return {
        activeTab: 'chat',
        showTodos: true,
        
        // Chat functionality
        chatMessages: [],
        chatInput: '',
        isStreaming: false,
        chatWs: null,
        currentStreamingMessage: null,
        todos: [],
        nextTodoId: 1,
        
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
        
        async init() {
            this.connectChatWebSocket();
            this.loadHistory();
            this.loadSettings();
            // Focus input after Alpine initializes
            this.$nextTick(() => {
                if (this.$refs.promptInput) {
                    this.$refs.promptInput.focus();
                }
            });
        },
        
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
                    this.scrollToBottom();
                } else if (data.type === 'end') {
                    if (this.currentStreamingMessage) {
                        this.chatMessages.push(this.currentStreamingMessage);
                        this.currentStreamingMessage = null;
                        this.scrollToBottom();
                    }
                    this.isStreaming = false;
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
        
        clearTerminal() {
            this.chatMessages = [];
            this.todos = [];
            this.chatInput = '';
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
        
        formatTerminalMessage(content) {
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
            
            if (atIndex >= 0 && (atIndex === 0 || input[atIndex - 1] === ' ')) {
                const prefix = input.substring(atIndex + 1);
                if (prefix.length > 0) {
                    await this.fetchAgentSuggestions(prefix);
                } else {
                    await this.fetchAgentSuggestions('');
                }
            } else {
                this.closeSuggestions();
            }
        },
        
        async fetchAgentSuggestions(prefix) {
            try {
                const response = await fetch(`/api/claude-code-agents/suggestions/${prefix || '_all'}`);
                if (response.ok) {
                    this.agentSuggestions = await response.json();
                    this.showAgentSuggestions = this.agentSuggestions.length > 0;
                    this.selectedSuggestionIndex = 0;
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
        
        // History methods
        loadHistory() {
            // Load command history from localStorage
            const saved = localStorage.getItem('cuti_command_history');
            if (saved) {
                this.commandHistory = JSON.parse(saved);
            } else {
                this.commandHistory = [];
            }
            
            // Calculate stats
            this.successCount = this.commandHistory.filter(item => item.status === 'success').length;
            const today = new Date().toDateString();
            this.todayCount = this.commandHistory.filter(item => 
                new Date(item.timestamp).toDateString() === today
            ).length;
            
            this.filterHistory();
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
            this.settingsSaved = true;
            // Show success for 3 seconds
            setTimeout(() => {
                this.settingsSaved = false;
            }, 3000);
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
        loadHistory() {
            // Load command history from localStorage
            const saved = localStorage.getItem('cuti_command_history');
            if (saved) {
                this.commandHistory = JSON.parse(saved);
            } else {
                this.commandHistory = [];
            }
            
            // Calculate stats
            this.successCount = this.commandHistory.filter(item => item.status === 'success').length;
            const today = new Date().toDateString();
            this.todayCount = this.commandHistory.filter(item => 
                new Date(item.timestamp).toDateString() === today
            ).length;
            
            this.filterHistory();
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
            this.settingsSaved = true;
            // Show success for 3 seconds
            setTimeout(() => {
                this.settingsSaved = false;
            }, 3000);
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

// Export functions for global use
window.terminalInterface = terminalInterface;
window.dashboard = dashboard;
window.initAgentStatus = initAgentStatus;