// ZK Attendance System - Simple App JS

// Main app object
const app = {
    // Current page
    currentPage: 'dashboard',
    
    // Device connection status
    isConnected: false,
    
    // Initialize the application
    init: function() {
        console.log('Initializing ZK Attendance System...');
        
        // Set up navigation
        this.setupNavigation();
        
        // Load the initial page (from hash or default to dashboard)
        this.loadPageFromHash();
        
        // Check device connection status
        this.checkConnectionStatus();
    },
    
    // Set up navigation
    setupNavigation: function() {
        console.log('Setting up navigation...');
        
        // Handle navigation clicks
        const navLinks = document.querySelectorAll('[data-page]');
        console.log(`Found ${navLinks.length} navigation links`);
        
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.getAttribute('data-page');
                console.log(`Navigation link clicked: ${page}`);
                this.loadPage(page);
                history.pushState(null, null, `#${page}`);
            });
            console.log(`Added event listener to ${link.textContent.trim()} link`);
        });
        
        // Handle browser back/forward
        window.addEventListener('popstate', () => {
            this.loadPageFromHash();
        });
        
        // Brand link goes to dashboard
        const brandLink = document.getElementById('brand-link');
        if (brandLink) {
            brandLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.loadPage('dashboard');
                history.pushState(null, null, '#dashboard');
            });
            console.log('Added event listener to brand link');
        }
    },
    
    // Load page from URL hash
    loadPageFromHash: function() {
        const hash = window.location.hash.substring(1) || 'dashboard';
        this.loadPage(hash);
    },
    
    // Load a specific page
    loadPage: function(page) {
        console.log(`Loading page: ${page}`);
        
        // Update current page
        this.currentPage = page;
        
        // Update active navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        const activeLink = document.querySelector(`.nav-link[data-page="${page}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }
        
        // Get the page template
        const template = document.getElementById(`${page}-template`);
        if (!template) {
            this.showNotification('Page not found', 'error');
            return;
        }
        
        // Load the template content
        const pageContainer = document.getElementById('page-container');
        pageContainer.innerHTML = '';
        pageContainer.appendChild(document.importNode(template.content, true));
        
        // Initialize page-specific functionality
        this.initPageFunctions(page);
    },
    
    // Show notification
    showNotification: function(message, type = 'info') {
        const container = document.getElementById('notification-container');
        if (!container) return;
        
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        container.appendChild(notification);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    },
    
    // Check connection status
    checkConnectionStatus: function() {
        console.log('Checking device connection status...');
        fetch('/api/device-info')
            .then(response => response.json())
            .then(data => {
                console.log('Device info response:', data);
                this.isConnected = (data.status === 'success');
                if (data.device_info) {
                    console.log('Device connected:', data.device_info.ip);
                }
                this.updateConnectionStatus();
            })
            .catch(error => {
                console.error('Error checking connection status:', error);
                this.isConnected = false;
                this.updateConnectionStatus();
            });
    },
    
    // Update connection status UI
    updateConnectionStatus: function() {
        const statusContainer = document.getElementById('connection-status-container');
        const statusElement = document.querySelector('.connection-status');
        
        if (statusContainer && statusElement) {
            if (this.isConnected) {
                statusElement.className = 'connection-status connected';
                statusElement.innerHTML = '<i class="bi bi-check-circle"></i> Connected';
            } else {
                statusElement.className = 'connection-status disconnected';
                statusElement.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Not Connected';
            }
        }
        
        // Update dashboard if we're on that page
        if (this.currentPage === 'dashboard') {
            const deviceStatus = document.getElementById('device-status');
            const deviceStatusIcon = document.getElementById('device-status-icon');
            const deviceAlert = document.getElementById('device-alert');
            const deviceInfoCard = document.getElementById('device-info-card');
            
            if (deviceStatus && deviceStatusIcon) {
                if (this.isConnected) {
                    deviceStatus.textContent = 'Connected';
                    deviceStatusIcon.className = 'icon text-success';
                    deviceStatusIcon.innerHTML = '<i class="bi bi-hdd-network-fill"></i>';
                    if (deviceAlert) deviceAlert.classList.add('d-none');
                    if (deviceInfoCard) deviceInfoCard.classList.remove('d-none');
                } else {
                    deviceStatus.textContent = 'Not Connected';
                    deviceStatusIcon.className = 'icon text-danger';
                    deviceStatusIcon.innerHTML = '<i class="bi bi-hdd-network"></i>';
                    if (deviceAlert) deviceAlert.classList.remove('d-none');
                    if (deviceInfoCard) deviceInfoCard.classList.add('d-none');
                }
            }
        }
        
        // Update API Send page connection badge if we're on that page
        if (this.currentPage === 'api-send') {
            const connectionBadge = document.getElementById('connection-badge');
            if (connectionBadge) {
                if (this.isConnected) {
                    connectionBadge.textContent = 'Connected';
                    connectionBadge.className = 'badge bg-success';
                } else {
                    connectionBadge.textContent = 'Not Connected';
                    connectionBadge.className = 'badge bg-danger';
                }
            }
        }
    },
    
    // Initialize page-specific functions
    initPageFunctions: function(page) {
        switch(page) {
            case 'dashboard':
                this.initDashboard();
                break;
            case 'connect':
                this.initConnectPage();
                break;
            case 'api-send':
                this.initApiSendPage();
                break;
            case 'settings':
                this.initSettingsPage();
                break;
        }
    },
    
    // Initialize dashboard page
    initDashboard: function() {
        // Check if device is connected
        this.checkConnectionStatus();
        
        // Load dashboard data
        this.loadDashboardStats();
        this.loadDeviceInfo();
        this.loadRecentActivity();
        
        // Set up refresh buttons
        const refreshDeviceBtn = document.getElementById('refresh-device');
        if (refreshDeviceBtn) {
            refreshDeviceBtn.addEventListener('click', () => {
                this.loadDeviceInfo();
            });
        }
        
        const refreshActivityBtn = document.getElementById('refresh-activity');
        if (refreshActivityBtn) {
            refreshActivityBtn.addEventListener('click', () => {
                this.loadRecentActivity();
            });
        }
    },
    
    // Load dashboard stats
    loadDashboardStats: function() {
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Update today's attendance count
                    const todayAttendance = document.getElementById('today-attendance');
                    if (todayAttendance) {
                        todayAttendance.textContent = data.data.today_attendance;
                    }
                    
                    // Update last sync time if available
                    if (data.data.last_sync) {
                        const lastSyncTime = document.getElementById('last-sync-time');
                        if (lastSyncTime) {
                            lastSyncTime.textContent = new Date(data.data.last_sync).toLocaleString();
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error loading stats:', error);
            });
    },
    
    // Load device info
    loadDeviceInfo: function() {
        const deviceIpDisplay = document.getElementById('device-ip-display');
        const devicePortDisplay = document.getElementById('device-port-display');
        const deviceSerial = document.getElementById('device-serial');
        
        if (!deviceIpDisplay && !deviceSerial) return;
        
        fetch('/api/device-info')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const deviceInfo = data.device_info || {};
                    
                    if (deviceIpDisplay) deviceIpDisplay.textContent = deviceInfo.ip || '-';
                    if (devicePortDisplay) devicePortDisplay.textContent = deviceInfo.port || '-';
                    if (deviceSerial) deviceSerial.textContent = deviceInfo.serial_number || '-';
                    
                    // Update last sync time
                    const lastSyncTime = document.getElementById('last-sync-time');
                    if (lastSyncTime && deviceInfo.last_sync) {
                        lastSyncTime.textContent = new Date(deviceInfo.last_sync).toLocaleString();
                    }
                }
            })
            .catch(error => {
                console.error('Error loading device info:', error);
            });
    },
    
    // Load recent activity
    loadRecentActivity: function() {
        const activityTable = document.getElementById('activity-table');
        const loadingIndicator = document.getElementById('activity-loading');
        const noActivity = document.getElementById('no-activity');
        
        if (!activityTable || !loadingIndicator || !noActivity) return;
        
        // Clear previous data
        activityTable.innerHTML = '';
        
        // Show loading indicator
        loadingIndicator.classList.remove('d-none');
        noActivity.classList.add('d-none');
        
        fetch('/api/attendance')
            .then(response => response.json())
            .then(data => {
                loadingIndicator.classList.add('d-none');
                
                if (data.status === 'success') {
                    const records = data.attendance || [];
                    
                    if (records.length === 0) {
                        noActivity.classList.remove('d-none');
                        return;
                    }
                    
                    // Sort records by timestamp (newest first)
                    const sortedRecords = [...records].sort((a, b) => {
                        return new Date(b.timestamp) - new Date(a.timestamp);
                    });
                    
                    // Display only the most recent 10 records
                    const recentRecords = sortedRecords.slice(0, 10);
                    
                    recentRecords.forEach(record => {
                        const row = document.createElement('tr');
                        
                        // User ID
                        const userIdCell = document.createElement('td');
                        userIdCell.textContent = record.user_id;
                        row.appendChild(userIdCell);
                        
                        // Name
                        const nameCell = document.createElement('td');
                        nameCell.textContent = record.name || 'Unknown';
                        row.appendChild(nameCell);
                        
                        // Date & Time
                        const timeCell = document.createElement('td');
                        const time = new Date(record.timestamp);
                        timeCell.textContent = time.toLocaleString();
                        row.appendChild(timeCell);
                        
                        // Punch Type
                        const typeCell = document.createElement('td');
                        const punchValue = record.punch || record.punch_type;
                        let badgeClass = 'bg-secondary';
                        let punchText = 'Unknown';
                        
                        if (punchValue === 0 || punchValue === '0') {
                            badgeClass = 'bg-success';
                            punchText = 'Check In';
                        } else if (punchValue === 1 || punchValue === '1') {
                            badgeClass = 'bg-danger';
                            punchText = 'Check Out';
                        }
                        
                        typeCell.innerHTML = `<span class="badge ${badgeClass}">${punchText}</span>`;
                        row.appendChild(typeCell);
                        
                        activityTable.appendChild(row);
                    });
                } else {
                    noActivity.classList.remove('d-none');
                }
            })
            .catch(error => {
                console.error('Error loading recent activity:', error);
                loadingIndicator.classList.add('d-none');
                noActivity.classList.remove('d-none');
                
                if (noActivity) {
                    noActivity.innerHTML = `
                        <i class="bi bi-exclamation-triangle text-danger fs-1"></i>
                        <p class="mt-2">Error loading activity: ${error.message}</p>
                        <button class="btn btn-sm btn-primary mt-2" onclick="app.loadRecentActivity()">
                            <i class="bi bi-arrow-clockwise"></i> Retry
                        </button>
                    `;
                }
            });
    },
    
    // Initialize connect page
    initConnectPage: function() {
        const connectForm = document.getElementById('connect-form');
        if (!connectForm) return;
        
        connectForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const ipAddress = document.getElementById('device-ip').value;
            const port = document.getElementById('device-port').value;
            const timeout = document.getElementById('device-timeout').value;
            
            if (!ipAddress) {
                this.showNotification('Please enter an IP address', 'warning');
                return;
            }
            
            // Show loading state
            const connectButton = connectForm.querySelector('button[type="submit"]');
            const originalButtonText = connectButton.innerHTML;
            connectButton.disabled = true;
            connectButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Connecting...';
            
            // Connect to device
            fetch('/api/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ip: ipAddress,
                    port: port,
                    timeout: timeout
                })
            })
            .then(response => response.json())
            .then(data => {
                // Reset button
                connectButton.disabled = false;
                connectButton.innerHTML = originalButtonText;
                
                // Handle response
                if (data.status === 'success') {
                    this.showNotification('Successfully connected to device!', 'success');
                    this.isConnected = true;
                    this.updateConnectionStatus();
                    
                    // Redirect to dashboard after a short delay
                    setTimeout(() => {
                        this.loadPage('dashboard');
                        history.pushState(null, null, '#dashboard');
                    }, 1500);
                } else {
                    this.showNotification(`Connection failed: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                // Reset button
                connectButton.disabled = false;
                connectButton.innerHTML = originalButtonText;
                
                this.showNotification(`Error connecting to device: ${error.message}`, 'danger');
            });
        });
    },
    
    // Initialize API Send page
    initApiSendPage: function() {
        // Check connection status
        this.checkConnectionStatus();
        
        // Set up date range inputs
        const startDateInput = document.getElementById('start-date');
        const endDateInput = document.getElementById('end-date');
        
        if (startDateInput && endDateInput) {
            // Set default dates (last 7 days)
            const today = new Date();
            const lastWeek = new Date();
            lastWeek.setDate(today.getDate() - 7);
            
            startDateInput.valueAsDate = lastWeek;
            endDateInput.valueAsDate = today;
            
            // Load preview when dates change
            startDateInput.addEventListener('change', () => this.loadDataPreview());
            endDateInput.addEventListener('change', () => this.loadDataPreview());
        }
        
        // Set up refresh button
        const refreshPreviewBtn = document.getElementById('refresh-preview-btn');
        if (refreshPreviewBtn) {
            refreshPreviewBtn.addEventListener('click', () => this.loadDataPreview());
        }
        
        // Set up form submission
        const sendDataForm = document.getElementById('send-data-form');
        if (sendDataForm) {
            sendDataForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendAttendanceData();
            });
        }
        
        // Load initial preview
        this.loadDataPreview();
    },
    
    // Load data preview for API Send page
    loadDataPreview: function() {
        const startDate = document.getElementById('start-date')?.value;
        const endDate = document.getElementById('end-date')?.value;
        
        if (!startDate || !endDate) return;
        
        const previewTable = document.getElementById('preview-table');
        const previewLoading = document.getElementById('preview-loading');
        const previewContent = document.getElementById('preview-content');
        const noData = document.getElementById('no-data');
        
        if (!previewTable || !previewLoading || !previewContent || !noData) return;
        
        // Clear previous data
        previewTable.innerHTML = '';
        
        // Show loading indicator
        previewLoading.classList.remove('d-none');
        previewContent.classList.add('d-none');
        noData.classList.add('d-none');
        
        // Fetch data
        fetch(`/api/attendance?start_date=${startDate}&end_date=${endDate}`)
            .then(response => response.json())
            .then(data => {
                previewLoading.classList.add('d-none');
                
                if (data.status === 'success') {
                    const records = data.attendance || [];
                    
                    if (records.length === 0) {
                        noData.classList.remove('d-none');
                        return;
                    }
                    
                    // Update record count
                    const recordCount = document.getElementById('record-count');
                    if (recordCount) {
                        recordCount.textContent = records.length;
                    }
                    
                    // Show preview content
                    previewContent.classList.remove('d-none');
                    
                    // Populate table (limit to 10 records for preview)
                    records.slice(0, 10).forEach(record => {
                        const row = document.createElement('tr');
                        
                        // User ID
                        const userIdCell = document.createElement('td');
                        userIdCell.textContent = record.user_id;
                        row.appendChild(userIdCell);
                        
                        // Date & Time
                        const timeCell = document.createElement('td');
                        timeCell.textContent = record.timestamp;
                        row.appendChild(timeCell);
                        
                        // Punch Type
                        const typeCell = document.createElement('td');
                        let badgeClass = 'bg-secondary';
                        let punchText = 'Unknown';
                        
                        if (record.punch === 0 || record.punch === '0' || record.punch_type === 0 || record.punch_type === '0') {
                            badgeClass = 'bg-success';
                            punchText = 'Check In';
                        } else if (record.punch === 1 || record.punch === '1' || record.punch_type === 1 || record.punch_type === '1') {
                            badgeClass = 'bg-danger';
                            punchText = 'Check Out';
                        }
                        
                        typeCell.innerHTML = `<span class="badge ${badgeClass}">${punchText}</span>`;
                        row.appendChild(typeCell);
                        
                        previewTable.appendChild(row);
                    });
                    
                    // Add note if there are more records
                    if (records.length > 10) {
                        const noteRow = document.createElement('tr');
                        const noteCell = document.createElement('td');
                        noteCell.colSpan = 3;
                        noteCell.className = 'text-center text-muted';
                        noteCell.textContent = `Showing 10 of ${records.length} records`;
                        noteRow.appendChild(noteCell);
                        previewTable.appendChild(noteRow);
                    }
                } else {
                    noData.classList.remove('d-none');
                    noData.innerHTML = `
                        <i class="bi bi-exclamation-triangle text-danger fs-1"></i>
                        <p class="mt-2">Error loading data: ${data.message}</p>
                    `;
                }
            })
            .catch(error => {
                console.error('Error loading data preview:', error);
                previewLoading.classList.add('d-none');
                noData.classList.remove('d-none');
                noData.innerHTML = `
                    <i class="bi bi-exclamation-triangle text-danger fs-1"></i>
                    <p class="mt-2">Error loading data: ${error.message}</p>
                `;
            });
    },
    
    // Send attendance data to API
    sendAttendanceData: function() {
        const startDate = document.getElementById('start-date')?.value;
        const endDate = document.getElementById('end-date')?.value;
        
        if (!startDate || !endDate) {
            this.showNotification('Please select a date range', 'warning');
            return;
        }
        
        // Get send button
        const sendBtn = document.getElementById('send-btn');
        if (!sendBtn) return;
        
        // Show loading state
        const originalBtnText = sendBtn.innerHTML;
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Sending...';
        
        // Send data
        fetch('/api/send-attendance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate
            })
        })
        .then(response => response.json())
        .then(data => {
            // Reset button
            sendBtn.disabled = false;
            sendBtn.innerHTML = originalBtnText;
            
            // Handle response
            if (data.status === 'success') {
                this.showNotification(`Successfully sent ${data.records_sent} records to API`, 'success');
            } else {
                this.showNotification(`Error sending data: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            // Reset button
            sendBtn.disabled = false;
            sendBtn.innerHTML = originalBtnText;
            
            this.showNotification(`Error sending data: ${error.message}`, 'danger');
        });
    },
    
    // Initialize settings page
    initSettingsPage: function() {
        // Load current settings
        this.loadApiSettings();
        
        // Set up form submission
        const apiSettingsForm = document.getElementById('api-settings-form');
        if (apiSettingsForm) {
            apiSettingsForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveApiSettings();
            });
        }
        
        // Set up test API button
        const testApiBtn = document.getElementById('test-api-btn');
        if (testApiBtn) {
            testApiBtn.addEventListener('click', () => {
                this.testApiConnection();
            });
        }
        
        // Set up trigger sync button
        const triggerSyncBtn = document.getElementById('trigger-sync-btn');
        if (triggerSyncBtn) {
            triggerSyncBtn.addEventListener('click', () => {
                this.triggerSync();
            });
        }
    },
    
    // Load API settings
    loadApiSettings: function() {
        const apiUrlInput = document.getElementById('api-url');
        const apiKeyInput = document.getElementById('api-key');
        const autoSyncCheckbox = document.getElementById('auto-sync');
        
        if (!apiUrlInput) return;
        
        fetch('/api/export-config')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const config = data.config || {};
                    
                    if (apiUrlInput) apiUrlInput.value = config.attendance_api_url || '';
                    if (apiKeyInput) apiKeyInput.value = config.api_key || '';
                    if (autoSyncCheckbox) autoSyncCheckbox.checked = config.auto_sync || false;
                    
                    // Update sync status
                    const lastSync = document.getElementById('last-sync');
                    const recordsSynced = document.getElementById('records-synced');
                    
                    if (lastSync && config.last_sync) {
                        lastSync.textContent = new Date(config.last_sync).toLocaleString();
                    }
                    
                    if (recordsSynced && config.records_synced) {
                        recordsSynced.textContent = config.records_synced;
                    }
                }
            })
            .catch(error => {
                console.error('Error loading API settings:', error);
                this.showNotification('Error loading settings', 'danger');
            });
    },
    
    // Save API settings
    saveApiSettings: function() {
        const apiUrl = document.getElementById('api-url')?.value;
        const apiKey = document.getElementById('api-key')?.value;
        const autoSync = document.getElementById('auto-sync')?.checked;
        
        if (!apiUrl) {
            this.showNotification('Please enter an API URL', 'warning');
            return;
        }
        
        // Get save button
        const saveBtn = document.querySelector('#api-settings-form button[type="submit"]');
        if (!saveBtn) return;
        
        // Show loading state
        const originalBtnText = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
        
        // Save settings
        fetch('/api/export-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                attendance_api_url: apiUrl,
                api_key: apiKey,
                auto_sync: autoSync
            })
        })
        .then(response => response.json())
        .then(data => {
            // Reset button
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalBtnText;
            
            // Handle response
            if (data.status === 'success') {
                this.showNotification('Settings saved successfully', 'success');
            } else {
                this.showNotification(`Error saving settings: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            // Reset button
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalBtnText;
            
            this.showNotification(`Error saving settings: ${error.message}`, 'danger');
        });
    },
    
    // Test API connection
    testApiConnection: function() {
        const apiUrl = document.getElementById('api-url')?.value;
        
        if (!apiUrl) {
            this.showNotification('Please enter an API URL', 'warning');
            return;
        }
        
        // Get test button
        const testBtn = document.getElementById('test-api-btn');
        if (!testBtn) return;
        
        // Show loading state
        const originalBtnText = testBtn.innerHTML;
        testBtn.disabled = true;
        testBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Testing...';
        
        // Test connection
        fetch('/api/test-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                api_url: apiUrl
            })
        })
        .then(response => response.json())
        .then(data => {
            // Reset button
            testBtn.disabled = false;
            testBtn.innerHTML = originalBtnText;
            
            // Handle response
            if (data.status === 'success') {
                this.showNotification('API connection successful!', 'success');
            } else {
                this.showNotification(`API connection failed: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            // Reset button
            testBtn.disabled = false;
            testBtn.innerHTML = originalBtnText;
            
            this.showNotification(`Error testing API connection: ${error.message}`, 'danger');
        });
    },
    
    // Trigger sync
    triggerSync: function() {
        // Get trigger button
        const triggerBtn = document.getElementById('trigger-sync-btn');
        if (!triggerBtn) return;
        
        // Show loading state
        const originalBtnText = triggerBtn.innerHTML;
        triggerBtn.disabled = true;
        triggerBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Syncing...';
        
        // Trigger sync
        fetch('/api/trigger-sync')
            .then(response => response.json())
            .then(data => {
                // Reset button
                triggerBtn.disabled = false;
                triggerBtn.innerHTML = originalBtnText;
                
                // Handle response
                if (data.status === 'success') {
                    this.showNotification('Sync triggered successfully', 'success');
                    
                    // Update sync status after a delay
                    setTimeout(() => {
                        this.loadApiSettings();
                    }, 2000);
                } else {
                    this.showNotification(`Sync failed: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                // Reset button
                triggerBtn.disabled = false;
                triggerBtn.innerHTML = originalBtnText;
                
                this.showNotification(`Error triggering sync: ${error.message}`, 'danger');
            });
    }
};

// Direct navigation function for links
function navigateTo(page) {
    console.log('Navigating to:', page);
    window.location.href = '/' + page;
    return false;
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded - initializing app');
    app.init();
});
