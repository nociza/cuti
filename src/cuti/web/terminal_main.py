"""
Terminal-style web interface for Claude Code streaming.
"""

def get_terminal_template(working_directory: str) -> str:
    """Get the terminal-style HTML template."""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>cuti - AI Terminal Interface</title>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:ital,wght@0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {{
            --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            --dark-gradient: linear-gradient(135deg, #1a1c20 0%, #2d3436 100%);
            --glass-bg: rgba(255, 255, 255, 0.05);
            --glass-border: rgba(255, 255, 255, 0.1);
            --text-primary: #1f2937;
            --text-secondary: #6b7280;
            --text-muted: #9ca3af;
            --terminal-bg: #0a0f14;
            --terminal-green: #10b981;
            --terminal-blue: #3b82f6;
            --terminal-yellow: #f59e0b;
            --terminal-red: #ef4444;
        }}
        
        /* Custom Scrollbar */
        *::-webkit-scrollbar {{
            width: 10px;
            height: 10px;
        }}
        
        *::-webkit-scrollbar-track {{
            background: rgba(0, 0, 0, 0.1);
            border-radius: 10px;
        }}
        
        *::-webkit-scrollbar-thumb {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
        }}
        
        *::-webkit-scrollbar-thumb:hover {{
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            color: var(--text-primary);
            position: relative;
            overflow: hidden;
        }}
        
        /* Animated Background */
        body::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 80%, rgba(102, 126, 234, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(118, 75, 162, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(240, 147, 251, 0.2) 0%, transparent 50%);
            animation: backgroundShift 20s ease infinite;
            pointer-events: none;
        }}
        
        @keyframes backgroundShift {{
            0%, 100% {{ transform: translate(0, 0) rotate(0deg); }}
            33% {{ transform: translate(-20px, -20px) rotate(120deg); }}
            66% {{ transform: translate(20px, -10px) rotate(240deg); }}
        }}
        
        /* Main Layout */
        .main-container {{
            display: flex;
            height: 100vh;
            position: relative;
        }}
        
        /* Modern Header */
        .header {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 72px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            z-index: 100;
            display: flex;
            align-items: center;
            padding: 0 32px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        }}
        
        .header-content {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
        }}
        
        .logo-section {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        
        .logo {{
            width: 42px;
            height: 42px;
            background: var(--primary-gradient);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: white;
            font-size: 18px;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}
        
        .app-title {{
            font-size: 24px;
            font-weight: 700;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .app-subtitle {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 2px;
        }}
        
        /* Navigation Pills */
        .nav-pills {{
            display: flex;
            gap: 8px;
            background: rgba(0, 0, 0, 0.05);
            padding: 6px;
            border-radius: 16px;
        }}
        
        .nav-pill {{
            padding: 10px 20px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 500;
            color: var(--text-secondary);
            background: transparent;
            border: none;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
        }}
        
        .nav-pill:hover {{
            color: var(--text-primary);
            background: rgba(255, 255, 255, 0.5);
        }}
        
        .nav-pill.active {{
            color: white;
            background: var(--primary-gradient);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}
        
        /* Content Area */
        .content-wrapper {{
            display: flex;
            flex: 1;
            margin-top: 72px;
            height: calc(100vh - 72px - 32px); /* Account for header (72px) and status bar (32px) */
        }}
        
        /* Main Content */
        .main-content {{
            flex: 1;
            display: flex;
            flex-direction: column;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            margin: 24px;
            margin-right: 12px;
            margin-bottom: 0; /* Remove bottom margin to prevent overlap */
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        
        /* Terminal Area (Chat Only) */
        .terminal-container {{
            flex: 1;
            background: var(--terminal-bg);
            border-radius: 16px;
            margin: 20px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: inset 0 2px 20px rgba(0, 0, 0, 0.3);
            position: relative;
        }}
        
        .terminal-header {{
            background: linear-gradient(180deg, #141e26 0%, #0a0f14 100%);
            padding: 12px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        .terminal-controls {{
            display: flex;
            gap: 8px;
        }}
        
        .terminal-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            transition: all 0.3s ease;
        }}
        
        .terminal-dot.red {{ background: #ff5f57; }}
        .terminal-dot.yellow {{ background: #ffbd2e; }}
        .terminal-dot.green {{ background: #28ca42; }}
        
        .terminal-dot:hover {{
            transform: scale(1.1);
        }}
        
        .terminal-title {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: rgba(255, 255, 255, 0.5);
            letter-spacing: 0.5px;
        }}
        
        .terminal-output {{
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            line-height: 1.8;
            min-height: 0; /* Allow proper flexbox scrolling */
        }}
        
        /* Terminal Message Styles */
        .terminal-message {{
            margin-bottom: 16px;
            animation: terminalFadeIn 0.3s ease;
        }}
        
        @keyframes terminalFadeIn {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .user-input {{
            color: var(--terminal-blue);
            display: flex;
            align-items: baseline;
            gap: 8px;
        }}
        
        .assistant-output {{
            color: var(--terminal-green);
            margin-left: 20px;
        }}
        
        .system-message {{
            color: var(--terminal-yellow);
            font-style: italic;
        }}
        
        .error-message {{
            color: var(--terminal-red);
            font-weight: 500;
        }}
        
        .timestamp {{
            color: rgba(255, 255, 255, 0.3);
            font-size: 11px;
            margin-right: 8px;
        }}
        
        .terminal-prompt {{
            color: var(--terminal-blue);
            font-weight: 600;
        }}
        
        .streaming-cursor::after {{
            content: '▊';
            color: var(--terminal-green);
            animation: blink 1s infinite;
        }}
        
        @keyframes blink {{
            0%, 50% {{ opacity: 1; }}
            51%, 100% {{ opacity: 0; }}
        }}
        
        /* Modern Input Area */
        .input-container {{
            background: linear-gradient(180deg, #0a0f14 0%, #141e26 100%);
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding: 20px;
        }}
        
        .input-wrapper {{
            display: flex;
            align-items: center;
            gap: 12px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 12px 16px;
            transition: all 0.3s ease;
        }}
        
        .input-wrapper:focus-within {{
            background: rgba(255, 255, 255, 0.05);
            border-color: var(--terminal-blue);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }}
        
        .prompt-symbol {{
            color: var(--terminal-blue);
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
        }}
        
        .prompt-input {{
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: white;
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            caret-color: var(--terminal-blue);
        }}
        
        .prompt-input::placeholder {{
            color: rgba(255, 255, 255, 0.3);
        }}
        
        .processing-indicator {{
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--terminal-yellow);
            font-size: 12px;
        }}
        
        .processing-dot {{
            width: 6px;
            height: 6px;
            background: var(--terminal-yellow);
            border-radius: 50%;
            animation: processingPulse 1.5s ease infinite;
        }}
        
        .processing-dot:nth-child(2) {{ animation-delay: 0.2s; }}
        .processing-dot:nth-child(3) {{ animation-delay: 0.4s; }}
        
        @keyframes processingPulse {{
            0%, 60%, 100% {{ transform: scale(1); opacity: 1; }}
            30% {{ transform: scale(1.5); opacity: 0.7; }}
        }}
        
        /* Sidebar */
        .sidebar {{
            width: 360px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            margin: 24px 24px 0 12px; /* Remove bottom margin */
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
            display: flex;
            flex-direction: column;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            overflow: hidden;
        }}
        
        .sidebar.collapsed {{
            width: 0;
            margin-right: 0;
            opacity: 0;
            pointer-events: none;
        }}
        
        .sidebar-header {{
            padding: 24px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.05);
        }}
        
        .sidebar-title {{
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 8px;
        }}
        
        .sidebar-subtitle {{
            font-size: 14px;
            color: var(--text-muted);
        }}
        
        .sidebar-stats {{
            display: flex;
            gap: 16px;
            margin-top: 16px;
        }}
        
        .stat-item {{
            flex: 1;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 24px;
            font-weight: 700;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .stat-label {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 4px;
        }}
        
        .sidebar-content {{
            flex: 1;
            overflow-y: auto;
            padding: 24px;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 48px 24px;
            color: var(--text-muted);
        }}
        
        .empty-icon {{
            width: 64px;
            height: 64px;
            margin: 0 auto 16px;
            background: rgba(0, 0, 0, 0.05);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }}
        
        /* Todo Items */
        .todo-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        
        .todo-item {{
            background: white;
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 12px;
            padding: 16px;
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        
        .todo-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
            border-color: rgba(102, 126, 234, 0.3);
        }}
        
        .todo-item.completed {{
            opacity: 0.6;
            background: rgba(0, 0, 0, 0.02);
        }}
        
        .todo-item.completed .todo-text {{
            text-decoration: line-through;
            color: var(--text-muted);
        }}
        
        .todo-content {{
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }}
        
        .todo-checkbox {{
            width: 20px;
            height: 20px;
            border: 2px solid rgba(102, 126, 234, 0.3);
            border-radius: 6px;
            background: white;
            cursor: pointer;
            transition: all 0.3s ease;
            flex-shrink: 0;
            margin-top: 2px;
            position: relative;
        }}
        
        .todo-checkbox:checked {{
            background: var(--primary-gradient);
            border-color: transparent;
        }}
        
        .todo-checkbox:checked::after {{
            content: '✓';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .todo-details {{
            flex: 1;
        }}
        
        .todo-text {{
            font-size: 14px;
            color: var(--text-primary);
            line-height: 1.5;
            margin-bottom: 6px;
        }}
        
        .todo-meta {{
            font-size: 11px;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        /* Toggle Button */
        .sidebar-toggle {{
            position: fixed;
            right: 24px;
            bottom: 24px;
            width: 56px;
            height: 56px;
            background: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
            cursor: pointer;
            transition: all 0.3s ease;
            z-index: 50;
        }}
        
        .sidebar-toggle:hover {{
            transform: scale(1.1);
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.2);
        }}
        
        .sidebar-toggle-icon {{
            font-size: 24px;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        /* Status Bar */
        .status-bar {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 32px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-top: 1px solid rgba(0, 0, 0, 0.05);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
            font-size: 11px;
            color: var(--text-muted);
            z-index: 90;
        }}
        
        .status-section {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        
        .status-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .status-indicator {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s ease infinite;
        }}
        
        .status-indicator.ready {{
            background: var(--terminal-green);
        }}
        
        .status-indicator.streaming {{
            background: var(--terminal-yellow);
            animation: pulse 1s ease infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        /* Responsive Design */
        @media (max-width: 768px) {{
            .sidebar {{
                position: fixed;
                right: 0;
                top: 72px;
                bottom: 32px;
                margin: 0;
                border-radius: 24px 0 0 24px;
                z-index: 80;
            }}
            
            .main-content {{
                margin-right: 24px;
            }}
            
            .nav-pills {{
                display: none;
            }}
        }}
    </style>
</head>
<body x-data="terminalInterface()">
    <!-- Modern Header -->
    <header class="header">
        <div class="header-content">
            <div class="logo-section">
                <div class="logo">AI</div>
                <div>
                    <div class="app-title">cuti</div>
                    <div class="app-subtitle">AI Terminal Interface</div>
                </div>
            </div>
            
            <!-- Navigation Pills -->
            <nav class="nav-pills">
                <button @click="activeTab = 'chat'" 
                        :class="activeTab === 'chat' ? 'active' : ''"
                        class="nav-pill">
                    Chat
                </button>
                <button @click="activeTab = 'history'" 
                        :class="activeTab === 'history' ? 'active' : ''"
                        class="nav-pill">
                    History
                </button>
                <button @click="activeTab = 'settings'" 
                        :class="activeTab === 'settings' ? 'active' : ''"
                        class="nav-pill">
                    Settings
                </button>
            </nav>
            
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 12px; color: var(--text-muted);">{working_directory}</span>
            </div>
        </div>
    </header>

    <!-- Main Container -->
    <div class="content-wrapper">
        <!-- Main Content Area -->
        <main class="main-content">
            <!-- Terminal Container -->
            <div class="terminal-container" x-show="activeTab === 'chat'">
                <!-- Terminal Header -->
                <div class="terminal-header">
                    <div class="terminal-controls">
                        <div class="terminal-dot red"></div>
                        <div class="terminal-dot yellow"></div>
                        <div class="terminal-dot green"></div>
                    </div>
                    <div class="terminal-title">claude-terminal@{working_directory}</div>
                    <div style="width: 60px;"></div>
                </div>
                
                <!-- Terminal Output -->
                <div id="terminalOutput" class="terminal-output">
                    <!-- Welcome Message -->
                    <div class="system-message" x-show="chatMessages.length === 0 && !isStreaming">
                        <div class="timestamp">System</div>
                        <div>Welcome to cuti v0.2.0 - Claude Code Terminal Interface</div>
                        <div>Type your message below to start chatting with Claude...</div>
                        <div>&nbsp;</div>
                    </div>
                    
                    <!-- Chat Messages -->
                    <template x-for="message in chatMessages" :key="message.id">
                        <div class="terminal-message">
                            <!-- User Input -->
                            <div x-show="message.role === 'user'" class="user-input">
                                <span class="timestamp" x-text="formatTime(message.timestamp)"></span>
                                <span class="terminal-prompt">$</span>
                                <span x-text="message.content"></span>
                            </div>
                            
                            <!-- Assistant Output -->
                            <div x-show="message.role === 'assistant'" class="assistant-output" 
                                 x-html="formatTerminalMessage(message.content)"></div>
                            
                            <!-- System Messages -->
                            <div x-show="message.role === 'system'" class="system-message">
                                <span class="timestamp" x-text="formatTime(message.timestamp)"></span>
                                <span>[SYSTEM]</span> <span x-text="message.content"></span>
                            </div>
                            
                            <!-- Error Messages -->
                            <div x-show="message.role === 'error'" class="error-message">
                                <span class="timestamp" x-text="formatTime(message.timestamp)"></span>
                                <span>[ERROR]</span> <span x-text="message.content"></span>
                            </div>
                        </div>
                    </template>
                    
                    <!-- Current Streaming Message -->
                    <div x-show="isStreaming && currentStreamingMessage" class="terminal-message">
                        <div class="assistant-output">
                            <span x-html="formatTerminalMessage(currentStreamingMessage.content)"></span>
                            <span class="streaming-cursor"></span>
                        </div>
                    </div>
                </div>
                
                <!-- Modern Input Area -->
                <div class="input-container">
                    <div class="input-wrapper">
                        <span class="prompt-symbol">$</span>
                        <input
                            x-model="chatInput"
                            @keydown.enter="sendChatMessage()"
                            @keydown.ctrl.c="clearTerminal()"
                            placeholder="Type your message here..."
                            class="prompt-input"
                            :disabled="isStreaming"
                            x-ref="promptInput">
                        <div x-show="isStreaming" class="processing-indicator">
                            <div class="processing-dot"></div>
                            <div class="processing-dot"></div>
                            <div class="processing-dot"></div>
                            <span>Processing</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- History Tab (placeholder) -->
            <div x-show="activeTab === 'history'" style="padding: 40px; text-align: center; color: var(--text-muted);">
                <h2 style="font-size: 24px; margin-bottom: 16px; color: var(--text-primary);">Command History</h2>
                <p>Your chat history will appear here</p>
            </div>
            
            <!-- Settings Tab (placeholder) -->
            <div x-show="activeTab === 'settings'" style="padding: 40px; text-align: center; color: var(--text-muted);">
                <h2 style="font-size: 24px; margin-bottom: 16px; color: var(--text-primary);">Settings</h2>
                <p>Configuration options will appear here</p>
            </div>
        </main>
        
        <!-- Modern Sidebar -->
        <aside class="sidebar" :class="showTodos ? '' : 'collapsed'">
            <div class="sidebar-header">
                <div class="sidebar-title">Task Tracker</div>
                <div class="sidebar-subtitle">AI-extracted tasks from conversation</div>
                
                <div class="sidebar-stats">
                    <div class="stat-item">
                        <div class="stat-value" x-text="todos.filter(t => !t.completed).length"></div>
                        <div class="stat-label">Pending</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" x-text="todos.filter(t => t.completed).length"></div>
                        <div class="stat-label">Completed</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" x-text="todos.length"></div>
                        <div class="stat-label">Total</div>
                    </div>
                </div>
            </div>
            
            <div class="sidebar-content">
                <div x-show="todos.length === 0" class="empty-state">
                    <div class="empty-icon">📝</div>
                    <div style="font-weight: 500; margin-bottom: 8px;">No tasks yet</div>
                    <div style="font-size: 14px;">Tasks will be automatically extracted from your conversation with Claude</div>
                </div>
                
                <div x-show="todos.length > 0" class="todo-list">
                    <template x-for="todo in todos" :key="todo.id">
                        <div class="todo-item" :class="todo.completed && 'completed'">
                            <div class="todo-content">
                                <input
                                    type="checkbox"
                                    :checked="todo.completed"
                                    @change="toggleTodo(todo.id)"
                                    class="todo-checkbox">
                                <div class="todo-details">
                                    <div class="todo-text" x-text="todo.text"></div>
                                    <div x-show="todo.timestamp" class="todo-meta">
                                        <span x-text="formatTime(todo.timestamp)"></span>
                                        <span>•</span>
                                        <span x-text="todo.completed ? 'Completed' : 'Active'"></span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </template>
                </div>
            </div>
        </aside>
    </div>
    
    <!-- Sidebar Toggle Button -->
    <button @click="showTodos = !showTodos" class="sidebar-toggle">
        <span class="sidebar-toggle-icon">📋</span>
    </button>
    
    <!-- Status Bar -->
    <div class="status-bar">
        <div class="status-section">
            <div class="status-item">
                <span>cuti v0.2.0</span>
            </div>
            <div class="status-item">
                <span x-text="chatMessages.length + ' messages'"></span>
            </div>
        </div>
        <div class="status-section">
            <div class="status-item">
                <div class="status-indicator" :class="isStreaming ? 'streaming' : 'ready'"></div>
                <span x-text="isStreaming ? 'Streaming' : 'Ready'"></span>
            </div>
            <div class="status-item">
                <span x-text="todos.filter(t => !t.completed).length + ' active tasks'"></span>
            </div>
        </div>
    </div>

    <script>
        function terminalInterface() {{
            return {{
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
                
                async init() {{
                    this.connectChatWebSocket();
                    this.$refs.promptInput.focus();
                }},
                
                connectChatWebSocket() {{
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    this.chatWs = new WebSocket(`${{protocol}}//${{window.location.host}}/chat-ws`);
                    
                    this.chatWs.onmessage = (event) => {{
                        const data = JSON.parse(event.data);
                        
                        if (data.type === 'start') {{
                            this.isStreaming = true;
                            this.currentStreamingMessage = {{
                                id: Date.now(),
                                role: 'assistant',
                                content: '',
                                timestamp: new Date()
                            }};
                        }} else if (data.type === 'stream' && this.currentStreamingMessage) {{
                            this.currentStreamingMessage.content += data.content;
                            this.extractTodosFromContent(data.content);
                            this.scrollToBottom();
                        }} else if (data.type === 'end') {{
                            if (this.currentStreamingMessage) {{
                                this.chatMessages.push(this.currentStreamingMessage);
                                this.currentStreamingMessage = null;
                                this.scrollToBottom();
                            }}
                            this.isStreaming = false;
                            this.$refs.promptInput.focus();
                        }} else if (data.type === 'error') {{
                            this.chatMessages.push({{
                                id: Date.now(),
                                role: 'error',
                                content: data.content,
                                timestamp: new Date()
                            }});
                            this.isStreaming = false;
                            this.$refs.promptInput.focus();
                        }}
                    }};
                    
                    this.chatWs.onclose = () => {{
                        setTimeout(() => this.connectChatWebSocket(), 3000);
                    }};
                }},
                
                sendChatMessage() {{
                    if (!this.chatInput.trim() || this.isStreaming || !this.chatWs) return;
                    
                    // Add user message
                    this.chatMessages.push({{
                        id: Date.now(),
                        role: 'user',
                        content: this.chatInput,
                        timestamp: new Date()
                    }});
                    
                    // Send to server
                    this.chatWs.send(JSON.stringify({{
                        type: 'message',
                        content: this.chatInput
                    }}));
                    
                    this.chatInput = '';
                    this.scrollToBottom();
                }},
                
                clearTerminal() {{
                    this.chatMessages = [];
                    this.todos = [];
                    this.chatInput = '';
                }},
                
                extractTodosFromContent(content) {{
                    // Only extract actual TODO items, not random lists
                    const todoPatterns = [
                        /TODO:\s*(.+)$/gim,
                        /\\[\\s*\\]\s*(.+)$/gm,
                        /TASK:\s*(.+)$/gim,
                        /FIX:\s*(.+)$/gim,
                        /FIXME:\s*(.+)$/gim
                    ];
                    
                    for (const pattern of todoPatterns) {{
                        const matches = content.matchAll(pattern);
                        for (const match of matches) {{
                            const todoText = match[1].trim();
                            if (todoText.length > 5 && !this.todos.find(t => t.text === todoText)) {{
                                this.todos.push({{
                                    id: this.nextTodoId++,
                                    text: todoText,
                                    completed: false,
                                    timestamp: new Date()
                                }});
                            }}
                        }}
                    }}
                }},
                
                toggleTodo(todoId) {{
                    const todo = this.todos.find(t => t.id === todoId);
                    if (todo) {{
                        todo.completed = !todo.completed;
                    }}
                }},
                
                formatTerminalMessage(content) {{
                    return content
                        .replace(/`([^`]+)`/g, '<span style="background: rgba(59, 130, 246, 0.2); padding: 2px 6px; border-radius: 4px; color: #60a5fa;">$1</span>')
                        .replace(/```([\\s\\S]*?)```/g, '<div style="background: rgba(16, 185, 129, 0.1); padding: 12px; margin: 8px 0; border-left: 3px solid #10b981; border-radius: 4px; font-family: JetBrains Mono, monospace;">$1</div>')
                        .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong style="color: #34d399;">$1</strong>')
                        .replace(/\\*([^*]+)\\*/g, '<em style="color: #fbbf24;">$1</em>')
                        .replace(/\\n/g, '<br>');
                }},
                
                formatTime(timestamp) {{
                    return new Date(timestamp).toLocaleTimeString('en-US', {{hour12: false}});
                }},
                
                getCurrentTime() {{
                    return new Date().toLocaleTimeString('en-US', {{hour12: false}});
                }},
                
                scrollToBottom() {{
                    this.$nextTick(() => {{
                        const output = document.getElementById('terminalOutput');
                        if (output) {{
                            output.scrollTop = output.scrollHeight;
                        }}
                    }});
                }}
            }}
        }}
    </script>
</body>
</html>
    """