"""
Dashboard Flask Application

Provides web UI for monitoring AI-Squad orchestration.
"""
import logging
import os
import secrets
from pathlib import Path
from typing import Optional, TYPE_CHECKING

try:
    from flask import Flask, render_template, jsonify, request  # type: ignore[import-not-found]
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None

if TYPE_CHECKING:
    from flask import Flask as FlaskType  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


def create_app(workspace_root: Optional[Path] = None) -> "FlaskType":
    """Create and configure the Flask dashboard application."""
    if not FLASK_AVAILABLE:
        raise ImportError(
            "Flask is not installed. Install with: pip install flask"
        )
    
    workspace_root = workspace_root or Path.cwd()
    
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )
    app.config["WORKSPACE_ROOT"] = workspace_root
    app.config["SECRET_KEY"] = os.getenv("AI_SQUAD_DASHBOARD_SECRET", secrets.token_urlsafe(32))
    
    # Register routes
    register_routes(app)
    
    return app


def register_routes(app: "FlaskType") -> None:
    """Register all dashboard routes."""
    
    @app.route("/")
    def index():
        """Dashboard home page."""
        return render_template("index.html")
    
    @app.route("/health")
    def health_page():
        """Routing health dashboard."""
        return render_template("health.html")
    
    @app.route("/delegations")
    def delegations_page():
        """Delegations management page."""
        return render_template("delegations.html")
    
    @app.route("/graph")
    def graph_page():
        """Operational graph visualization."""
        return render_template("graph.html")
    
    @app.route("/work")
    def work_page():
        """Work items dashboard."""
        return render_template("work.html")
    
    @app.route("/convoys")
    def convoys_page():
        """Convoys dashboard."""
        return render_template("convoys.html")
    
    # API endpoints
    @app.route("/api/health")
    def api_health():
        """Get routing health data."""
        try:
            from ai_squad.core.router import HealthView, HealthConfig
            
            workspace = app.config["WORKSPACE_ROOT"]
            health_view = HealthView(workspace_root=workspace)
            health_cfg = HealthConfig()
            summary = health_view.summarize(config=health_cfg)
            
            return jsonify({"success": True, "data": summary})
        except (RuntimeError, OSError, ValueError) as e:
            logger.exception("Error fetching health data")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/api/delegations")
    def api_delegations():
        """Get delegation links."""
        try:
            from ai_squad.core.delegation import DelegationManager
            
            workspace = app.config["WORKSPACE_ROOT"]
            manager = DelegationManager(workspace_root=workspace)
            links = manager.list()
            
            return jsonify({
                "success": True,
                "data": [link.to_dict() for link in links]
            })
        except (RuntimeError, OSError, ValueError) as e:
            logger.exception("Error fetching delegations")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/api/graph")
    def api_graph():
        """Get operational graph data."""
        try:
            from ai_squad.core.operational_graph import OperationalGraph
            
            workspace = app.config["WORKSPACE_ROOT"]
            graph = OperationalGraph(workspace_root=workspace)
            
            # Get all nodes and edges
            nodes = [node.to_dict() for node in graph.get_nodes()]
            edges = [edge.to_dict() for edge in graph.get_edges()]
            
            return jsonify({
                "success": True,
                "data": {
                    "nodes": nodes,
                    "edges": edges,
                    "mermaid": graph.export_mermaid()
                }
            })
        except (RuntimeError, OSError, ValueError) as e:
            logger.exception("Error fetching graph data")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/api/graph/impact/<node_id>")
    def api_graph_impact(node_id: str):
        """Get impact analysis for a node."""
        try:
            from ai_squad.core.operational_graph import OperationalGraph
            
            workspace = app.config["WORKSPACE_ROOT"]
            graph = OperationalGraph(workspace_root=workspace)
            impact = graph.impact_analysis(node_id)
            
            return jsonify({"success": True, "data": impact})
        except (RuntimeError, OSError, ValueError) as e:
            logger.exception("Error computing impact analysis")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/api/work")
    def api_work():
        """Get work items."""
        try:
            from ai_squad.core.workstate import WorkStateManager
            
            workspace = app.config["WORKSPACE_ROOT"]
            manager = WorkStateManager(workspace_root=workspace)
            
            status = request.args.get("status")
            agent = request.args.get("agent")
            
            # Map status string to enum if provided
            status_filter = None
            if status:
                from ai_squad.core.workstate import WorkStatus
                status_map = {
                    "backlog": WorkStatus.BACKLOG,
                    "ready": WorkStatus.READY,
                    "in_progress": WorkStatus.IN_PROGRESS,
                    "blocked": WorkStatus.BLOCKED,
                    "done": WorkStatus.DONE,
                }
                status_filter = status_map.get(status)
            
            items = manager.list_work_items(status=status_filter, agent=agent)
            stats = manager.get_stats()
            return jsonify({
                "success": True,
                "data": {
                    "items": [item.to_dict() for item in items],
                    "stats": stats
                }
            })
        except (RuntimeError, OSError, ValueError) as e:
            logger.exception("Error fetching work items")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/workers")
    def api_workers():
        """Get worker lifecycle data."""
        try:
            from ai_squad.core.worker_lifecycle import WorkerLifecycleManager

            workspace = app.config["WORKSPACE_ROOT"]
            manager = WorkerLifecycleManager(workspace_root=workspace)
            workers = manager.list()

            return jsonify({"success": True, "data": [w.__dict__ for w in workers]})
        except (RuntimeError, OSError, ValueError) as e:
            logger.exception("Error fetching workers")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/hooks")
    def api_hooks():
        """Get hook metadata list."""
        try:
            from ai_squad.core.hooks import HookManager

            workspace = app.config["WORKSPACE_ROOT"]
            manager = HookManager(workspace_root=workspace)
            hooks = manager.list_hooks()

            return jsonify({"success": True, "data": hooks})
        except (RuntimeError, OSError, ValueError) as e:
            logger.exception("Error fetching hooks")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/api/convoys")
    def api_convoys():
        """Get convoys."""
        try:
            from ai_squad.core.workstate import WorkStateManager
            from ai_squad.core.convoy import ConvoyManager
            
            workspace = app.config["WORKSPACE_ROOT"]
            work_manager = WorkStateManager(workspace_root=workspace)
            convoy_manager = ConvoyManager(work_manager)
            
            convoys = convoy_manager.list_convoys()
            
            return jsonify({
                "success": True,
                "data": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "status": c.status.value,
                        "progress": c.get_progress()
                    }
                    for c in convoys
                ]
            })
        except (RuntimeError, OSError, ValueError) as e:
            logger.exception("Error fetching convoys")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/api/signals/<agent>")
    def api_signals(agent: str):
        """Get signals for an agent."""
        try:
            from ai_squad.core.signal import SignalManager
            
            workspace = app.config["WORKSPACE_ROOT"]
            manager = SignalManager(workspace_root=workspace)
            
            unread_only = request.args.get("unread", "false").lower() == "true"
            messages = manager.get_inbox(agent, unread_only=unread_only)
            
            return jsonify({
                "success": True,
                "data": [
                    {
                        "id": msg.id,
                        "sender": msg.sender,
                        "subject": msg.subject,
                        "body": msg.body[:200],
                        "priority": msg.priority.value,
                        "status": msg.status.value,
                        "created_at": msg.created_at,
                    }
                    for msg in messages
                ]
            })
        except (RuntimeError, OSError, ValueError) as e:
            logger.exception("Error fetching signals")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/api/identity")
    def api_identity():
        """Get current identity dossier."""
        from ai_squad.core.identity import IdentityManager

        workspace = app.config["WORKSPACE_ROOT"]
        manager = IdentityManager(workspace_root=workspace)
        dossier = manager.load()

        if dossier:
            return jsonify({"success": True, "data": dossier.to_dict()})
        return jsonify({"success": True, "data": None})
    
    @app.route("/api/capabilities")
    def api_capabilities():
        """Get installed capabilities."""
        from ai_squad.core.capability_registry import CapabilityRegistry

        workspace = app.config["WORKSPACE_ROOT"]
        registry = CapabilityRegistry(workspace_root=workspace)
        packages = registry.list()

        return jsonify({
            "success": True,
            "data": [pkg.to_dict() for pkg in packages]
        })
    
    @app.route("/api/scout")
    def api_scout():
        """Get scout worker runs."""
        from ai_squad.core.scout_worker import ScoutWorker

        workspace = app.config["WORKSPACE_ROOT"]
        worker = ScoutWorker(workspace_root=workspace)
        runs = worker.list_runs()

        data = []
        for run_id in runs:
            run = worker.load_run(run_id)
            if run:
                data.append(run.to_dict())

        return jsonify({"success": True, "data": data})


def run_dashboard(host: str = "127.0.0.1", port: int = 5050, debug: bool = False) -> None:
    """Run the dashboard server."""
    if not FLASK_AVAILABLE:
        raise ImportError(
            "Flask is not installed. Install with: pip install flask"
        )
    
    app = create_app()
    print(f"\n🚀 AI-Squad Dashboard running at http://{host}:{port}\n")
    app.run(host=host, port=port, debug=debug)
