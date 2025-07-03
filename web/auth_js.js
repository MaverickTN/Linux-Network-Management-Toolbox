// web/static/js/auth.js

class AuthManager {
    constructor() {
        this.token = localStorage.getItem('token');
        this.user = null;
        this.refreshTimer = null;
    }

    // Check if user is authenticated
    isAuthenticated() {
        return !!this.token;
    }

    // Get current user info
    async getCurrentUser() {
        if (!this.token) return null;

        try {
            const response = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (response.ok) {
                this.user = await response.json();
                return this.user;
            } else {
                this.logout();
                return null;
            }
        } catch (error) {
            console.error('Error fetching user info:', error);
            this.logout();
            return null;
        }
    }

    // Login function
    async login(username, password) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.token = data.access_token;
                localStorage.setItem('token', this.token);
                
                // Get user info
                await this.getCurrentUser();
                
                // Start token refresh timer
                this.startTokenRefreshTimer();
                
                return { success: true, user: this.user };
            } else {
                return { success: false, error: data.detail || 'Login failed' };
            }
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: 'Network error. Please try again.' };
        }
    }

    // Logout function
    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('token');
        
        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
            this.refreshTimer = null;
        }
        
        // Redirect to login page
        window.location.href = '/login';
    }

    // Make authenticated API request
    async apiRequest(url, options = {}) {
        if (!this.token) {
            throw new Error('Not authenticated');
        }

        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.token}`,
            ...options.headers
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            if (response.status === 401) {
                this.logout();
                throw new Error('Session expired');
            }

            return response;
        } catch (error) {
            if (error.message === 'Session expired') {
                throw error;
            }
            console.error('API request error:', error);
            throw error;
        }
    }

    // Check user role/permissions
    hasRole(requiredRole) {
        if (!this.user) return false;

        const roleHierarchy = {
            'guest': 0,
            'user': 1,
            'admin': 2
        };

        const userLevel = roleHierarchy[this.user.role] || 0;
        const requiredLevel = roleHierarchy[requiredRole] || 2;

        return userLevel >= requiredLevel;
    }

    // Start token refresh timer (refresh before expiry)
    startTokenRefreshTimer() {
        // Refresh token every 25 minutes (token expires in 30 minutes)
        this.refreshTimer = setTimeout(async () => {
            try {
                // In a real implementation, you'd have a refresh token endpoint
                // For now, we'll just check if the current token is still valid
                await this.getCurrentUser();
                this.startTokenRefreshTimer(); // Schedule next refresh
            } catch (error) {
                console.error('Token refresh failed:', error);
                this.logout();
            }
        }, 25 * 60 * 1000); // 25 minutes
    }

    // Update UI based on authentication state
    updateUI() {
        const usernameSpan = document.getElementById('username');
        
        if (this.user) {
            if (usernameSpan) {
                usernameSpan.textContent = this.user.username;
            }
            
            // Show/hide elements based on role
            this.updateRoleBasedUI();
        } else {
            if (usernameSpan) {
                usernameSpan.textContent = 'Guest';
            }
        }
    }

    // Update UI elements based on user role
    updateRoleBasedUI() {
        if (!this.user) return;

        // Hide admin-only elements for non-admin users
        const adminElements = document.querySelectorAll('[data-role="admin"]');
        adminElements.forEach(element => {
            if (this.hasRole('admin')) {
                element.style.display = '';
            } else {
                element.style.display = 'none';
            }
        });

        // Hide user-level elements for guests
        const userElements = document.querySelectorAll('[data-role="user"]');
        userElements.forEach(element => {
            if (this.hasRole('user')) {
                element.style.display = '';
            } else {
                element.style.display = 'none';
            }
        });

        // Add role badge
        const userInfo = document.querySelector('.dropdown-toggle');
        if (userInfo && !userInfo.querySelector('.role-badge')) {
            const roleBadge = document.createElement('span');
            roleBadge.className = `badge bg-${this.user.role === 'admin' ? 'danger' : 'primary'} ms-1 role-badge`;
            roleBadge.textContent = this.user.role.toUpperCase();
            userInfo.appendChild(roleBadge);
        }
    }
}

// Global auth manager instance
const authManager = new AuthManager();

// Global functions for easy access
window.login = async function(username, password) {
    return await authManager.login(username, password);
};

window.logout = function() {
    authManager.logout();
};

window.checkAuth = async function() {
    const currentPath = window.location.pathname;
    
    // Don't check auth on login page
    if (currentPath === '/login') {
        return;
    }
    
    if (!authManager.isAuthenticated()) {
        window.location.href = '/login';
        return;
    }
    
    // Verify token and get user info
    const user = await authManager.getCurrentUser();
    if (!user) {
        window.location.href = '/login';
        return;
    }
    
    // Update UI
    authManager.updateUI();
    
    // Start token refresh timer if not already started
    if (!authManager.refreshTimer) {
        authManager.startTokenRefreshTimer();
    }
};

window.apiRequest = async function(url, options = {}) {
    return await authManager.apiRequest(url, options);
};

window.hasRole = function(role) {
    return authManager.hasRole(role);
};

window.getCurrentUser = function() {
    return authManager.user;
};

// Show profile modal
window.showProfile = async function() {
    const user = authManager.user;
    if (!user) return;

    const profileContent = document.getElementById('profileContent');
    profileContent.innerHTML = `
        <div class="row">
            <div class="col-md-4 text-center">
                <i class="fas fa-user-circle fa-5x text-muted mb-3"></i>
                <h5>${user.username}</h5>
                <span class="badge bg-${user.role === 'admin' ? 'danger' : 'primary'}">${user.role.toUpperCase()}</span>
            </div>
            <div class="col-md-8">
                <table class="table table-borderless">
                    <tr>
                        <td><strong>Username:</strong></td>
                        <td>${user.username}</td>
                    </tr>
                    <tr>
                        <td><strong>Email:</strong></td>
                        <td>${user.email}</td>
                    </tr>
                    <tr>
                        <td><strong>Role:</strong></td>
                        <td>${user.role}</td>
                    </tr>
                    <tr>
                        <td><strong>Status:</strong></td>
                        <td>
                            <span class="badge bg-${user.is_active ? 'success' : 'danger'}">
                                ${user.is_active ? 'Active' : 'Inactive'}
                            </span>
                        </td>
                    </tr>
                </table>
            </div>
        </div>
    `;

    const modal = new bootstrap.Modal(document.getElementById('profileModal'));
    modal.show();
};