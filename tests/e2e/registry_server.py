#!/usr/bin/env python3
"""
Simple in-memory agent registry for E2E testing.

Flask-based registry server with no database dependency.
Provides endpoints matching the NANDA registry API for:
- Agent registration and discovery
- Health checks
- Agent status management

Usage:
    python registry_server.py  # Starts on port 5000
    python registry_server.py --port 5001  # Custom port
"""

import argparse
import sys
import threading
from datetime import datetime
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request


def create_app() -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)

    # In-memory storage
    agents: Dict[str, Dict[str, Any]] = {}
    lock = threading.Lock()

    # =============================================================================
    # Health Endpoints
    # =============================================================================

    @app.route("/health", methods=["GET"])
    def health():
        """
        Health check endpoint.

        Returns:
            200: {"status": "ok", "agents_count": N}
        """
        with lock:
            return jsonify(
                {
                    "status": "ok",
                    "agents_count": len(agents),
                    "timestamp": datetime.now().isoformat(),
                }
            )

    @app.route("/stats", methods=["GET"])
    def stats():
        """
        Registry statistics endpoint.

        Returns:
            200: {"total_agents": N, "active_agents": N}
        """
        with lock:
            active = sum(1 for a in agents.values() if a.get("status") == "active")
            return jsonify(
                {
                    "total_agents": len(agents),
                    "active_agents": active,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    # =============================================================================
    # Agent Registration Endpoints
    # =============================================================================

    @app.route("/register", methods=["POST"])
    def register():
        """
        Register an agent with the registry.

        Request Body:
            {"agent_id": "string", "agent_url": "string", ...optional metadata}

        Returns:
            200: {"status": "registered", "agent_id": "string"}
            400: {"error": "Missing required field"}
        """
        data = request.json
        if not data:
            return jsonify({"error": "Request body required"}), 400

        agent_id = data.get("agent_id")
        agent_url = data.get("agent_url")

        if not agent_id:
            return jsonify({"error": "Missing required field: agent_id"}), 400
        if not agent_url:
            return jsonify({"error": "Missing required field: agent_url"}), 400

        with lock:
            agents[agent_id] = {
                "agent_id": agent_id,
                "agent_url": agent_url,
                "name": data.get("name", agent_id),
                "description": data.get("description", ""),
                "capabilities": data.get("capabilities", []),
                "tags": data.get("tags", []),
                "status": "active",
                "registered_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

        return jsonify({"status": "registered", "agent_id": agent_id})

    @app.route("/unregister/<agent_id>", methods=["DELETE"])
    def unregister(agent_id: str):
        """
        Unregister an agent from the registry.

        Returns:
            200: {"status": "unregistered", "agent_id": "string"}
            404: {"error": "Agent not found"}
        """
        with lock:
            if agent_id in agents:
                del agents[agent_id]
                return jsonify({"status": "unregistered", "agent_id": agent_id})
            return jsonify({"error": f"Agent '{agent_id}' not found"}), 404

    # =============================================================================
    # Agent Lookup Endpoints
    # =============================================================================

    @app.route("/lookup/<agent_id>", methods=["GET"])
    def lookup(agent_id: str):
        """
        Look up an agent by ID.

        Returns:
            200: Agent data dict
            404: {"error": "Agent not found"}
        """
        with lock:
            agent = agents.get(agent_id)
            if agent:
                return jsonify(agent)
            return jsonify({"error": f"Agent '{agent_id}' not found"}), 404

    @app.route("/list", methods=["GET"])
    def list_agents():
        """
        List all registered agents.

        Returns:
            200: {"agents": [...], "count": N}
        """
        with lock:
            return jsonify({"agents": list(agents.values()), "count": len(agents)})

    @app.route("/search", methods=["GET"])
    def search():
        """
        Search agents by query, capabilities, or tags.

        Query Params:
            q: Search query (matches agent_id, name, description)
            capabilities: Comma-separated capabilities to match
            tags: Comma-separated tags to match

        Returns:
            200: {"agents": [...], "count": N}
        """
        query = request.args.get("q", "").lower()
        capabilities = (
            request.args.get("capabilities", "").split(",")
            if request.args.get("capabilities")
            else []
        )
        tags = (
            request.args.get("tags", "").split(",") if request.args.get("tags") else []
        )

        # Filter empty strings
        capabilities = [c.strip() for c in capabilities if c.strip()]
        tags = [t.strip() for t in tags if t.strip()]

        with lock:
            results = []
            for agent in agents.values():
                # Query match
                if query:
                    searchable = f"{agent.get('agent_id', '')} {agent.get('name', '')} {agent.get('description', '')}".lower()
                    if query not in searchable:
                        continue

                # Capabilities match
                if capabilities:
                    agent_caps = agent.get("capabilities", [])
                    if not any(c in agent_caps for c in capabilities):
                        continue

                # Tags match
                if tags:
                    agent_tags = agent.get("tags", [])
                    if not any(t in agent_tags for t in tags):
                        continue

                results.append(agent)

            return jsonify({"agents": results, "count": len(results)})

    # =============================================================================
    # Agent Status Endpoints
    # =============================================================================

    @app.route("/status/<agent_id>", methods=["GET"])
    def get_status(agent_id: str):
        """
        Get agent status.

        Returns:
            200: {"agent_id": "string", "status": "string", "updated_at": "string"}
            404: {"error": "Agent not found"}
        """
        with lock:
            agent = agents.get(agent_id)
            if agent:
                return jsonify(
                    {
                        "agent_id": agent_id,
                        "status": agent.get("status", "unknown"),
                        "updated_at": agent.get("updated_at"),
                    }
                )
            return jsonify({"error": f"Agent '{agent_id}' not found"}), 404

    @app.route("/status/<agent_id>", methods=["PUT"])
    def update_status(agent_id: str):
        """
        Update agent status.

        Request Body:
            {"status": "active|inactive|busy", ...optional metadata}

        Returns:
            200: {"status": "updated", "agent_id": "string"}
            404: {"error": "Agent not found"}
        """
        with lock:
            if agent_id not in agents:
                return jsonify({"error": f"Agent '{agent_id}' not found"}), 404

            data = request.json or {}
            if "status" in data:
                agents[agent_id]["status"] = data["status"]
            if "metadata" in data:
                agents[agent_id]["metadata"] = data["metadata"]
            agents[agent_id]["updated_at"] = datetime.now().isoformat()

            return jsonify({"status": "updated", "agent_id": agent_id})

    # =============================================================================
    # MCP Server Endpoints (for MCP integration tests)
    # =============================================================================

    mcp_servers: Dict[str, Dict[str, Any]] = {}

    @app.route("/mcp_servers", methods=["GET"])
    def list_mcp_servers():
        """List all MCP servers."""
        provider = request.args.get("provider")
        with lock:
            if provider:
                filtered = [
                    s for s in mcp_servers.values() if s.get("provider") == provider
                ]
                return jsonify({"servers": filtered, "count": len(filtered)})
            return jsonify(
                {"servers": list(mcp_servers.values()), "count": len(mcp_servers)}
            )

    @app.route("/mcp_servers/<server_name>", methods=["GET"])
    def get_mcp_server(server_name: str):
        """Get MCP server by name."""
        with lock:
            server = mcp_servers.get(server_name)
            if server:
                return jsonify(server)
            return jsonify({"error": f"MCP server '{server_name}' not found"}), 404

    @app.route("/mcp_servers", methods=["POST"])
    def register_mcp_server():
        """Register an MCP server."""
        data = request.json
        if not data:
            return jsonify({"error": "Request body required"}), 400

        qualified_name = data.get("qualified_name")
        if not qualified_name:
            return jsonify({"error": "Missing required field: qualified_name"}), 400

        with lock:
            mcp_servers[qualified_name] = {
                "qualified_name": qualified_name,
                "endpoint": data.get("endpoint", ""),
                "server_url": data.get("server_url", data.get("endpoint", "")),
                "description": data.get("description", ""),
                "provider": data.get("provider", "nanda"),
                "config": data.get("config", {}),
                "registered_at": datetime.now().isoformat(),
            }

        return jsonify({"status": "registered", "qualified_name": qualified_name})

    # =============================================================================
    # Test Control Endpoints (for E2E test setup/teardown)
    # =============================================================================

    @app.route("/_reset", methods=["POST"])
    def reset():
        """Reset all data (for test cleanup)."""
        with lock:
            agents.clear()
            mcp_servers.clear()
        return jsonify({"status": "reset", "message": "All data cleared"})

    @app.route("/_seed", methods=["POST"])
    def seed():
        """Seed test data."""
        data = request.json or {}
        with lock:
            for agent in data.get("agents", []):
                agents[agent["agent_id"]] = {
                    **agent,
                    "status": agent.get("status", "active"),
                    "registered_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
            for server in data.get("mcp_servers", []):
                mcp_servers[server["qualified_name"]] = {
                    **server,
                    "registered_at": datetime.now().isoformat(),
                }
        return jsonify(
            {
                "status": "seeded",
                "agents_count": len(data.get("agents", [])),
                "mcp_servers_count": len(data.get("mcp_servers", [])),
            }
        )

    return app


def main():
    """Run the registry server."""
    parser = argparse.ArgumentParser(description="E2E Test Registry Server")
    parser.add_argument("--port", type=int, default=5000, help="Port to run on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    app = create_app()
    print(f"Starting E2E Registry Server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
