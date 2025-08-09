"""
FastAPI web application for ccutils.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import asyncio
import psutil

from ..queue_manager import QueueManager
from ..models import QueuedPrompt, PromptStatus
from ..aliases import PromptAliasManager
from ..history import PromptHistoryManager
from ..task_expansion import TaskExpansionEngine
from .monitoring import SystemMonitor


class PromptRequest(BaseModel):
    content: str
    priority: int = 0
    working_directory: str = "."
    context_files: List[str] = []
    max_retries: int = 3
    estimated_tokens: Optional[int] = None


class AliasRequest(BaseModel):
    name: str
    content: str
    description: str = ""
    working_directory: str = "."
    context_files: List[str] = []


class TaskExpansionRequest(BaseModel):
    task_description: str
    context: Optional[Dict[str, Any]] = None


class WebSocketManager:
    """Manage WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass  # Connection might be closed


def create_app(storage_dir: str = "~/.claude-queue") -> FastAPI:
    """Create FastAPI application instance."""
    
    app = FastAPI(
        title="ccutils",
        description="Production-ready ccutils system with web interface",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize managers
    queue_manager = QueueManager(storage_dir=storage_dir)
    alias_manager = PromptAliasManager(storage_dir)
    history_manager = PromptHistoryManager(storage_dir)
    task_engine = TaskExpansionEngine(storage_dir)
    system_monitor = SystemMonitor()
    websocket_manager = WebSocketManager()
    
    # Static files and templates
    web_dir = Path(__file__).parent
    templates = Jinja2Templates(directory=str(web_dir / "templates"))
    
    try:
        app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")
    except RuntimeError:
        pass  # Directory might not exist, will create later
    
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        """Main dashboard page."""
        template_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ccutils</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100 min-h-screen" x-data="dashboard()">
    <!-- Navigation -->
    <nav class="bg-blue-600 text-white p-4 shadow-lg">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-2xl font-bold flex items-center">
                <i class="fas fa-robot mr-2"></i>
                ccutils
            </h1>
            <div class="flex space-x-4">
                <button @click="activeTab = 'dashboard'" 
                        :class="activeTab === 'dashboard' ? 'bg-blue-800' : 'bg-blue-500'"
                        class="px-4 py-2 rounded hover:bg-blue-700 transition">
                    <i class="fas fa-tachometer-alt mr-1"></i> Dashboard
                </button>
                <button @click="activeTab = 'queue'" 
                        :class="activeTab === 'queue' ? 'bg-blue-800' : 'bg-blue-500'"
                        class="px-4 py-2 rounded hover:bg-blue-700 transition">
                    <i class="fas fa-list mr-1"></i> Queue
                </button>
                <button @click="activeTab = 'aliases'" 
                        :class="activeTab === 'aliases' ? 'bg-blue-800' : 'bg-blue-500'"
                        class="px-4 py-2 rounded hover:bg-blue-700 transition">
                    <i class="fas fa-bookmark mr-1"></i> Aliases
                </button>
                <button @click="activeTab = 'history'" 
                        :class="activeTab === 'history' ? 'bg-blue-800' : 'bg-blue-500'"
                        class="px-4 py-2 rounded hover:bg-blue-700 transition">
                    <i class="fas fa-history mr-1"></i> History
                </button>
                <button @click="activeTab = 'monitoring'" 
                        :class="activeTab === 'monitoring' ? 'bg-blue-800' : 'bg-blue-500'"
                        class="px-4 py-2 rounded hover:bg-blue-700 transition">
                    <i class="fas fa-chart-line mr-1"></i> Monitoring
                </button>
            </div>
        </div>
    </nav>

    <div class="container mx-auto p-6">
        <!-- Dashboard Tab -->
        <div x-show="activeTab === 'dashboard'" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <!-- Stats Cards -->
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="flex-1">
                            <p class="text-sm text-gray-600">Total Prompts</p>
                            <p class="text-2xl font-semibold text-gray-900" x-text="stats.total_prompts || 0"></p>
                        </div>
                        <i class="fas fa-list-alt text-blue-500 text-2xl"></i>
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="flex-1">
                            <p class="text-sm text-gray-600">Completed</p>
                            <p class="text-2xl font-semibold text-green-600" x-text="stats.total_processed || 0"></p>
                        </div>
                        <i class="fas fa-check-circle text-green-500 text-2xl"></i>
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="flex-1">
                            <p class="text-sm text-gray-600">Failed</p>
                            <p class="text-2xl font-semibold text-red-600" x-text="stats.failed_count || 0"></p>
                        </div>
                        <i class="fas fa-times-circle text-red-500 text-2xl"></i>
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="flex-1">
                            <p class="text-sm text-gray-600">Success Rate</p>
                            <p class="text-2xl font-semibold text-blue-600" x-text="(stats.success_rate * 100).toFixed(1) + '%'"></p>
                        </div>
                        <i class="fas fa-percentage text-blue-500 text-2xl"></i>
                    </div>
                </div>
            </div>

            <!-- Quick Actions -->
            <div class="bg-white rounded-lg shadow p-6">
                <h2 class="text-xl font-semibold mb-4">Quick Actions</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <button @click="showAddPromptModal = true" 
                            class="flex items-center p-4 bg-blue-50 hover:bg-blue-100 rounded-lg transition">
                        <i class="fas fa-plus text-blue-600 mr-3"></i>
                        <span class="text-blue-800 font-medium">Add Prompt</span>
                    </button>
                    
                    <button @click="showTaskExpansionModal = true" 
                            class="flex items-center p-4 bg-green-50 hover:bg-green-100 rounded-lg transition">
                        <i class="fas fa-sitemap text-green-600 mr-3"></i>
                        <span class="text-green-800 font-medium">Expand Task</span>
                    </button>
                    
                    <button @click="toggleQueueProcessor()" 
                            class="flex items-center p-4 bg-yellow-50 hover:bg-yellow-100 rounded-lg transition">
                        <i :class="queueRunning ? 'fas fa-pause text-yellow-600' : 'fas fa-play text-yellow-600'" class="mr-3"></i>
                        <span class="text-yellow-800 font-medium" x-text="queueRunning ? 'Pause Queue' : 'Start Queue'"></span>
                    </button>
                </div>
            </div>

            <!-- System Status -->
            <div class="bg-white rounded-lg shadow p-6">
                <h2 class="text-xl font-semibold mb-4">System Status</h2>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="text-center p-4 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-semibold text-gray-900" x-text="systemStatus.cpu_percent + '%'"></div>
                        <div class="text-sm text-gray-600">CPU Usage</div>
                    </div>
                    <div class="text-center p-4 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-semibold text-gray-900" x-text="systemStatus.memory_percent + '%'"></div>
                        <div class="text-sm text-gray-600">Memory Usage</div>
                    </div>
                    <div class="text-center p-4 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-semibold text-gray-900" x-text="systemStatus.disk_percent + '%'"></div>
                        <div class="text-sm text-gray-600">Disk Usage</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Queue Tab -->
        <div x-show="activeTab === 'queue'">
            <div class="bg-white rounded-lg shadow">
                <div class="p-6 border-b">
                    <h2 class="text-xl font-semibold">Queue Management</h2>
                </div>
                <div class="p-6">
                    <div class="overflow-x-auto">
                        <table class="min-w-full table-auto">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Content</th>
                                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-gray-200">
                                <template x-for="prompt in prompts" :key="prompt.id">
                                    <tr class="hover:bg-gray-50">
                                        <td class="px-4 py-3 text-sm text-gray-900" x-text="prompt.id"></td>
                                        <td class="px-4 py-3">
                                            <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full" 
                                                  :class="getStatusColor(prompt.status)">
                                                <i :class="getStatusIcon(prompt.status)" class="mr-1"></i>
                                                <span x-text="prompt.status"></span>
                                            </span>
                                        </td>
                                        <td class="px-4 py-3 text-sm text-gray-900" x-text="prompt.priority"></td>
                                        <td class="px-4 py-3 text-sm text-gray-900">
                                            <span x-text="prompt.content.substring(0, 60) + (prompt.content.length > 60 ? '...' : '')"></span>
                                        </td>
                                        <td class="px-4 py-3 text-sm text-gray-900" x-text="new Date(prompt.created_at).toLocaleString()"></td>
                                        <td class="px-4 py-3 text-sm">
                                            <button @click="cancelPrompt(prompt.id)" 
                                                    class="text-red-600 hover:text-red-800 mr-2">
                                                <i class="fas fa-trash"></i>
                                            </button>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Aliases Tab -->
        <div x-show="activeTab === 'aliases'">
            <div class="bg-white rounded-lg shadow">
                <div class="p-6 border-b flex justify-between items-center">
                    <h2 class="text-xl font-semibold">Prompt Aliases</h2>
                    <button @click="showCreateAliasModal = true" 
                            class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition">
                        <i class="fas fa-plus mr-1"></i> Create Alias
                    </button>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        <template x-for="alias in aliases" :key="alias.name">
                            <div class="border rounded-lg p-4 hover:shadow-md transition">
                                <h3 class="font-semibold text-lg" x-text="alias.name"></h3>
                                <p class="text-gray-600 text-sm mb-2" x-text="alias.description"></p>
                                <p class="text-xs text-gray-500 mb-3">
                                    <span x-text="alias.content.substring(0, 100) + (alias.content.length > 100 ? '...' : '')"></span>
                                </p>
                                <div class="flex justify-between items-center">
                                    <span class="text-xs text-gray-500" x-text="alias.working_directory"></span>
                                    <div class="space-x-2">
                                        <button @click="useAlias(alias.name)" 
                                                class="text-blue-600 hover:text-blue-800 text-sm">
                                            <i class="fas fa-play"></i> Use
                                        </button>
                                        <button @click="deleteAlias(alias.name)" 
                                                class="text-red-600 hover:text-red-800 text-sm">
                                            <i class="fas fa-trash"></i> Delete
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </template>
                    </div>
                </div>
            </div>
        </div>

        <!-- History Tab -->
        <div x-show="activeTab === 'history'">
            <div class="bg-white rounded-lg shadow">
                <div class="p-6 border-b">
                    <h2 class="text-xl font-semibold">Prompt History</h2>
                </div>
                <div class="p-6">
                    <div class="mb-4">
                        <input type="text" x-model="historySearch" @input="searchHistory()" 
                               placeholder="Search history..." 
                               class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                    </div>
                    <div class="space-y-4">
                        <template x-for="entry in historyEntries" :key="entry.id">
                            <div class="border rounded-lg p-4 hover:bg-gray-50">
                                <div class="flex justify-between items-start mb-2">
                                    <span class="text-sm text-gray-500" x-text="new Date(entry.timestamp).toLocaleString()"></span>
                                    <div class="flex space-x-2">
                                        <span class="text-xs text-gray-500" x-text="entry.working_directory"></span>
                                        <span x-show="entry.success !== null" 
                                              :class="entry.success ? 'text-green-600' : 'text-red-600'" 
                                              class="text-xs">
                                            <i :class="entry.success ? 'fas fa-check' : 'fas fa-times'"></i>
                                        </span>
                                    </div>
                                </div>
                                <p class="text-gray-800" x-text="entry.content"></p>
                                <div x-show="entry.tags && entry.tags.length > 0" class="mt-2">
                                    <template x-for="tag in entry.tags" :key="tag">
                                        <span class="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full mr-1" 
                                              x-text="tag"></span>
                                    </template>
                                </div>
                            </div>
                        </template>
                    </div>
                </div>
            </div>
        </div>

        <!-- Monitoring Tab -->
        <div x-show="activeTab === 'monitoring'">
            <div class="space-y-6">
                <div class="bg-white rounded-lg shadow p-6">
                    <h2 class="text-xl font-semibold mb-4">Token Usage</h2>
                    <canvas id="tokenChart" width="400" height="200"></canvas>
                </div>
                
                <div class="bg-white rounded-lg shadow p-6">
                    <h2 class="text-xl font-semibold mb-4">Performance Metrics</h2>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <h3 class="font-medium mb-2">Average Execution Time</h3>
                            <div class="text-2xl font-semibold text-blue-600" x-text="performanceMetrics.avg_execution_time + 's'"></div>
                        </div>
                        <div>
                            <h3 class="font-medium mb-2">Queue Throughput</h3>
                            <div class="text-2xl font-semibold text-green-600" x-text="performanceMetrics.throughput + '/hr'"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Add Prompt Modal -->
    <div x-show="showAddPromptModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <h3 class="text-lg font-semibold mb-4">Add New Prompt</h3>
            <form @submit.prevent="addPrompt()">
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Prompt Content</label>
                        <textarea x-model="newPrompt.content" 
                                  class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" 
                                  rows="4" required></textarea>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                            <input type="number" x-model="newPrompt.priority" 
                                   class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Max Retries</label>
                            <input type="number" x-model="newPrompt.max_retries" 
                                   class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                        </div>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Working Directory</label>
                        <input type="text" x-model="newPrompt.working_directory" 
                               class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                    </div>
                </div>
                <div class="flex justify-end space-x-4 mt-6">
                    <button type="button" @click="showAddPromptModal = false" 
                            class="px-4 py-2 text-gray-600 border rounded hover:bg-gray-50">
                        Cancel
                    </button>
                    <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Add Prompt
                    </button>
                </div>
            </form>
        </div>
    </div>

    <script>
        function dashboard() {
            return {
                activeTab: 'dashboard',
                stats: {},
                prompts: [],
                aliases: [],
                historyEntries: [],
                systemStatus: {},
                performanceMetrics: {},
                queueRunning: false,
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
                    
                    // Set up WebSocket connection
                    this.connectWebSocket();
                    
                    // Refresh data periodically
                    setInterval(() => {
                        this.loadStats();
                        this.loadPrompts();
                        this.loadSystemStatus();
                    }, 5000);
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
    </script>
</body>
</html>
        """
        return HTMLResponse(content=template_content)
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket_manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            websocket_manager.disconnect(websocket)
    
    # Queue Management APIs
    @app.get("/api/queue/status")
    async def get_queue_status():
        """Get current queue status and statistics."""
        state = queue_manager.get_status()
        return state.get_stats()
    
    @app.get("/api/queue/prompts")
    async def get_prompts():
        """Get all prompts in the queue."""
        state = queue_manager.get_status()
        return [
            {
                "id": prompt.id,
                "content": prompt.content,
                "status": prompt.status.value,
                "priority": prompt.priority,
                "working_directory": prompt.working_directory,
                "context_files": prompt.context_files,
                "created_at": prompt.created_at.isoformat(),
                "retry_count": prompt.retry_count,
                "max_retries": prompt.max_retries,
                "estimated_tokens": prompt.estimated_tokens,
            }
            for prompt in state.prompts
        ]
    
    @app.post("/api/queue/prompts")
    async def add_prompt(request: PromptRequest):
        """Add a new prompt to the queue."""
        # Resolve alias if needed
        resolved_content = alias_manager.resolve_alias(request.content, request.working_directory)
        
        # Add to history
        history_manager.add_prompt_to_history(
            resolved_content,
            request.working_directory,
            request.context_files,
            request.estimated_tokens
        )
        
        # Create queued prompt
        queued_prompt = QueuedPrompt(
            content=resolved_content,
            working_directory=request.working_directory,
            priority=request.priority,
            context_files=request.context_files,
            max_retries=request.max_retries,
            estimated_tokens=request.estimated_tokens,
        )
        
        success = queue_manager.add_prompt(queued_prompt)
        if success:
            # Notify connected clients
            await websocket_manager.broadcast(json.dumps({
                "type": "status_update",
                "message": f"New prompt added: {queued_prompt.id}"
            }))
            return {"success": True, "prompt_id": queued_prompt.id}
        else:
            raise HTTPException(status_code=500, detail="Failed to add prompt")
    
    @app.delete("/api/queue/prompts/{prompt_id}")
    async def cancel_prompt(prompt_id: str):
        """Cancel a prompt."""
        success = queue_manager.remove_prompt(prompt_id)
        if success:
            await websocket_manager.broadcast(json.dumps({
                "type": "status_update",
                "message": f"Prompt cancelled: {prompt_id}"
            }))
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Alias Management APIs
    @app.get("/api/aliases")
    async def get_aliases():
        """Get all aliases."""
        return alias_manager.list_aliases()
    
    @app.post("/api/aliases")
    async def create_alias(request: AliasRequest):
        """Create a new alias."""
        success = alias_manager.create_alias(
            request.name,
            request.content,
            request.description,
            request.working_directory,
            request.context_files
        )
        if success:
            return {"success": True, "alias_name": request.name}
        else:
            raise HTTPException(status_code=400, detail="Alias already exists")
    
    @app.delete("/api/aliases/{alias_name}")
    async def delete_alias(alias_name: str):
        """Delete an alias."""
        success = alias_manager.delete_alias(alias_name)
        if success:
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="Alias not found")
    
    @app.get("/api/aliases/{alias_name}")
    async def get_alias(alias_name: str):
        """Get a specific alias."""
        alias = alias_manager.get_alias(alias_name)
        if alias:
            return alias
        else:
            raise HTTPException(status_code=404, detail="Alias not found")
    
    # History APIs
    @app.get("/api/history")
    async def get_history(limit: int = 50, offset: int = 0):
        """Get prompt history."""
        return history_manager.get_history(limit, offset)
    
    @app.get("/api/history/search")
    async def search_history(query: str, limit: int = 20):
        """Search prompt history."""
        return history_manager.search_history(query, limit)
    
    @app.get("/api/history/stats")
    async def get_history_stats():
        """Get history statistics."""
        return history_manager.get_history_stats()
    
    # Task Expansion APIs
    @app.post("/api/tasks/expand")
    async def expand_task(request: TaskExpansionRequest):
        """Expand a task into subtasks."""
        breakdown = task_engine.expand_task(request.task_description, request.context)
        
        # Convert to serializable format
        return {
            "original_task": breakdown.original_task,
            "overall_complexity": breakdown.overall_complexity.value,
            "estimated_total_hours": breakdown.estimated_total_hours,
            "execution_order": breakdown.execution_order,
            "parallel_groups": breakdown.parallel_groups,
            "risk_factors": breakdown.risk_factors,
            "success_metrics": breakdown.success_metrics,
            "subtasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "category": task.category.value,
                    "complexity": task.complexity.value,
                    "estimated_time_hours": task.estimated_time_hours,
                    "dependencies": task.dependencies,
                    "deliverables": task.deliverables,
                    "acceptance_criteria": task.acceptance_criteria,
                    "priority": task.priority,
                    "tags": task.tags
                }
                for task in breakdown.subtasks
            ]
        }
    
    # Monitoring APIs
    @app.get("/api/monitoring/system")
    async def get_system_status():
        """Get system monitoring data."""
        return system_monitor.get_system_metrics()
    
    @app.get("/api/monitoring/tokens")
    async def get_token_usage():
        """Get token usage statistics."""
        # This would be implemented based on your token tracking needs
        return {"daily_usage": [], "monthly_usage": [], "total_tokens": 0}
    
    @app.get("/api/monitoring/performance")
    async def get_performance_metrics():
        """Get performance metrics."""
        history_stats = history_manager.get_history_stats()
        return {
            "avg_execution_time": history_stats.get("avg_execution_time", 0),
            "throughput": history_stats.get("total_prompts", 0),  # Simplified
            "success_rate": history_stats.get("success_rate", 0),
            "error_rate": 1 - history_stats.get("success_rate", 1)
        }
    
    return app


def main():
    """Main entry point for the web application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ccutils Web Interface")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--storage-dir", default="~/.claude-queue", help="Storage directory")
    
    args = parser.parse_args()
    
    app = create_app(args.storage_dir)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()