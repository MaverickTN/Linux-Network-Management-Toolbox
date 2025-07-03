// web/static/js/dashboard.js

// Dashboard specific functionality
class Dashboard {
    constructor() {
        this.charts = {};
        this.refreshInterval = null;
        this.refreshRate = 30000; // 30 seconds
    }

    // Initialize dashboard
    async initialize() {
        try {
            await this.loadSummaryData();
            this.initializeCharts();
            this.loadRecentAlerts();
            this.startAutoRefresh();
            this.setupRealTimeUpdates();
        } catch (error) {
            console.error('Dashboard initialization error:', error);
            showAlert('Failed to initialize dashboard', 'danger');
        }
    }

    // Load summary data
    async loadSummaryData() {
        try {
            const response = await apiRequest('/api/dashboard/summary');
            const data = await response.json();

            // Update summary cards
            this.updateSummaryCard('totalDevices', data.total_devices);
            this.updateSummaryCard('onlineDevices', data.online_devices);
            this.updateSummaryCard('activeAlerts', data.total_alerts);
            this.updateSummaryCard('totalVlans', data.total_vlans);

            // Update device status chart
            this.updateDeviceStatusChart(data);

        } catch (error) {
            console.error('Error loading summary data:', error);
            showAlert('Failed to load dashboard summary', 'warning');
        }
    }

