        @self.app.route('/api/interfaces/<interface_name>/status', methods=['GET'])
        def api_get_interface_status(interface_name):
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                config = self.tc_manager.get_current_tc_config(interface_name)
                return jsonify(config)
                
            except Exception as e:
                self.logger.error(f"Error getting interface status: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/interfaces/<interface_name>/statistics', methods=['GET'])
        def api_get_interface_statistics(interface_name):
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                stats = self.tc_manager.get_statistics(interface_name)
                return jsonify(stats)
                
            except Exception as e:
                self.logger.error(f"Error getting interface statistics: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/interfaces/<interface_name>/clear', methods=['POST'])
        def api_clear_interface(interface_name):
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                self.tc_manager._clear_tc_config(interface_name)
                return jsonify({'message': f'TC configuration cleared for {interface_name}'})
                
            except Exception as e:
                self.logger.error(f"Error clearing interface: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/policies', methods=['GET'])
        def api_get_policies():
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                policies = []
                for policy_name in self.tc_manager.list_policies():
                    policy = self.tc_manager.get_policy(policy_name)
                    if policy:
                        policies.append({
                            'name': policy.name,
                            'description': policy.description,
                            'interface': policy.interface,
                            'enabled': policy.enabled,
                            'created_at': policy.created_at.isoformat(),
                            'updated_at': policy.updated_at.isoformat(),
                            'qdiscs_count': len(policy.qdiscs),
                            'classes_count': len(policy.classes),
                            'filters_count': len(policy.filters)
                        })
                
                return jsonify(policies)
                
            except Exception as e:
                self.logger.error(f"Error getting policies: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/policies/<policy_name>', methods=['GET'])
        def api_get_policy(policy_name):
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                policy = self.tc_manager.get_policy(policy_name)
                if not policy:
                    return jsonify({'error': 'Policy not found'}), 404
                
                return jsonify({
                    'name': policy.name,
                    'description': policy.description,
                    'interface': policy.interface,
                    'enabled': policy.enabled,
                    'created_at': policy.created_at.isoformat(),
                    'updated_at': policy.updated_at.isoformat(),
                    'qdiscs': [{
                        'handle': q.handle,
                        'parent': q.parent,
                        'kind': q.kind,
                        'interface': q.interface,
                        'options': q.options,
                        'enabled': q.enabled
                    } for q in policy.qdiscs],
                    'classes': [{
                        'classid': c.classid,
                        'parent': c.parent,
                        'kind': c.kind,
                        'interface': c.interface,
                        'rate': c.rate,
                        'ceil': c.ceil,
                        'prio': c.prio,
                        'enabled': c.enabled
                    } for c in policy.classes],
                    'filters': [{
                        'handle': f.handle,
                        'parent': f.parent,
                        'protocol': f.protocol,
                        'prio': f.prio,
                        'kind': f.kind,
                        'interface': f.interface,
                        'match_criteria': f.match_criteria,
                        'flowid': f.flowid,
                        'enabled': f.enabled
                    } for f in policy.filters]
                })
                
            except Exception as e:
                self.logger.error(f"Error getting policy: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/policies', methods=['POST'])
        def api_create_policy():
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                
                # Convert JSON data to policy objects
                policy = self._json_to_policy(data)
                
                if self.tc_manager.create_policy(policy):
                    return jsonify({'message': f'Policy {policy.name} created successfully'}), 201
                else:
                    return jsonify({'error': 'Failed to create policy'}), 500
                
            except Exception as e:
                self.logger.error(f"Error creating policy: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/policies/<policy_name>', methods=['DELETE'])
        def api_delete_policy(policy_name):
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                if self.tc_manager.delete_policy(policy_name):
                    return jsonify({'message': f'Policy {policy_name} deleted successfully'})
                else:
                    return jsonify({'error': 'Failed to delete policy'}), 500
                
            except Exception as e:
                self.logger.error(f"Error deleting policy: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/policies/<policy_name>/apply', methods=['POST'])
        def api_apply_policy(policy_name):
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                test_mode = request.args.get('test', 'false').lower() == 'true'
                
                if self.tc_manager.apply_policy(policy_name, test_mode):
                    if test_mode:
                        return jsonify({'message': f'Policy {policy_name} test passed'})
                    else:
                        return jsonify({'message': f'Policy {policy_name} applied successfully'})
                else:
                    return jsonify({'error': 'Failed to apply policy'}), 500
                
            except Exception as e:
                self.logger.error(f"Error applying policy: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/policies/<policy_name>/export', methods=['GET'])
        def api_export_policy(policy_name):
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                format_type = request.args.get('format', 'json')
                exported = self.tc_manager.export_policy(policy_name, format_type)
                
                if exported:
                    filename = f"{policy_name}.{format_type}"
                    
                    # Write to temporary file
                    temp_path = Path(f"/tmp/{filename}")
                    with open(temp_path, 'w') as f:
                        f.write(exported)
                    
                    return send_file(str(temp_path), as_attachment=True, download_name=filename)
                else:
                    return jsonify({'error': 'Failed to export policy'}), 500
                
            except Exception as e:
                self.logger.error(f"Error exporting policy: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/policies/import', methods=['POST'])
        def api_import_policy():
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                if 'file' not in request.files:
                    return jsonify({'error': 'No file provided'}), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400
                
                # Determine format from file extension
                filename = secure_filename(file.filename)
                if filename.endswith('.yaml') or filename.endswith('.yml'):
                    format_type = 'yaml'
                else:
                    format_type = 'json'
                
                # Read file content
                policy_data = file.read().decode('utf-8')
                
                if self.tc_manager.import_policy(policy_data, format_type):
                    return jsonify({'message': 'Policy imported successfully'}), 201
                else:
                    return jsonify({'error': 'Failed to import policy'}), 500
                
            except Exception as e:
                self.logger.error(f"Error importing policy: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/policies/htb', methods=['POST'])
        def api_create_htb_policy():
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                
                name = data.get('name')
                interface = data.get('interface')
                total_rate = data.get('total_rate')
                classes = data.get('classes', [])
                
                if not all([name, interface, total_rate]):
                    return jsonify({'error': 'Missing required fields: name, interface, total_rate'}), 400
                
                if self.tc_manager.create_simple_htb_policy(name, interface, total_rate, classes):
                    return jsonify({'message': f'HTB policy {name} created successfully'}), 201
                else:
                    return jsonify({'error': 'Failed to create HTB policy'}), 500
                
            except Exception as e:
                self.logger.error(f"Error creating HTB policy: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/interfaces/<interface_name>/rollback', methods=['POST'])
        def api_rollback_interface(interface_name):
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                # Get the most recent rollback entry
                cursor = self.tc_manager.db_conn.cursor()
                cursor.execute("""
                    SELECT id FROM tc_rollback_history 
                    WHERE interface = ? AND status = 'active'
                    ORDER BY applied_at DESC
                    LIMIT 1
                """, (interface_name,))
                
                row = cursor.fetchone()
                if row:
                    rollback_id = str(row[0])
                    if self.tc_manager._rollback_config(rollback_id):
                        return jsonify({'message': f'Configuration rolled back for {interface_name}'})
                    else:
                        return jsonify({'error': 'Failed to rollback configuration'}), 500
                else:
                    return jsonify({'error': 'No rollback data found'}), 404
                
            except Exception as e:
                self.logger.error(f"Error rolling back interface: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/statistics/cleanup', methods=['POST'])
        def api_cleanup_statistics():
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                days = request.args.get('days', 7, type=int)
                self.tc_manager.cleanup_old_statistics(days)
                
                return jsonify({'message': f'Statistics older than {days} days cleaned up'})
                
            except Exception as e:
                self.logger.error(f"Error cleaning up statistics: {e}")
                return jsonify({'error': str(e)}), 500
        
        # WebSocket endpoint for real-time updates
        @self.app.route('/ws')
        async def websocket_handler():
            async def handler(websocket, path):
                self.websocket_clients.add(websocket)
                try:
                    await websocket.wait_closed()
                finally:
                    self.websocket_clients.remove(websocket)
            
            return handler
    
    def _json_to_policy(self, data: Dict[str, Any]) -> TCPolicy:
        """Convert JSON data to TCPolicy object"""
        qdiscs = []
        for qdisc_data in data.get('qdiscs', []):
            qdisc = TCQdisc(
                handle=qdisc_data['handle'],
                parent=qdisc_data['parent'],
                kind=qdisc_data['kind'],
                interface=data['interface'],
                options=qdisc_data.get('options', {}),
                created_at=datetime.now(),
                enabled=qdisc_data.get('enabled', True)
            )
            qdiscs.append(qdisc)
        
        classes = []
        for class_data in data.get('classes', []):
            class_obj = TCClass(
                classid=class_data['classid'],
                parent=class_data['parent'],
                kind=class_data['kind'],
                interface=data['interface'],
                rate=class_data['rate'],
                ceil=class_data.get('ceil', class_data['rate']),
                burst=class_data.get('burst'),
                cburst=class_data.get('cburst'),
                prio=class_data.get('prio', 0),
                quantum=class_data.get('quantum'),
                options=class_data.get('options', {}),
                created_at=datetime.now(),
                enabled=class_data.get('enabled', True)
            )
            classes.append(class_obj)
        
        filters = []
        for filter_data in data.get('filters', []):
            filter_obj = TCFilter(
                handle=filter_data['handle'],
                parent=filter_data['parent'],
                protocol=filter_data['protocol'],
                prio=filter_data['prio'],
                kind=filter_data['kind'],
                interface=data['interface'],
                match_criteria=filter_data.get('match_criteria', {}),
                flowid=filter_data['flowid'],
                action=filter_data.get('action'),
                created_at=datetime.now(),
                enabled=filter_data.get('enabled', True)
            )
            filters.append(filter_obj)
        
        return TCPolicy(
            name=data['name'],
            description=data.get('description', ''),
            interface=data['interface'],
            qdiscs=qdiscs,
            classes=classes,
            filters=filters,
            enabled=data.get('enabled', True)
        )
    
    def _start_background_tasks(self):
        """Start background tasks for monitoring and WebSocket updates"""
        def monitor_statistics():
            while True:
                try:
                    if self.tc_manager:
                        # Get all interfaces
                        interfaces = self.tc_manager.discover_interfaces()
                        
                        # Collect statistics for each interface with TC config
                        for interface in interfaces:
                            config = self.tc_manager.get_current_tc_config(interface.name)
                            if any(config.values()):  # Has TC configuration
                                stats = self.tc_manager.get_statistics(interface.name)
                                self.tc_manager.record_statistics(interface.name)
                                
                                # Send to WebSocket clients
                                if stats and self.websocket_clients:
                                    message = {
                                        'type': 'statistics',
                                        'interface': interface.name,
                                        'data': stats,
                                        'timestamp': datetime.now().isoformat()
                                    }
                                    self._broadcast_websocket(message)
                    
                    time.sleep(30)  # Update every 30 seconds
                    
                except Exception as e:
                    self.logger.error(f"Error in background monitoring: {e}")
                    time.sleep(60)  # Wait longer on error
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_statistics, daemon=True)
        monitor_thread.start()
    
    def _broadcast_websocket(self, message: Dict[str, Any]):
        """Broadcast message to all WebSocket clients"""
        if not self.websocket_clients:
            return
        
        disconnected = set()
        for client in self.websocket_clients:
            try:
                asyncio.create_task(client.send(json.dumps(message)))
            except Exception:
                disconnected.add(client)
        
        # Remove disconnected clients
        for client in disconnected:
            self.websocket_clients.discard(client)
    
    def run(self):
        """Run the web server"""
        self.app.run(host=self.host, port=self.port, debug=self.debug)


# HTML Templates
def create_templates():
    """Create HTML templates for the web dashboard"""
    
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    # Base template
    base_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}LNMT TC Dashboard{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .sidebar {
            min-height: 100vh;
            background-color: #f8f9fa;
        }
        .nav-link.active {
            background-color: #0d6efd;
            color: white !important;
        }
        .status-up { color: #28a745; }
        .status-down { color: #dc3545; }
        .card-stat {
            transition: transform 0.2s;
        }
        .card-stat:hover {
            transform: translateY(-5px);
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <nav class="col-md-2 d-md-block sidebar">
                <div class="position-sticky pt-3">
                    <h4 class="text-center mb-4">LNMT TC</h4>
                    <ul class="nav flex-column">
                        <li class="nav-item">
                            <a class="nav-link" href="/">
                                <i class="fas fa-tachometer-alt"></i> Dashboard
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/interfaces">
                                <i class="fas fa-network-wired"></i> Interfaces
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/policies">
                                <i class="fas fa-cogs"></i> Policies
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/monitoring">
                                <i class="fas fa-chart-line"></i> Monitoring
                            </a>
                        </li>
                    </ul>
                </div>
            </nav>
            
            <main class="col-md-10 ms-sm-auto px-4">
                {% block content %}{% endblock %}
            </main>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
    """
    
    # Dashboard template
    dashboard_template = """
{% extends "base.html" %}

{% block title %}TC Dashboard - LNMT{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <h1 class="h2">Traffic Control Dashboard</h1>
    <div class="btn-toolbar mb-2 mb-md-0">
        <button class="btn btn-outline-secondary btn-sm" onclick="refreshData()">
            <i class="fas fa-sync-alt"></i> Refresh
        </button>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-3">
        <div class="card card-stat">
            <div class="card-body text-center">
                <i class="fas fa-network-wired fa-3x text-primary mb-3"></i>
                <h4 id="total-interfaces">-</h4>
                <p class="text-muted">Total Interfaces</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card card-stat">
            <div class="card-body text-center">
                <i class="fas fa-cogs fa-3x text-success mb-3"></i>
                <h4 id="total-policies">-</h4>
                <p class="text-muted">Active Policies</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card card-stat">
            <div class="card-body text-center">
                <i class="fas fa-check-circle fa-3x text-info mb-3"></i>
                <h4 id="interfaces-with-tc">-</h4>
                <p class="text-muted">Interfaces with TC</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card card-stat">
            <div class="card-body text-center">
                <i class="fas fa-exclamation-triangle fa-3x text-warning mb-3"></i>
                <h4 id="total-drops">-</h4>
                <p class="text-muted">Total Drops</p>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h5>Interface Status</h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Interface</th>
                                <th>Type</th>
                                <th>State</th>
                                <th>TC Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="interfaces-table">
                            <tr>
                                <td colspan="5" class="text-center">Loading...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5>Recent Activity</h5>
            </div>
            <div class="card-body">
                <div id="activity-log">
                    <p class="text-muted">No recent activity</p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
let ws;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === 'statistics') {
            updateStatistics(data);
        }
    };
    
    ws.onclose = function() {
        setTimeout(connectWebSocket, 5000); // Reconnect after 5 seconds
    };
}

function updateStatistics(data) {
    // Update real-time statistics display
    console.log('Statistics update:', data);
}

async function loadDashboardData() {
    try {
        // Load interfaces
        const interfacesResponse = await fetch('/api/interfaces');
        const interfaces = await interfacesResponse.json();
        
        // Load policies
        const policiesResponse = await fetch('/api/policies');
        const policies = await policiesResponse.json();
        
        // Update statistics
        document.getElementById('total-interfaces').textContent = interfaces.length;
        document.getElementById('total-policies').textContent = policies.length;
        
        // Update interfaces table
        const tableBody = document.getElementById('interfaces-table');
        tableBody.innerHTML = '';
        
        let interfacesWithTC = 0;
        
        for (const iface of interfaces) {
            // Check TC status
            const statusResponse = await fetch(`/api/interfaces/${iface.name}/status`);
            const status = await statusResponse.json();
            const hasTc = status.qdiscs?.length > 0 || status.classes?.length > 0 || status.filters?.length > 0;
            
            if (hasTc) interfacesWithTC++;
            
            const row = tableBody.insertRow();
            row.innerHTML = `
                <td>${iface.name}</td>
                <td><span class="badge bg-secondary">${iface.type}</span></td>
                <td><span class="badge ${iface.state === 'UP' ? 'bg-success' : 'bg-danger'}">${iface.state}</span></td>
                <td><span class="badge ${hasTc ? 'bg-primary' : 'bg-light text-dark'}">${hasTc ? 'Active' : 'None'}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewInterface('${iface.name}')">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${hasTc ? `<button class="btn btn-sm btn-outline-warning" onclick="clearInterface('${iface.name}')">
                        <i class="fas fa-trash"></i>
                    </button>` : ''}
                </td>
            `;
        }
        
        document.getElementById('interfaces-with-tc').textContent = interfacesWithTC;
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

function viewInterface(interfaceName) {
    window.location.href = `/interfaces?interface=${interfaceName}`;
}

async function clearInterface(interfaceName) {
    if (confirm(`Are you sure you want to clear TC configuration for ${interfaceName}?`)) {
        try {
            const response = await fetch(`/api/interfaces/${interfaceName}/clear`, {
                method: 'POST'
            });
            
            if (response.ok) {
                refreshData();
            } else {
                alert('Failed to clear interface configuration');
            }
        } catch (error) {
            console.error('Error clearing interface:', error);
            alert('Error clearing interface configuration');
        }
    }
}

function refreshData() {
    loadDashboardData();
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
    connectWebSocket();
    
    // Auto-refresh every 30 seconds
    setInterval(refreshData, 30000);
});
</script>
{% endblock %}
    """
    
    # Save templates
    with open(templates_dir / 'base.html', 'w') as f:
        f.write(base_template)
    
    with open(templates_dir / 'tc_dashboard.html', 'w') as f:
        f.write(dashboard_template)
    
    # Create other template files (simplified versions)
    interfaces_template = """
{% extends "base.html" %}
{% block title %}Interfaces - LNMT TC{% endblock %}
{% block content %}
<h1>Network Interfaces</h1>
<div id="interfaces-content">Loading...</div>
{% endblock %}
    """
    
    policies_template = """
{% extends "base.html" %}
{% block title %}Policies - LNMT TC{% endblock %}
{% block content %}
<h1>TC Policies</h1>
<div id="policies-content">Loading...</div>
{% endblock %}
    """
    
    monitoring_template = """
{% extends "base.html" %}
{% block title %}Monitoring - LNMT TC{% endblock %}
{% block content %}
<h1>TC Monitoring</h1>
<div id="monitoring-content">Loading...</div>
{% endblock %}
    """
    
    with open(templates_dir / 'tc_interfaces.html', 'w') as f:
        f.write(interfaces_template)
    
    with open(templates_dir / 'tc_policies.html', 'w') as f:
        f.write(policies_template)
    
    with open(templates_dir / 'tc_monitoring.html', 'w') as f:
        f.write(monitoring_template)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='LNMT TC Web API and Dashboard')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--create-templates', action='store_true', help='Create HTML templates')
    
    args = parser.parse_args()
    
    if args.create_templates:
        create_templates()
        print("HTML templates created in 'templates' directory")
        sys.exit(0)
    
    # Initialize logging
    logging.basicConfig(
        level=logging.INFO if not args.debug else logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create templates if they don't exist
    if not Path('templates').exists():
        create_templates()
        print("Created HTML templates")
    
    # Start web server
    api = TCWebAPI(host=args.host, port=args.port, debug=args.debug)
    print(f"Starting LNMT TC Web API on {args.host}:{args.port}")
    api.run()#!/usr/bin/env python3
"""
LNMT TC Web API and Dashboard
REST API and web interface for Traffic Control and Quality of Service management

Features:
- REST API endpoints for all TC operations
- Web dashboard with real-time statistics
- Policy management interface
- Live monitoring with WebSocket support
- Import/export functionality

Author: LNMT Development Team
License: MIT
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading
import asyncio
import websockets
import yaml

from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Import TC service
try:
    from tc_service import TCManager, TCPolicy, TCQdisc, TCClass, TCFilter
except ImportError:
    print("Warning: tc_service module not found. Some functionality may be limited.")
    TCManager = None

class TCWebAPI:
    """TC Web API and Dashboard"""
    
    def __init__(self, host='0.0.0.0', port=8080, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        self.app = Flask(__name__, template_folder='templates', static_folder='static')
        CORS(self.app)
        
        # Initialize TC Manager
        if TCManager:
            self.tc_manager = TCManager()
        else:
            self.tc_manager = None
        
        # WebSocket clients for real-time updates
        self.websocket_clients = set()
        
        # Setup routes
        self._setup_routes()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Start background tasks
        self._start_background_tasks()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        # Web dashboard routes
        @self.app.route('/')
        def index():
            return render_template('tc_dashboard.html')
        
        @self.app.route('/policies')
        def policies_page():
            return render_template('tc_policies.html')
        
        @self.app.route('/interfaces')
        def interfaces_page():
            return render_template('tc_interfaces.html')
        
        @self.app.route('/monitoring')
        def monitoring_page():
            return render_template('tc_monitoring.html')
        
        # API routes
        @self.app.route('/api/interfaces', methods=['GET'])
        def api_get_interfaces():
            try:
                if not self.tc_manager:
                    return jsonify({'error': 'TC Manager not available'}), 500
                
                interfaces = self.tc_manager.discover_interfaces()
                return jsonify([{
                    'name': iface.name,
                    'type': iface.type,
                    'state': iface.state,
                    'mtu': iface.mtu,
                    'mac_address': iface.mac_address,
                    'ip_addresses': iface.ip_addresses,
                    'speed': iface.speed,
                    'duplex': iface.duplex
                } for iface in interfaces])
                
            except Exception as e:
                self.logger.error(f"Error getting interfaces: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/interfaces/<interface_name>/status', methods