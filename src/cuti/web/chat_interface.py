"""
Minimalist chat interface for Claude Code streaming.
"""

import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, AsyncGenerator
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn


def create_chat_app(working_directory: Optional[str] = None) -> FastAPI:
    """Create the chat interface FastAPI app."""
    
    app = FastAPI(title="cuti", version="0.2.0")
    
    # Set working directory
    if working_directory is None:
        working_directory = os.environ.get("CUTI_WORKING_DIR", os.getcwd())
    
    app.state.working_directory = working_directory
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/", response_class=HTMLResponse)
    async def index():
        """Minimalist chat interface."""
        return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>cuti</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #fff;
            color: #333;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        #header {
            padding: 10px 20px;
            border-bottom: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
        }
        #messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .message {
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }
        .message.user { flex-direction: row-reverse; }
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 12px;
            word-wrap: break-word;
            white-space: pre-wrap;
        }
        .message.user .message-content {
            background: #007AFF;
            color: white;
        }
        .message.assistant .message-content {
            background: #f0f0f0;
            color: #333;
        }
        .message.system .message-content {
            background: #fff3cd;
            color: #856404;
            font-size: 12px;
        }
        #input-container {
            padding: 20px;
            border-top: 1px solid #e0e0e0;
        }
        #input-wrapper {
            display: flex;
            gap: 10px;
            align-items: flex-end;
        }
        #input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid #e0e0e0;
            border-radius: 24px;
            outline: none;
            font-size: 16px;
            resize: none;
            min-height: 44px;
            max-height: 200px;
            line-height: 1.5;
        }
        #input:focus {
            border-color: #007AFF;
        }
        #send {
            background: #007AFF;
            color: white;
            border: none;
            border-radius: 50%;
            width: 44px;
            height: 44px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: opacity 0.2s;
        }
        #send:hover { opacity: 0.8; }
        #send:disabled { opacity: 0.5; cursor: not-allowed; }
        .streaming::after {
            content: '●●●';
            animation: dots 1.5s infinite;
            display: inline-block;
            width: 30px;
        }
        @keyframes dots {
            0%, 20% { content: '●'; }
            40% { content: '●●'; }
            60%, 100% { content: '●●●'; }
        }
        pre {
            background: #f5f5f5;
            padding: 12px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 8px 0;
        }
        code {
            background: #f5f5f5;
            padding: 2px 4px;
            border-radius: 4px;
            font-family: 'SF Mono', Consolas, monospace;
        }
    </style>
</head>
<body>
    <div id="header">""" + working_directory + """</div>
    <div id="messages"></div>
    <div id="input-container">
        <div id="input-wrapper">
            <textarea id="input" 
                      placeholder="Message Claude..." 
                      rows="1"
                      onkeydown="handleKeyDown(event)"
                      oninput="autoResize(this)"></textarea>
            <button id="send" onclick="sendMessage()">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 2L11 13M22 2L15 22L11 13L2 9L22 2Z"/>
                </svg>
            </button>
        </div>
    </div>

    <script>
        let ws = null;
        let isStreaming = false;
        let currentMessageDiv = null;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = () => {
                addSystemMessage('Connected to Claude Code');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'start') {
                    isStreaming = true;
                    currentMessageDiv = addMessage('', 'assistant', true);
                } else if (data.type === 'stream') {
                    if (currentMessageDiv) {
                        currentMessageDiv.textContent += data.content;
                        scrollToBottom();
                    }
                } else if (data.type === 'end') {
                    isStreaming = false;
                    if (currentMessageDiv) {
                        currentMessageDiv.classList.remove('streaming');
                    }
                    currentMessageDiv = null;
                    document.getElementById('send').disabled = false;
                } else if (data.type === 'error') {
                    addSystemMessage('Error: ' + data.content);
                    isStreaming = false;
                    document.getElementById('send').disabled = false;
                }
            };
            
            ws.onclose = () => {
                addSystemMessage('Disconnected. Reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = (error) => {
                addSystemMessage('Connection error');
            };
        }
        
        function sendMessage() {
            const input = document.getElementById('input');
            const message = input.value.trim();
            
            if (!message || isStreaming || !ws || ws.readyState !== WebSocket.OPEN) return;
            
            addMessage(message, 'user');
            
            ws.send(JSON.stringify({
                type: 'message',
                content: message
            }));
            
            input.value = '';
            autoResize(input);
            document.getElementById('send').disabled = true;
        }
        
        function addMessage(content, role, streaming = false) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content' + (streaming ? ' streaming' : '');
            contentDiv.textContent = content;
            
            messageDiv.appendChild(contentDiv);
            messagesDiv.appendChild(messageDiv);
            scrollToBottom();
            
            return contentDiv;
        }
        
        function addSystemMessage(content) {
            addMessage(content, 'system');
        }
        
        function scrollToBottom() {
            const messages = document.getElementById('messages');
            messages.scrollTop = messages.scrollHeight;
        }
        
        function handleKeyDown(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }
        
        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
        }
        
        // Connect on load
        connectWebSocket();
        document.getElementById('input').focus();
    </script>
</body>
</html>
        """)
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for streaming Claude responses."""
        await websocket.accept()
        
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message["type"] == "message":
                    # Start streaming response
                    await websocket.send_text(json.dumps({
                        "type": "start"
                    }))
                    
                    # Stream Claude Code output
                    async for chunk in stream_claude_response(
                        message["content"], 
                        app.state.working_directory
                    ):
                        await websocket.send_text(json.dumps({
                            "type": "stream",
                            "content": chunk
                        }))
                    
                    # End streaming
                    await websocket.send_text(json.dumps({
                        "type": "end"
                    }))
                    
        except WebSocketDisconnect:
            pass
        except Exception as e:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": str(e)
            }))
    
    return app


async def stream_claude_response(prompt: str, working_dir: str) -> AsyncGenerator[str, None]:
    """Stream output from Claude Code CLI."""
    cmd = ["claude", prompt]
    
    try:
        # Start the process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
            env={**os.environ}
        )
        
        # Stream stdout
        async for line in process.stdout:
            yield line.decode('utf-8', errors='replace')
        
        # Wait for process to complete
        await process.wait()
        
        # If there's stderr, yield it too
        if process.returncode != 0:
            stderr = await process.stderr.read()
            if stderr:
                yield f"\n[Error] {stderr.decode('utf-8', errors='replace')}"
                
    except Exception as e:
        yield f"\n[Error] {str(e)}"


def main():
    """Run the chat interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="cuti Chat Interface")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--working-dir", help="Working directory")
    
    args = parser.parse_args()
    
    app = create_chat_app(args.working_dir)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()