    // Update summary card
    updateSummaryCard(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            // Add loading animation
            setLoading(element);
            
            setTimeout(() => {
                element.textContent = value || '--';
                setLoading(element, false);
            }, 500);
        }
    }

    // Initialize charts
    initializeCharts() {
        this.initializeBandwidthChart();
        this.initializeDeviceStatusChart();
    }

    // Initialize bandwidth chart
    async initializeBandwidthChart() {
        const ctx = document.getElementById('bandwidthChart');
        if (!ctx) return;

        try {
            // Load bandwidth data
            const response = await apiRequest('/api/stats/bandwidth?hours=24');
            const bandwidthData = await response.json();

            // Process data for chart
            const processedData = this.processBandwidthData(bandwidthData);

            this.charts.bandwidth = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: processedData.labels,
                    datasets: [{
                        label: 'Download (RX)',
                        data: processedData.rx,
                        borderColor: 'rgb(54, 185, 204)',
                        backgroundColor: 'rgba(54, 185, 204, 0.1)',
                        fill: true,
                        tension: 0.4
                    }, {
                        label: 'Upload (TX)',
                        data: processedData.tx,
                        borderColor: 'rgb(78, 115, 223)',
                        backgroundColor: 'rgba(78, 115, 223, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: false
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Time'
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Bandwidth (MB/s)'
                            },
                            ticks: {
                                callback: function(value) {
                                    return formatBytes(value * 1024 * 1024, 1);
                                }
                            }
                        }
                    },
                    elements: {
                        point: {
                            radius: 2,
                            hoverRadius: 6
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error initializing bandwidth chart:', error);
        }
    }

    // Initialize device status chart
    initializeDeviceStatusChart() {
        const ctx = document.getElementById('deviceStatusChart');
        if (!ctx) return;

        this.charts.deviceStatus = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Online', 'Offline', 'Unknown'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [
                        'rgb(28, 200, 138)',
                        'rgb(231, 74, 59)',
                        'rgb(133, 135, 150)'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                cutout: '60%'
            }
        });
    }

    // Update device status chart
    updateDeviceStatusChart(data) {
        if (!this.charts.deviceStatus) return;

        const online = data.online_devices || 0;
        const offline = data.offline_devices || 0;
        const unknown = Math.max(0, (data.total_devices || 0) - online - offline);

        this.charts.deviceStatus.data.datasets[0].data = [online, offline, unknown];
        this.charts.deviceStatus.update();
    }

    // Process bandwidth data for chart
    processBandwidthData(rawData) {
        // Group data by hour for the last 24 hours
        const now = new Date();
        const hours = [];
        const rxData = [];
        const txData = [];

        // Generate 24 hours worth of labels
        for (let i = 23; i >= 0; i--) {
            const hour = new Date(now.getTime() - (i * 60 * 60 * 1000));
            hours.push(hour.getHours() + ':00');
        }

        // Initialize with zeros
        for (let i = 0; i < 24; i++) {
            rxData.push(0);
            txData.push(0);
        }

        // Fill with actual data (mock data for demo)
        for (let i = 0; i < 24; i++) {
            rxData[i] = Math.random() * 50 + 10; // 10-60 MB/s
            txData[i] = Math.random() * 20 + 5;  // 5-25 MB/s
        }

        return {
            labels: hours,
            rx: rxData,
            tx: txData
        };
    }

    // Load recent alerts
    async loadRecentAlerts() {
        try {
            const response = await apiRequest('/api/alerts');
            const alerts = await response.json();

            const recentAlertsContainer = document.getElementById('recentAlerts');
            if (!recentAlertsContainer) return;

            // Filter unresolved alerts and take first 5
            const recentAlerts = alerts
                .filter(alert => !alert.resolved)
                .slice(0, 5);

            if (recentAlerts.length === 0) {
                recentAlertsContainer.innerHTML = `
                    <div class="text-center text-muted py-3">
                        <i class="fas fa-check-circle fa-2x mb-2"></i>
                        <p>No active alerts</p>
                    </div>
                `;
                return;
            }

            const alertsHTML = recentAlerts.map(alert => `
                <div class="alert-item ${alert.severity.toLowerCase()}" data-alert-id="${alert.id}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="fw-bold text-capitalize">${alert.alert_type}</div>
                            <div class="small text-muted mb-1">${alert.message}</div>
                            <div class="small">
                                <i class="fas fa-clock me-1"></i>
                                ${formatTimestamp(alert.timestamp)}
                                ${alert.source_ip ? `<span class="ms-2"><i class="fas fa-map-marker-alt me-1"></i>${alert.source_ip}</span>` : ''}
                            </div>
                        </div>
                        <div class="ms-2">
                            <span class="badge bg-${this.getSeverityColor(alert.severity)}">${alert.severity}</span>
                            <button class="btn btn-sm btn-outline-success ms-1" onclick="dashboard.resolveAlert(${alert.id})" title="Resolve">
                                <i class="fas fa-check"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');

            recentAlertsContainer.innerHTML = alertsHTML;

        } catch (error) {
            console.error('Error loading recent alerts:', error);
        }
    }

    // Get severity color
    getSeverityColor(severity) {
        const colors = {
            'critical': 'danger',
            'high': 'warning',
            'medium': 'info',
            'low': 'secondary'
        };
        return colors[severity.toLowerCase()] || 'secondary';
    }

    // Resolve alert
    async resolveAlert(alertId) {
        try {
            const response = await apiRequest(`/api/alerts/${alertId}/resolve`, {
                method: 'PUT'
            });

            if (response.ok) {
                showAlert('Alert resolved successfully', 'success');
                
                // Remove alert from display
                const alertElement = document.querySelector(`[data-alert-id="${alertId}"]`);
                if (alertElement) {
                    alertElement.style.opacity = '0.5';
                    setTimeout(() => alertElement.remove(), 500);
                }

                // Update alert counter
                const alertCounter = document.getElementById('activeAlerts');
                if (alertCounter) {
                    const currentCount = parseInt(alertCounter.textContent) || 0;
                    alertCounter.textContent = Math.max(0, currentCount - 1);
                }
            }
        } catch (error) {
            console.error('Error resolving alert:', error);
            showAlert('Failed to resolve alert', 'danger');
        }
    }

    // Start auto-refresh
    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadSummaryData();
            this.loadRecentAlerts();
            this.updateSystemHealth();
        }, this.refreshRate);
    }

    // Stop auto-refresh
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    // Update system health (mock data)
    updateSystemHealth() {
        const metrics = {
            cpu: Math.random() * 40 + 20,     // 20-60%
            memory: Math.random() * 30 + 40,  // 40-70%
            disk: Math.random() * 20 + 15,    // 15-35%
            network: Math.random() * 40 + 30  // 30-70%
        };

        this.updateProgressBar('cpuUsage', metrics.cpu);
        this.updateProgressBar('memoryUsage', metrics.memory);
        this.updateProgressBar('diskUsage', metrics.disk);
        this.updateProgressBar('networkLoad', metrics.network);

        // Update last updated time
        const lastUpdatedElement = document.getElementById('lastUpdated');
        if (lastUpdatedElement) {
            lastUpdatedElement.textContent = formatTimestamp(new Date());
        }
    }

    // Update progress bar
    updateProgressBar(id, percentage) {
        const progressBar = document.getElementById(id);
        if (!progressBar) return;

        const parentRow = progressBar.closest('.row') || progressBar.closest('.mb-3');
        const valueSpan = parentRow?.querySelector('.small.text-muted:last-child');

        progressBar.style.width = percentage + '%';
        progressBar.setAttribute('aria-valuenow', percentage);

        if (valueSpan) {
            valueSpan.textContent = Math.round(percentage) + '%';
        }

        // Update color based on percentage
        progressBar.className = progressBar.className.replace(/bg-\w+/, '');
        if (percentage < 60) {
            progressBar.classList.add('bg-success');
        } else if (percentage < 80) {
            progressBar.classList.add('bg-warning');
        } else {
            progressBar.classList.add('bg-danger');
        }
    }

    // Setup real-time updates
    setupRealTimeUpdates() {
        // Subscribe to real-time updates
        realTimeUpdater.subscribe('device_status', (data) => {
            this.loadSummaryData(); // Refresh summary when device status changes
        });

        realTimeUpdater.subscribe('new_alert', (data) => {
            this.loadRecentAlerts(); // Refresh alerts when new alert arrives
        });

        realTimeUpdater.subscribe('bandwidth_update', (data) => {
            if (this.charts.bandwidth) {
                this.refreshBandwidthChart();
            }
        });
    }

    // Refresh bandwidth chart
    async refreshBandwidthChart() {
        try {
            const response = await apiRequest('/api/stats/bandwidth?hours=24');
            const bandwidthData = await response.json();
            const processedData = this.processBandwidthData(bandwidthData);

            if (this.charts.bandwidth) {
                this.charts.bandwidth.data.labels = processedData.labels;
                this.charts.bandwidth.data.datasets[0].data = processedData.rx;
                this.charts.bandwidth.data.datasets[1].data = processedData.tx;
                this.charts.bandwidth.update();
            }
        } catch (error) {
            console.error('Error refreshing bandwidth chart:', error);
        }
    }

    // Export chart
    exportChart(chartName = 'bandwidth') {
        if (!this.charts[chartName]) return;

        const link = document.createElement('a');
        link.download = `${chartName}-chart-${new Date().toISOString().split('T')[0]}.png`;
        link.href = this.charts[chartName].toBase64Image();
        link.click();
    }

    // Show network map (placeholder)
    showNetworkMap() {
        showAlert('Network topology view coming soon!', 'info');
    }

    // Load network map (placeholder)
    loadNetworkMap() {
        const preview = document.getElementById('networkPreview');
        if (!preview) return;

        preview.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted">Loading network topology...</p>
            </div>
        `;

        setTimeout(() => {
            preview.innerHTML = `
                <div class="network-topology" style="position: relative; height: 280px;">
                    <div class="network-node node-router" style="top: 50px; left: 50px;" title="Router-01">
                        <i class="fas fa-router"></i>
                    </div>
                    <div class="network-node node-switch" style="top: 150px; left: 200px;" title="Switch-01">
                        <i class="fas fa-network-wired"></i>
                    </div>
                    <div class="network-node node-server" style="top: 50px; left: 350px;" title="Server-01">
                        <i class="fas fa-server"></i>
                    </div>
                    <div class="network-node node-workstation" style="top: 200px; left: 350px;" title="Workstation-01">
                        <i class="fas fa-desktop"></i>
                    </div>
                    <svg style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;">
                        <line x1="110" y1="80" x2="200" y2="180" class="network-connection" />
                        <line x1="260" y1="180" x2="350" y2="80" class="network-connection" />
                        <line x1="260" y1="180" x2="350" y2="230" class="network-connection" />
                    </svg>
                </div>
                <div class="text-center mt-3">
                    <button class="btn btn-primary btn-sm" onclick="dashboard.showNetworkMap()">
                        View Full Topology
                    </button>
                </div>
            `;
        }, 2000);
    }

    // Cleanup
    destroy() {
        this.stopAutoRefresh();
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        
        // Unsubscribe from real-time updates
        realTimeUpdater.unsubscribe('device_status');
        realTimeUpdater.unsubscribe('new_alert');
        realTimeUpdater.unsubscribe('bandwidth_update');
    }
}

// Global dashboard instance
const dashboard = new Dashboard();

// Global functions for template access
window.initializeDashboard = () => dashboard.initialize();
window.refreshBandwidthChart = () => dashboard.refreshBandwidthChart();
window.exportChart = (chartName) => dashboard.exportChart(chartName);
window.showNetworkMap = () => dashboard.showNetworkMap();
window.loadNetworkMap = () => dashboard.loadNetworkMap();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    dashboard.destroy();
});