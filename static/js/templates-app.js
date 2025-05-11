// ZK Attendance System - Templates App JS

document.addEventListener('DOMContentLoaded', function() {
    console.log('Templates app initialized');
    
    // Initialize settings page functionality
    initSettingsPage();
    
    // Check connection status and update UI
    updateConnectionStatus();
});

// Update connection status UI
function updateConnectionStatus() {
    const statusElement = document.querySelector('.connection-status');
    
    if (!statusElement) return;
    
    fetch('/api/device-info')
        .then(response => response.json())
        .then(data => {
            const isConnected = (data.status === 'success');
            
            if (isConnected) {
                statusElement.className = 'connection-status connected';
                statusElement.innerHTML = '<i class="bi bi-check-circle"></i> Connected';
            } else {
                statusElement.className = 'connection-status disconnected';
                statusElement.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Not Connected';
            }
        })
        .catch(error => {
            console.error('Error checking connection status:', error);
            statusElement.className = 'connection-status disconnected';
            statusElement.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Not Connected';
        });
}

// Initialize settings page functionality
function initSettingsPage() {
    // Only run on settings page
    if (!document.getElementById('api-settings-form')) return;
    
    console.log('Initializing settings page');
    
    // Load API settings
    loadApiSettings();
    
    // Set up form submission
    const settingsForm = document.getElementById('api-settings-form');
    if (settingsForm) {
        settingsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveApiSettings();
        });
    }
    
    // Set up test API button
    const testApiBtn = document.getElementById('test-api-btn');
    if (testApiBtn) {
        testApiBtn.addEventListener('click', function() {
            testApiConnection();
        });
    }
    
    // Set up trigger sync button
    const triggerSyncBtn = document.getElementById('trigger-sync-btn');
    if (triggerSyncBtn) {
        triggerSyncBtn.addEventListener('click', function() {
            triggerSync(false);
        });
    }
    
    // Set up trigger sync reset button
    const triggerSyncResetBtn = document.getElementById('trigger-sync-reset');
    if (triggerSyncResetBtn) {
        triggerSyncResetBtn.addEventListener('click', function() {
            triggerSync(true);
        });
    }
}

// Load API settings
function loadApiSettings() {
    const apiUrlInput = document.getElementById('api-url');
    const apiKeyInput = document.getElementById('api-key');
    const autoSyncCheckbox = document.getElementById('auto-sync');
    const lastSync = document.getElementById('last-sync');
    const recordsSynced = document.getElementById('records-synced');
    
    if (!apiUrlInput) return;
    
    fetch('/api/export-config')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const config = data.config || {};
                
                if (apiUrlInput) apiUrlInput.value = config.attendance_api_url || '';
                if (apiKeyInput) apiKeyInput.value = config.api_key || '';
                if (autoSyncCheckbox) autoSyncCheckbox.checked = config.auto_sync !== false;
                
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
            showNotification('Error loading settings', 'danger');
        });
}

// Save API settings
function saveApiSettings() {
    const apiUrl = document.getElementById('api-url')?.value;
    const apiKey = document.getElementById('api-key')?.value;
    const autoSync = document.getElementById('auto-sync')?.checked;
    
    if (!apiUrl) {
        showNotification('Please enter an API URL', 'warning');
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
            showNotification('Settings saved successfully', 'success');
        } else {
            showNotification(`Error saving settings: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        // Reset button
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalBtnText;
        
        showNotification(`Error saving settings: ${error.message}`, 'danger');
    });
}

// Test API connection
function testApiConnection() {
    const apiUrl = document.getElementById('api-url')?.value;
    
    if (!apiUrl) {
        showNotification('Please enter an API URL', 'warning');
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
            showNotification('API connection successful!', 'success');
        } else {
            showNotification(`API connection failed: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        // Reset button
        testBtn.disabled = false;
        testBtn.innerHTML = originalBtnText;
        
        showNotification(`Error testing API connection: ${error.message}`, 'danger');
    });
}

// Trigger sync
function triggerSync(reset = false) {
    // Get trigger button
    const triggerBtn = reset ? 
        document.getElementById('trigger-sync-reset') : 
        document.getElementById('trigger-sync-btn');
    
    if (!triggerBtn) return;
    
    // Show loading state
    const originalBtnText = triggerBtn.innerHTML;
    triggerBtn.disabled = true;
    triggerBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Syncing...';
    
    // Update status
    const syncStatus = document.getElementById('sync-status');
    if (syncStatus) {
        syncStatus.innerHTML = '<div class="alert alert-info">Sync in progress...</div>';
        syncStatus.classList.remove('d-none');
    }
    
    // Trigger sync
    fetch('/api/trigger-sync', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            reset: reset
        })
    })
    .then(response => response.json())
    .then(data => {
        // Reset button
        triggerBtn.disabled = false;
        triggerBtn.innerHTML = originalBtnText;
        
        // Handle response
        if (data.status === 'success') {
            if (syncStatus) {
                syncStatus.innerHTML = '<div class="alert alert-success">Sync triggered successfully!</div>';
            }
            
            showNotification('Sync triggered successfully', 'success');
            
            // Update sync status after a delay
            setTimeout(() => {
                loadApiSettings();
            }, 2000);
        } else {
            if (syncStatus) {
                syncStatus.innerHTML = `<div class="alert alert-danger">Sync failed: ${data.message}</div>`;
            }
            
            showNotification(`Sync failed: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        // Reset button
        triggerBtn.disabled = false;
        triggerBtn.innerHTML = originalBtnText;
        
        if (syncStatus) {
            syncStatus.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
        }
        
        showNotification(`Error triggering sync: ${error.message}`, 'danger');
    });
}

// Show notification
function showNotification(message, type = 'info') {
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
}
