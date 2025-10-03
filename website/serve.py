#!/usr/bin/env python3
"""
Simple HTTP server for testing the Cuti website locally.
Usage: python serve.py [port]
"""

import http.server
import socketserver
import sys
import os

# Change to the website directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Get port from command line or use default
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

# Create server
Handler = http.server.SimpleHTTPRequestHandler

# Add CORS headers for local development
class CORSRequestHandler(Handler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super().end_headers()

    def log_message(self, format, *args):
        # Colorful logging
        print(f"\033[92m[{self.log_date_time_string()}]\033[0m {format % args}")

with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
    print(f"\n\033[94m╔═══════════════════════════════════════════════════╗\033[0m")
    print(f"\033[94m║\033[0m  🚀 Cuti Website Server                         \033[94m║\033[0m")
    print(f"\033[94m╠═══════════════════════════════════════════════════╣\033[0m")
    print(f"\033[94m║\033[0m  \033[92m✓\033[0m Server running at http://localhost:{PORT}      \033[94m║\033[0m")
    print(f"\033[94m║\033[0m  \033[92m✓\033[0m Press Ctrl+C to stop                           \033[94m║\033[0m")
    print(f"\033[94m╚═══════════════════════════════════════════════════╝\033[0m\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n\n\033[93m✓ Server stopped\033[0m\n")
        sys.exit(0)

