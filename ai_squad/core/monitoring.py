"""
Monitoring API for AI-Squad Metrics

Provides a simple API to query and visualize convoy metrics, resource usage,
and system health. Can be used standalone or integrated into existing dashboards.

Quick Start:
    # Start monitoring API
    from ai_squad.core.monitoring import start_monitoring_api
    
    start_monitoring_api(port=8080)
    # Access at http://localhost:8080

Endpoints:
    GET  /health                    - System health check
    GET  /metrics/convoys           - Recent convoy metrics
    GET  /metrics/convoys/stats     - Convoy statistics
    GET  /metrics/resources         - Resource usage over time
    GET  /metrics/system            - Current system status
    GET  /dashboard                 - Simple HTML dashboard

Usage:
    import requests
    
    # Get recent convoys
    response = requests.get('http://localhost:8080/metrics/convoys')
    convoys = response.json()
    
    # Get statistics
    response = requests.get('http://localhost:8080/metrics/convoys/stats?hours=24')
    stats = response.json()
"""
import json
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from .metrics import get_global_collector
from .resource_monitor import get_global_monitor

logger = logging.getLogger(__name__)


class MonitoringAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for monitoring API"""
    
    def log_message(self, format, *args):
        """Override to use logger instead of print"""
        logger.info(f"{self.address_string()} - {format%args}")
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        try:
            if path == '/health':
                self._handle_health()
            elif path == '/metrics/convoys':
                self._handle_convoys(query_params)
            elif path == '/metrics/convoys/stats':
                self._handle_convoy_stats(query_params)
            elif path == '/metrics/resources':
                self._handle_resources(query_params)
            elif path == '/metrics/system':
                self._handle_system_status()
            elif path == '/dashboard':
                self._handle_dashboard()
            elif path == '/':
                self._handle_root()
            else:
                self._send_error(404, "Not Found")
        
        except Exception as e:
            logger.error(f"Error handling request {path}: {e}")
            self._send_error(500, str(e))
    
    def _handle_health(self):
        """Health check endpoint"""
        response = {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "ai-squad-monitoring"
        }
        self._send_json_response(response)
    
    def _handle_convoys(self, params: Dict):
        """Get recent convoy metrics"""
        limit = int(params.get('limit', ['10'])[0])
        status = params.get('status', [None])[0]
        
        collector = get_global_collector()
        convoys = collector.get_recent_convoy_metrics(limit=limit, status=status)
        
        self._send_json_response({
            "count": len(convoys),
            "convoys": convoys
        })
    
    def _handle_convoy_stats(self, params: Dict):
        """Get convoy statistics"""
        hours = int(params.get('hours', ['24'])[0])
        
        collector = get_global_collector()
        stats = collector.get_convoy_stats(hours=hours)
        
        self._send_json_response({
            "period_hours": hours,
            "stats": stats
        })
    
    def _handle_resources(self, params: Dict):
        """Get resource metrics over time"""
        hours = int(params.get('hours', ['1'])[0])
        sample_interval = int(params.get('sample', ['10'])[0])
        
        collector = get_global_collector()
        resources = collector.get_resource_metrics(
            hours=hours,
            sample_interval=sample_interval
        )
        
        self._send_json_response({
            "period_hours": hours,
            "sample_interval": sample_interval,
            "count": len(resources),
            "resources": resources
        })
    
    def _handle_system_status(self):
        """Get current system status"""
        # Resource monitor status
        monitor = get_global_monitor()
        current_metrics = monitor.get_current_metrics()
        monitor_stats = monitor.get_stats()
        
        # Metrics collector status
        collector = get_global_collector()
        collector_stats = collector.get_stats()
        
        # Calculate optimal parallelism
        optimal_parallel = monitor.calculate_optimal_parallelism(
            max_parallel=20,
            baseline=5
        )
        
        response = {
            "timestamp": time.time(),
            "resources": {
                "cpu_percent": current_metrics.cpu_percent,
                "memory_percent": current_metrics.memory_percent,
                "memory_available_mb": current_metrics.memory_available_mb,
                "thread_count": current_metrics.thread_count,
                "process_cpu_percent": current_metrics.process_cpu_percent,
                "process_memory_mb": current_metrics.process_memory_mb
            },
            "recommendations": {
                "optimal_parallelism": optimal_parallel,
                "should_throttle": monitor.should_throttle(),
                "throttle_factor": monitor.get_throttle_factor()
            },
            "monitoring": {
                "resource_monitor": monitor_stats,
                "metrics_collector": collector_stats
            }
        }
        
        self._send_json_response(response)
    
    def _handle_dashboard(self):
        """Serve simple HTML dashboard"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>AI-Squad Monitoring Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1 { color: #333; }
        h2 { color: #666; margin-top: 30px; }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .metric-card {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #4CAF50;
        }
        .metric-card.warning {
            border-left-color: #FF9800;
        }
        .metric-card.error {
            border-left-color: #f44336;
        }
        .metric-label {
            font-size: 12px;
            color: #999;
            text-transform: uppercase;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
            margin: 5px 0;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-healthy {
            background: #4CAF50;
            color: white;
        }
        .status-warning {
            background: #FF9800;
            color: white;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #f0f0f0;
            font-weight: bold;
        }
        .refresh-note {
            color: #999;
            font-size: 12px;
            text-align: center;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 AI-Squad Monitoring Dashboard</h1>
        <span class="status-badge status-healthy">OPERATIONAL</span>
        
        <h2>System Resources</h2>
        <div class="metric-grid">
            <div class="metric-card" id="cpu-card">
                <div class="metric-label">CPU Usage</div>
                <div class="metric-value" id="cpu-value">--%</div>
            </div>
            <div class="metric-card" id="memory-card">
                <div class="metric-label">Memory Usage</div>
                <div class="metric-value" id="memory-value">--%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Threads</div>
                <div class="metric-value" id="threads-value">--</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Optimal Parallelism</div>
                <div class="metric-value" id="parallelism-value">--</div>
            </div>
        </div>
        
        <h2>Convoy Statistics (Last 24 Hours)</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Convoys</div>
                <div class="metric-value" id="total-convoys">--</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Completed</div>
                <div class="metric-value" id="completed-convoys">--</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Failed</div>
                <div class="metric-value" id="failed-convoys">--</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Duration</div>
                <div class="metric-value" id="avg-duration">--s</div>
            </div>
        </div>
        
        <h2>Recent Convoys</h2>
        <table id="convoys-table">
            <thead>
                <tr>
                    <th>Convoy ID</th>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Members</th>
                    <th>Duration</th>
                </tr>
            </thead>
            <tbody id="convoys-tbody">
                <tr><td colspan="5">Loading...</td></tr>
            </tbody>
        </table>
        
        <div class="refresh-note">Auto-refreshing every 30 seconds | <a href="/dashboard">Manual Refresh</a></div>
    </div>
    
    <script>
        // Fetch system status
        fetch('/metrics/system')
            .then(r => r.json())
            .then(data => {
                // Update resource metrics
                const cpu = data.resources.cpu_percent.toFixed(1);
                const memory = data.resources.memory_percent.toFixed(1);
                
                document.getElementById('cpu-value').textContent = cpu + '%';
                document.getElementById('memory-value').textContent = memory + '%';
                document.getElementById('threads-value').textContent = data.resources.thread_count;
                document.getElementById('parallelism-value').textContent = data.recommendations.optimal_parallelism;
                
                // Color code based on usage
                const cpuCard = document.getElementById('cpu-card');
                if (cpu > 80) cpuCard.className = 'metric-card error';
                else if (cpu > 60) cpuCard.className = 'metric-card warning';
                
                const memCard = document.getElementById('memory-card');
                if (memory > 85) memCard.className = 'metric-card error';
                else if (memory > 70) memCard.className = 'metric-card warning';
            });
        
        // Fetch convoy stats
        fetch('/metrics/convoys/stats?hours=24')
            .then(r => r.json())
            .then(data => {
                const stats = data.stats;
                document.getElementById('total-convoys').textContent = stats.total_convoys || 0;
                document.getElementById('completed-convoys').textContent = stats.completed || 0;
                document.getElementById('failed-convoys').textContent = stats.failed || 0;
                
                const avgDur = stats.avg_duration || 0;
                document.getElementById('avg-duration').textContent = avgDur.toFixed(1) + 's';
            });
        
        // Fetch recent convoys
        fetch('/metrics/convoys?limit=10')
            .then(r => r.json())
            .then(data => {
                const tbody = document.getElementById('convoys-tbody');
                tbody.innerHTML = '';
                
                if (data.convoys.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5">No convoys found</td></tr>';
                    return;
                }
                
                data.convoys.forEach(convoy => {
                    const row = tbody.insertRow();
                    row.insertCell(0).textContent = convoy.convoy_id.substring(0, 12) + '...';
                    row.insertCell(1).textContent = convoy.convoy_name || '-';
                    
                    const statusCell = row.insertCell(2);
                    const status = convoy.status || 'unknown';
                    statusCell.innerHTML = `<span class="status-badge status-${status === 'completed' ? 'healthy' : 'warning'}">${status.toUpperCase()}</span>`;
                    
                    const completed = convoy.completed_members || 0;
                    const total = convoy.total_members || 0;
                    row.insertCell(3).textContent = `${completed}/${total}`;
                    
                    const duration = convoy.duration_seconds || 0;
                    row.insertCell(4).textContent = duration > 0 ? duration.toFixed(1) + 's' : '-';
                });
            });
    </script>
</body>
</html>
        """
        
        self._send_html_response(html)
    
    def _handle_root(self):
        """Root endpoint - redirect to dashboard"""
        self.send_response(302)
        self.send_header('Location', '/dashboard')
        self.end_headers()
    
    def _send_json_response(self, data: Any, status_code: int = 200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        json_data = json.dumps(data, indent=2, default=str)
        self.wfile.write(json_data.encode('utf-8'))
    
    def _send_html_response(self, html: str, status_code: int = 200):
        """Send HTML response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def _send_error(self, status_code: int, message: str):
        """Send error response"""
        self._send_json_response({
            "error": message,
            "status_code": status_code
        }, status_code=status_code)


def start_monitoring_api(host: str = '0.0.0.0', port: int = 8080):
    """
    Start monitoring API server.
    
    Args:
        host: Host to bind to
        port: Port to listen on
    
    Example:
        from ai_squad.core.monitoring import start_monitoring_api
        
        # Start server
        start_monitoring_api(port=8080)
        
        # Access dashboard at http://localhost:8080/dashboard
    """
    server_address = (host, port)
    httpd = HTTPServer(server_address, MonitoringAPIHandler)
    
    logger.info(f"Starting monitoring API on {host}:{port}")
    logger.info(f"Dashboard available at: http://{host}:{port}/dashboard")
    logger.info("Press Ctrl+C to stop")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nStopping monitoring API...")
        httpd.shutdown()


if __name__ == "__main__":
    # Run standalone
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    start_monitoring_api(port=port)
