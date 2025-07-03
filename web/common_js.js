// web/static/js/common.js

// Utility functions for the LNMT dashboard

// Show alert message
function showAlert(message, type = 'info', duration = 5000) {
    const alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) return;

    const alertId = 'alert-' + Date.now();
    const iconMap = {
        success: 'check-circle',
        danger: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle',
        primary: 'info-circle'
    };

    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-${iconMap[type] || 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    alertContainer.insertAdjacentHTML('beforeend', alertHTML);

    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                bsAlert.close();
            }
        }, duration);
    }
}

// Format timestamp
function formatTimestamp(timestamp, format = 'relative') {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (format === 'relative') {
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (seconds < 60) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 7) return `${days}d ago`;
        return date.toLocaleDateString();
    } else if (format === 'full') {
        return date.toLocaleString();
    } else if (format === 'date') {
        return date.toLocaleDateString();
    } else if (format === 'time') {
        return date.toLocaleTimeString();
    }

    return date.toISOString();
}

// Format bytes
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// Format percentage
function formatPercentage(value, total, decimals = 1) {
    if (total === 0) return '0%';
    const percentage = (value / total) * 100;
    return percentage.toFixed(decimals) + '%';
}

// Debounce function
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

// Loading state management
function setLoading(element, isLoading = true) {
    if (typeof element === 'string') {
        element = document.getElementById(element);
    }
    
    if (!element) return;

    if (isLoading) {
        element.classList.add('loading');
        element.setAttribute('data-original-content', element.innerHTML);
    } else {
        element.classList.remove('loading');
        const originalContent = element.getAttribute('data-original-content');
        if (originalContent) {
            element.innerHTML = originalContent;
            element.removeAttribute('data-original-content');
        }
    }
}

// Confirm dialog
function confirmAction(message, title = 'Confirm Action') {
    return new Promise((resolve) => {
        const modalId = 'confirmModal-' + Date.now();
        const modalHTML = `
            <div class="modal fade" id="${modalId}" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>${message}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-danger" id="confirmBtn">Confirm</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        const modal = new bootstrap.Modal(document.getElementById(modalId));
        
        document.getElementById('confirmBtn').onclick = () => {
            modal.hide();
            resolve(true);
        };

        document.getElementById(modalId).addEventListener('hidden.bs.modal', () => {
            document.getElementById(modalId).remove();
            resolve(false);
        });

        modal.show();
    });
}

// Generic form handler
function handleForm(formId, submitUrl, options = {}) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // Apply any data transformations
        if (options.transform) {
            Object.assign(data, options.transform(data));
        }

        try {
            setLoading(options.submitButton || form.querySelector('button[type="submit"]'));

            const response = await apiRequest(submitUrl, {
                method: options.method || 'POST',
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                showAlert(result.message || 'Operation completed successfully', 'success');
                
                if (options.onSuccess) {
                    options.onSuccess(result);
                }
                
                if (options.resetForm !== false) {
                    form.reset();
                }
                
                if (options.closeModal) {
                    const modal = bootstrap.Modal.getInstance(document.getElementById(options.closeModal));
                    if (modal) modal.hide();
                }
                
                if (options.reload) {
                    setTimeout(() => window.location.reload(), 1000);
                }
            } else {
                showAlert(result.detail || 'Operation failed', 'danger');
                
                if (options.onError) {
                    options.onError(result);
                }
            }
        } catch (error) {
            console.error('Form submission error:', error);
            showAlert('Network error. Please try again.', 'danger');
        } finally {
            setLoading(options.submitButton || form.querySelector('button[type="submit"]'), false);
        }
    });
}

// DataTable utilities
function initializeDataTable(tableId, options = {}) {
    const defaultOptions = {
        responsive: true,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100], [10, 25, 50, 100]],
        language: {
            search: "Search:",
            lengthMenu: "Show _MENU_ entries",
            info: "Showing _START_ to _END_ of _TOTAL_ entries",
            paginate: {
                first: "First",
                last: "Last",
                next: "Next",
                previous: "Previous"
            }
        },
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>t<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        ...options
    };

    return $('#' + tableId).DataTable(defaultOptions);
}

// Real-time updates using WebSocket
class RealTimeUpdater {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.subscribers = new Map();
    }

    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('WebSocket message parse error:', error);
                }
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus(false);
                this.scheduleReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.scheduleReconnect();
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
            setTimeout(() => this.connect(), delay);
        } else {
            console.error('Max reconnection attempts reached');
            showAlert('Real-time updates disconnected. Please refresh the page.', 'warning', 0);
        }
    }

    handleMessage(data) {
        // Notify subscribers
        this.subscribers.forEach((callback, type) => {
            if (data.type === type || type === '*') {
                callback(data);
            }
        });

        // Handle common message types
        switch (data.type) {
            case 'health_update':
                this.updateLastSeen();
                break;
            case 'device_status':
                this.updateDeviceStatus(data.data);
                break;
            case 'new_alert':
                this.handleNewAlert(data.data);
                break;
        }
    }

    subscribe(messageType, callback) {
        this.subscribers.set(messageType, callback);
    }

    unsubscribe(messageType) {
        this.subscribers.delete(messageType);
    }

    updateConnectionStatus(connected) {
        const indicators = document.querySelectorAll('.real-time-indicator');
        indicators.forEach(indicator => {
            if (connected) {
                indicator.style.backgroundColor = 'var(--success-color)';
                indicator.title = 'Real-time updates active';
            } else {
                indicator.style.backgroundColor = 'var(--danger-color)';
                indicator.title = 'Real-time updates disconnected';
            }
        });
    }

    updateLastSeen() {
        const elements = document.querySelectorAll('[data-last-updated]');
        elements.forEach(element => {
            element.textContent = formatTimestamp(new Date());
        });
    }

    updateDeviceStatus(deviceData) {
        // Update device status in tables or lists
        const deviceRows = document.querySelectorAll(`[data-device-id="${deviceData.id}"]`);
        deviceRows.forEach(row => {
            const statusCell = row.querySelector('.device-status');
            if (statusCell) {
                statusCell.className = `device-status ${deviceData.status}`;
            }
        });
    }

    handleNewAlert(alertData) {
        // Show notification for new alerts
        showAlert(`New ${alertData.severity} alert: ${alertData.message}`, 'warning');
        
        // Update alert counters
        const alertCounter = document.getElementById('activeAlerts');
        if (alertCounter) {
            const currentCount = parseInt(alertCounter.textContent) || 0;
            alertCounter.textContent = currentCount + 1;
        }
    }
}

// Global real-time updater instance
const realTimeUpdater = new RealTimeUpdater();

// Auto-connect WebSocket when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Connect WebSocket after authentication is verified
    setTimeout(() => {
        if (getCurrentUser()) {
            realTimeUpdater.connect();
        }
    }, 1000);
});

// Disconnect WebSocket when page unloads
window.addEventListener('beforeunload', () => {
    realTimeUpdater.disconnect();
});

// Export utilities for global use
window.showAlert = showAlert;
window.formatTimestamp = formatTimestamp;
window.formatBytes = formatBytes;
window.formatPercentage = formatPercentage;
window.debounce = debounce;
window.setLoading = setLoading;
window.confirmAction = confirmAction;
window.handleForm = handleForm;
window.initializeDataTable = initializeDataTable;
window.realTimeUpdater = realTimeUpdater;