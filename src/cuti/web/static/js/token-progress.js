/**
 * Real-time token progress display for Claude chat interface
 */

class TokenProgressDisplay {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.inputTokens = 0;
        this.outputTokens = 0;
        this.totalTokens = 0;
        this.tokenRate = 0;
        this.totalCost = 0;
        this.sessionTotalCost = 0;
        
        this.initializeDisplay();
    }
    
    initializeDisplay() {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="token-progress-container">
                <!-- Main Progress Bar -->
                <div class="token-main-progress">
                    <div class="token-progress-header">
                        <div class="token-title">
                            <span class="token-icon">🎯</span>
                            <span>Token Usage</span>
                        </div>
                        <div class="token-stats">
                            <span class="token-rate">
                                <span id="token-rate">0</span> tokens/sec
                            </span>
                        </div>
                    </div>
                    
                    <!-- Input/Output Token Bars -->
                    <div class="token-bars">
                        <div class="token-bar-group">
                            <div class="token-bar-label">
                                <span>Input</span>
                                <span id="input-tokens">0</span>
                            </div>
                            <div class="token-bar-container">
                                <div class="token-bar token-bar-input" id="input-bar"></div>
                            </div>
                        </div>
                        
                        <div class="token-bar-group">
                            <div class="token-bar-label">
                                <span>Output</span>
                                <span id="output-tokens">0</span>
                            </div>
                            <div class="token-bar-container">
                                <div class="token-bar token-bar-output" id="output-bar">
                                    <div class="token-bar-animation"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Cost Display -->
                    <div class="token-cost">
                        <div class="token-cost-item">
                            <span class="cost-label">Current:</span>
                            <span class="cost-value" id="current-cost">$0.0000</span>
                        </div>
                        <div class="token-cost-item">
                            <span class="cost-label">Session:</span>
                            <span class="cost-value" id="session-cost">$0.0000</span>
                        </div>
                    </div>
                </div>
                
                <!-- Detailed Metrics (collapsible) -->
                <div class="token-details" id="token-details">
                    <div class="token-detail-row">
                        <span>Total Tokens:</span>
                        <span id="total-tokens">0</span>
                    </div>
                    <div class="token-detail-row">
                        <span>Elapsed Time:</span>
                        <span id="elapsed-time">0s</span>
                    </div>
                    <div class="token-detail-row">
                        <span>Avg Token/Sec:</span>
                        <span id="avg-rate">0</span>
                    </div>
                </div>
            </div>
        `;
        
        this.addStyles();
    }
    
    addStyles() {
        if (document.getElementById('token-progress-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'token-progress-styles';
        style.textContent = `
            .token-progress-container {
                background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
                border: 1px solid #3a3a4e;
                border-radius: 12px;
                padding: 16px;
                margin: 16px 0;
                font-family: 'Inter', -apple-system, sans-serif;
                animation: slideIn 0.3s ease-out;
            }
            
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateY(-10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .token-progress-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }
            
            .token-title {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 14px;
                font-weight: 600;
                color: #ffffff;
            }
            
            .token-icon {
                font-size: 18px;
            }
            
            .token-stats {
                display: flex;
                gap: 16px;
                font-size: 13px;
                color: #a0a0b0;
            }
            
            .token-rate {
                display: flex;
                align-items: center;
                gap: 4px;
                padding: 4px 8px;
                background: rgba(79, 209, 197, 0.1);
                border: 1px solid rgba(79, 209, 197, 0.3);
                border-radius: 6px;
                color: #4fd1c5;
                font-weight: 500;
            }
            
            .token-bars {
                display: flex;
                flex-direction: column;
                gap: 12px;
                margin-bottom: 12px;
            }
            
            .token-bar-group {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            
            .token-bar-label {
                display: flex;
                justify-content: space-between;
                font-size: 12px;
                color: #a0a0b0;
            }
            
            .token-bar-label span:last-child {
                font-weight: 600;
                color: #ffffff;
            }
            
            .token-bar-container {
                height: 24px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                overflow: hidden;
                position: relative;
            }
            
            .token-bar {
                height: 100%;
                border-radius: 12px;
                transition: width 0.3s ease-out;
                position: relative;
                overflow: hidden;
            }
            
            .token-bar-input {
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                width: 0%;
            }
            
            .token-bar-output {
                background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%);
                width: 0%;
            }
            
            .token-bar-animation {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(
                    90deg,
                    transparent 0%,
                    rgba(255, 255, 255, 0.2) 50%,
                    transparent 100%
                );
                animation: shimmer 2s infinite;
            }
            
            @keyframes shimmer {
                0% {
                    transform: translateX(-100%);
                }
                100% {
                    transform: translateX(100%);
                }
            }
            
            .token-cost {
                display: flex;
                justify-content: space-around;
                padding: 12px;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 8px;
                margin-top: 12px;
            }
            
            .token-cost-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 4px;
            }
            
            .cost-label {
                font-size: 11px;
                color: #808090;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .cost-value {
                font-size: 16px;
                font-weight: 600;
                color: #4fd1c5;
                font-family: 'Monaco', 'Courier New', monospace;
            }
            
            .token-details {
                margin-top: 12px;
                padding-top: 12px;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                display: none;
            }
            
            .token-details.show {
                display: block;
            }
            
            .token-detail-row {
                display: flex;
                justify-content: space-between;
                padding: 4px 0;
                font-size: 12px;
                color: #a0a0b0;
            }
            
            .token-detail-row span:last-child {
                color: #ffffff;
                font-weight: 500;
            }
            
            /* Pulsing animation when updating */
            .token-updating {
                animation: pulse 0.5s ease-out;
            }
            
            @keyframes pulse {
                0% {
                    transform: scale(1);
                }
                50% {
                    transform: scale(1.02);
                }
                100% {
                    transform: scale(1);
                }
            }
        `;
        
        document.head.appendChild(style);
    }
    
    updateTokens(data) {
        // Update token counts
        if (data.input_tokens !== undefined) {
            this.inputTokens = data.input_tokens;
            document.getElementById('input-tokens').textContent = this.formatNumber(this.inputTokens);
            this.updateBar('input-bar', this.inputTokens, 10000); // Scale to 10k tokens
        }
        
        if (data.output_tokens !== undefined) {
            this.outputTokens = data.output_tokens;
            document.getElementById('output-tokens').textContent = this.formatNumber(this.outputTokens);
            this.updateBar('output-bar', this.outputTokens, 10000);
            
            // Add pulsing animation
            const outputBar = document.getElementById('output-bar');
            outputBar.classList.add('token-updating');
            setTimeout(() => outputBar.classList.remove('token-updating'), 500);
        }
        
        if (data.total_tokens !== undefined) {
            this.totalTokens = data.total_tokens;
            document.getElementById('total-tokens').textContent = this.formatNumber(this.totalTokens);
        }
        
        // Update rate
        if (data.token_rate !== undefined) {
            this.tokenRate = data.token_rate;
            document.getElementById('token-rate').textContent = this.tokenRate;
            document.getElementById('avg-rate').textContent = this.tokenRate;
        }
        
        // Update costs
        if (data.total_cost !== undefined) {
            this.totalCost = data.total_cost;
            document.getElementById('current-cost').textContent = data.total_cost;
        }
        
        // Update elapsed time
        if (data.elapsed_seconds !== undefined) {
            document.getElementById('elapsed-time').textContent = this.formatTime(data.elapsed_seconds);
        }
    }
    
    updateSessionTotals(data) {
        if (data.total_cost !== undefined) {
            this.sessionTotalCost = data.total_cost;
            document.getElementById('session-cost').textContent = data.total_cost;
        }
    }
    
    updateBar(barId, value, maxValue) {
        const bar = document.getElementById(barId);
        if (bar) {
            const percentage = Math.min((value / maxValue) * 100, 100);
            bar.style.width = `${percentage}%`;
        }
    }
    
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }
    
    formatTime(seconds) {
        if (seconds < 60) {
            return `${Math.round(seconds)}s`;
        }
        const minutes = Math.floor(seconds / 60);
        const secs = Math.round(seconds % 60);
        return `${minutes}m ${secs}s`;
    }
    
    reset() {
        this.inputTokens = 0;
        this.outputTokens = 0;
        this.totalTokens = 0;
        this.tokenRate = 0;
        this.totalCost = 0;
        
        document.getElementById('input-tokens').textContent = '0';
        document.getElementById('output-tokens').textContent = '0';
        document.getElementById('total-tokens').textContent = '0';
        document.getElementById('token-rate').textContent = '0';
        document.getElementById('current-cost').textContent = '$0.0000';
        document.getElementById('elapsed-time').textContent = '0s';
        document.getElementById('avg-rate').textContent = '0';
        
        this.updateBar('input-bar', 0, 100);
        this.updateBar('output-bar', 0, 100);
    }
    
    showDetails() {
        const details = document.getElementById('token-details');
        if (details) {
            details.classList.toggle('show');
        }
    }
}

// Export for use in other modules
window.TokenProgressDisplay = TokenProgressDisplay;