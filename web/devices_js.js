// web/static/js/devices.js

class DevicesManager {
    constructor() {
        this.dataTable = null;
        this.devices = [];
        this.vlans = [];
    }

    // Initialize devices page
    async initialize() {
        try {
            await this.loadVLANs();
            await this.loadDevices();
            this.initializeDataTable();
            this.setupEventHandlers();
            this.setupRealTimeUpdates();
        } catch (error) {
            console.error('Devices page initialization error:', error);
            showAlert('Failed to initialize devices page', 'danger');
        }
    }

    // Load devices data
    async loadDevices() {
        try {
            const response = await apiRequest('/api/devices');
            this.devices = await response.json();
            this.updateDeviceStatistics();
            return this.devices;
        } catch (error) {
            console.error('Error loading devices:', error);
            showAlert('Failed to load devices', 'danger');
            return [];
        }
    }

    // Load VLANs for dropdowns
    async loadVLANs() {
        try {
            const response = await apiRequest('/api/vlans');
            this.vlans = await response.json();
            this.populateVLANDropdowns();
        } catch (error) {
            console.error('Error loading VLANs:', error);
        }
    }

    // Populate VLAN dropdowns
    populateVLANDropdowns() {
        const vlanSelects = ['filterVlan', 'vlan_id', 'edit_vlan_id'];
        
        vlanSelects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (!select) return;

            // Clear existing options (except first one for filters)
            const startIndex = selectId === 'filterVlan' ? 1 : 1;
            while (select.children.length > startIndex) {
                select.removeChild(select.lastChild);
            }

            // Add VLAN options
            this.vlans.forEach(vlan => {
                const option = document.createElement('option');
                option.value = vlan.vlan_id;
                option.textContent = `VLAN ${vlan.vlan_id} - ${vlan.name}`;
                select.appendChild(option);
            });
        });
    }

    // Update device statistics
    updateDeviceStatistics() {
        const stats = this.calculateDeviceStats();
        
        document.getElementById('totalDevicesCount').textContent = stats.total;
        document.getElementById('onlineDevicesCount').textContent = stats.online;
        document.getElementById('offlineDevicesCount').textContent = stats.offline;
        document.getElementById('unknownDevicesCount').textContent = stats.unknown;
    }

    // Calculate device statistics
    calculateDeviceStats() {
        const stats = {
            total: this.devices.length,
            online: 0,
            offline: 0,
            unknown: 0
        };

        this.devices.forEach(device => {
            switch (device.status) {
                case 'online':
                    stats.online++;
                    break;
                case 'offline':
                    stats.offline++;
                    break;
                default:
                    stats.unknown++;
            }
        });

        return stats;
    }

    // Initialize DataTable
    initializeDataTable() {
        if (this.dataTable) {
            this.dataTable.destroy();
        }

        this.dataTable = initializeDataTable('devicesTable', {
            data: this.devices,
            columns: [
                {
                    data: 'status',
                    render: (data) => this.renderDeviceStatus(data)
                },
                { data: 'hostname' },
                { data: 'ip_address' },
                { data: 'mac_address' },
                {
                    data: 'device_type',
                    render: (data) => this.renderDeviceType(data)
                },
                {
                    data: 'vlan_id',
                    render: (data) => this.renderVLAN(data)
                },
                {
                    data: 'last_seen',
                    render: (data) => data ? formatTimestamp(data) : 'Never'
                },
                {
                    data: null,
                    orderable: false,
                    render: (data, type, row) => this.renderDeviceActions(row)
                }
            ],
            order: [[1, 'asc']], // Sort by hostname
            rowCallback: (row, data) => {
                // Add data attributes for filtering
                row.setAttribute('data-device-id', data.id);
                row.setAttribute('data-status', data.status);
                row.setAttribute('data-type', data.device_type);
                row.setAttribute('data-vlan', data.vlan_id || '');
            }
        });
    }

    // Render device status
    renderDeviceStatus(status) {
        const statusMap = {
            online: { class: 'online', icon: 'check-circle', text: 'Online' },
            offline: { class: 'offline', icon: 'times-circle', text: 'Offline' },
            unknown: { class: 'unknown', icon: 'question-circle', text: 'Unknown' }
        };

        const statusInfo = statusMap[status] || statusMap.unknown;
        
        return `
            <span class="d-flex align-items-center">
                <span class="device-status ${statusInfo.class}"></span>
                <i class="fas fa-${statusInfo.icon} me-1"></i>
                ${statusInfo.text}
            </span>
        `;
    }

    // Render device type
    renderDeviceType(type) {
        const typeMap = {
            router: { icon: 'route', color: 'primary' },
            switch: { icon: 'network-wired', color: 'success' },
            server: { icon: 'server', color: 'warning' },
            workstation: { icon: 'desktop', color: 'info' },
            printer: { icon: 'print', color: 'secondary' },
            other: { icon: 'question', color: 'secondary' }
        };

        const typeInfo = typeMap[type] || typeMap.other;
        
        return `
            <span class="badge bg-${typeInfo.color}">
                <i class="fas fa-${typeInfo.icon} me-1"></i>
                ${type.charAt(0).toUpperCase() + type.slice(1)}
            </span>
        `;
    }

    // Render VLAN
    renderVLAN(vlanId) {
        if (!vlanId) return '<span class="text-muted">None</span>';
        
        const vlan = this.vlans.find(v => v.vlan_id === vlanId);
        const vlanName = vlan ? vlan.name : 'Unknown';
        
        return `<span class="badge bg-outline-primary">VLAN ${vlanId} - ${vlanName}</span>`;
    }

    // Render device actions
    renderDeviceActions(device) {
        const currentUser = getCurrentUser();
        if (!currentUser || !hasRole('user')) {
            return '<span class="text-muted">No access</span>';
        }

        return `
            <div class="btn-group" role="group">
                <button class="btn btn-sm btn-outline-primary" onclick="devicesManager.showDeviceDetails(${device.id})" title="View Details">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-secondary" onclick="devicesManager.editDevice(${device.id})" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="devicesManager.deleteDevice(${device.id})" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
    }

    // Setup event handlers
    setupEventHandlers() {
        // Add device form
        handleForm('addDeviceForm', '/api/devices', {
            onSuccess: (result) => {
                this.refreshDevices();
                const modal = bootstrap.Modal.getInstance(document.getElementById('addDeviceModal'));
                modal.hide();
            },
            closeModal: 'addDeviceModal'
        });

        // Edit device form
        handleForm('editDeviceForm', '/api/devices', {
            method: 'PUT',
            transform: (data) => ({
                ...data,
                id: data.device_id
            }),
            onSuccess: () => {
                this.refreshDevices();
                const modal = bootstrap.Modal.getInstance(document.getElementById('editDeviceModal'));
                modal.hide();
            }
        });
    }

    // Setup real-time updates
    setupRealTimeUpdates() {
        realTimeUpdater.subscribe('device_status', (data) => {
            this.handleDeviceStatusUpdate(data.data);
        });

        realTimeUpdater.subscribe('device_added', (data) => {
            this.refreshDevices();
        });

        realTimeUpdater.subscribe('device_removed', (data) => {
            this.refreshDevices();
        });
    }

    // Handle device status update
    handleDeviceStatusUpdate(deviceData) {
        // Update local data
        const deviceIndex = this.devices.findIndex(d => d.id === deviceData.id);
        if (deviceIndex !== -1) {
            this.devices[deviceIndex].status = deviceData.status;
            this.devices[deviceIndex].last_seen = deviceData.last_seen;
            
            // Update statistics
            this.updateDeviceStatistics();
            
            // Update table row
            this.dataTable.row(`[data-device-id="${deviceData.id}"]`).data(this.devices[deviceIndex]).draw();
        }
    }

    // Show device details
    async showDeviceDetails(deviceId) {
        const device = this.devices.find(d => d.id === deviceId);
        if (!device) return;

        const vlan = this.vlans.find(v => v.vlan_id === device.vlan_id);
        
        const detailsHTML = `
            <div class="row">
                <div class="col-md-6">
                    <table class="table table-borderless">
                        <tr>
                            <td><strong>Hostname:</strong></td>
                            <td>${device.hostname}</td>
                        </tr>
                        <tr>
                            <td><strong>IP Address:</strong></td>
                            <td>${device.ip_address}</td>
                        </tr>
                        <tr>
                            <td><strong>MAC Address:</strong></td>
                            <td>${device.mac_address}</td>
                        </tr>
                        <tr>
                            <td><strong>Device Type:</strong></td>
                            <td>${this.renderDeviceType(device.device_type)}</td>
                        </tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <table class="table table-borderless">
                        <tr>
                            <td><strong>Status:</strong></td>
                            <td>${this.renderDeviceStatus(device.status)}</td>
                        </tr>
                        <tr>
                            <td><strong>VLAN:</strong></td>
                            <td>${device.vlan_id ? `VLAN ${device.vlan_id}${vlan ? ` - ${vlan.name}` : ''}` : 'None'}</td>
                        </tr>
                        <tr>
                            <td><strong>Last Seen:</strong></td>
                            <td>${device.last_seen ? formatTimestamp(device.last_seen, 'full') : 'Never'}</td>
                        </tr>
                        <tr>
                            <td><strong>Device ID:</strong></td>
                            <td>${device.id}</td>
                        </tr>
                    </table>
                </div>
            </div>
            
            <hr>
            
            <div class="row">
                <div class="col-12">
                    <h6>Additional Information</h6>
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        This device was ${device.status === 'online' ? 'last seen' : 'first detected'} 
                        ${device.last_seen ? formatTimestamp(device.last_seen) : 'at an unknown time'}.
                        ${vlan ? `It is assigned to ${vlan.name} (${vlan.subnet}).` : 'It is not assigned to any VLAN.'}
                    </div>
                </div>
            </div>
        `;

        document.getElementById('deviceDetailsContent').innerHTML = detailsHTML;
        const modal = new bootstrap.Modal(document.getElementById('deviceDetailsModal'));
        modal.show();
    }

    // Edit device
    editDevice(deviceId) {
        const device = this.devices.find(d => d.id === deviceId);
        if (!device) return;

        // Populate form fields
        document.getElementById('edit_device_id').value = device.id;
        document.getElementById('edit_hostname').value = device.hostname;
        document.getElementById('edit_ip_address').value = device.ip_address;
        document.getElementById('edit_mac_address').value = device.mac_address;
        document.getElementById('edit_device_type').value = device.device_type;
        document.getElementById('edit_vlan_id').value = device.vlan_id || '';

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('editDeviceModal'));
        modal.show();
    }

    // Delete device
    async deleteDevice(deviceId) {
        const device = this.devices.find(d => d.id === deviceId);
        if (!device) return;

        const confirmed = await confirmAction(
            `Are you sure you want to delete device "${device.hostname}"? This action cannot be undone.`,
            'Delete Device'
        );

        if (!confirmed) return;

        try {
            const response = await apiRequest(`/api/devices/${deviceId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                showAlert('Device deleted successfully', 'success');
                this.refreshDevices();
            } else {
                const error = await response.json();
                showAlert(error.detail || 'Failed to delete device', 'danger');
            }
        } catch (error) {
            console.error('Error deleting device:', error);
            showAlert('Network error. Please try again.', 'danger');
        }
    }

    // Apply filters
    applyFilters() {
        const statusFilter = document.getElementById('filterStatus').value;
        const typeFilter = document.getElementById('filterType').value;
        const vlanFilter = document.getElementById('filterVlan').value;

        // Apply DataTable column filters
        this.dataTable
            .column(0).search(statusFilter)
            .column(4).search(typeFilter)
            .column(5).search(vlanFilter)
            .draw();
    }

    // Clear filters
    clearFilters() {
        document.getElementById('filterStatus').value = '';
        document.getElementById('filterType').value = '';
        document.getElementById('filterVlan').value = '';
        
        this.dataTable.search('').columns().search('').draw();
    }

    // Refresh devices
    async refreshDevices() {
        setLoading('devicesTable');
        try {
            await this.loadDevices();
            this.dataTable.clear().rows.add(this.devices).draw();
        } catch (error) {
            console.error('Error refreshing devices:', error);
        } finally {
            setLoading('devicesTable', false);
        }
    }

    // Cleanup
    destroy() {
        if (this.dataTable) {
            this.dataTable.destroy();
        }
        
        realTimeUpdater.unsubscribe('device_status');
        realTimeUpdater.unsubscribe('device_added');
        realTimeUpdater.unsubscribe('device_removed');
    }
}

// Global devices manager instance
const devicesManager = new DevicesManager();

// Global functions
window.initializeDevicesPage = () => devicesManager.initialize();
window.refreshDevices = () => devicesManager.refreshDevices();
window.applyFilters = () => devicesManager.applyFilters();
window.clearFilters = () => devicesManager.clearFilters();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    devicesManager.destroy();
});