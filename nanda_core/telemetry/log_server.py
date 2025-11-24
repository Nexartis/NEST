#!/usr/bin/env python3
"""
WebSocket Log Streaming Server
"""

import json
import asyncio
from typing import Set
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading


class LogStreamServer:
    """
    WebSocket server for streaming logs.
    Provides both HTTP endpoint for recent logs and WebSocket for live streaming.
    """
    
    def __init__(self, telemetry_system, port: int = 6001):
        """
        Initialize log stream server.
        
        Args:
            telemetry_system: TelemetrySystem instance
            port: Port for log server (default: 6001, agent runs on 6000)
        """
        self.telemetry_system = telemetry_system
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)
        
        # WebSocket clients
        self.clients: Set = set()
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/logs', methods=['GET'])
        def get_logs():
            """Get recent logs (last 50)"""
            n = int(request.args.get('n', 50))
            logs = self.telemetry_system.get_recent_logs(n)
            return jsonify({
                'logs': logs,
                'count': len(logs)
            })
        
        @self.app.route('/logs/stream', methods=['GET'])
        def stream_logs():
            """
            Server-Sent Events endpoint for log streaming.
            WebSocket alternative using SSE (simpler, works in browser).
            """
            def generate():
                # Send recent logs first
                recent = self.telemetry_system.get_recent_logs(10)
                for log in recent:
                    yield f"data: {json.dumps(log)}\n\n"
                
                # TODO: Stream new logs as they arrive
                # For now, just keeps connection open
                while True:
                    yield f": keepalive\n\n"
                    import time
                    time.sleep(30)
            
            return self.app.response_class(
                generate(),
                mimetype='text/event-stream'
            )
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check"""
            return jsonify({'status': 'ok'})
    
    def start(self):
        """Start log server in background thread"""
        def run():
            self.app.run(
                host='0.0.0.0',
                port=self.port,
                debug=False,
                use_reloader=False
            )
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        print(f"📊 Log server started: http://localhost:{self.port}/logs")