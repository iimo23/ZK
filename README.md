# ZK Attendance System

A modern web interface for managing ZK biometric devices, featuring real-time attendance tracking, user management, and data export capabilities.

## Features

- **Real-time Dashboard**
  - Device connection status
  - User statistics
  - Recent activity feed
  - Dynamic activity filtering

- **User Management**
  - View all users
  - Add/Delete users
  - View user attendance history
  - Bulk user operations

- **Activity Monitoring**
  - Real-time attendance tracking
  - Filter by date range
  - Filter by user
  - Filter by punch type (Check In/Out)
  - Advanced search capabilities

- **Data Export**
  - Customizable data export
  - Date range selection
  - User selection
  - Preview before export
  - Auto-export capability
  - Custom endpoint configuration

- **Settings Management**
  - Device configuration
  - Export settings
  - System maintenance

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Access the web interface:
```
http://localhost:5000
```

## Usage Guide

### 1. Device Connection

1. Click Settings in the navigation bar
2. Enter device IP and Port
3. Click "Save Device Settings"
4. The connection status will be shown in the navigation bar

### 2. User Management

Access the Users page to:
- View all registered users
- Add new users
- Delete existing users
- View individual user attendance history

### 3. Activity Monitoring

The dashboard provides:
- Real-time activity feed
- Multiple filtering options:
  - Date filters (Today, This Week, This Month)
  - User search
  - Punch type filters
- Automatic refresh

### 4. Data Export

The Export page allows you to:
1. Select date range:
   - Quick selections (Today, This Week, This Month)
   - Custom date range
2. Select users:
   - Individual users
   - Multiple users
   - All users
3. Preview data before export
4. Export to external system

### 5. Settings

The Settings page provides:
1. Device Settings:
   - IP Address
   - Port number
2. Export Settings:
   - Export URL configuration
   - Auto-export toggle
3. System Settings:
   - Clear data
   - Reset settings

## API Endpoints

### Device Management

```
GET /api/device-info
```
Returns current device connection information.

```
POST /api/connect
```
Connect to a device with specified IP and port.

### User Management

```
GET /api/users
```
Returns list of all users.

```
POST /api/user
```
Add a new user.

```
DELETE /api/user/<user_id>
```
Delete a user.

### Attendance Management

```
GET /api/attendance
```
Get attendance records with optional filters:
- start_date
- end_date
- emp_no

### Export Management

```
GET /api/export-config
```
Get current export configuration.

```
POST /api/export-config
```
Update export configuration:
```json
{
  "export_url": "https://your-endpoint.com/data",
  "auto_export": false
}
```

```
POST /api/export-attendance
```
Export attendance data to configured endpoint.

### Settings Management

```
POST /api/clear-data
```
Clear all stored data.

```
POST /api/reset-settings
```
Reset all settings to default.

## Data Formats

### Export Data Format

```json
{
  "device_info": {
    "ip": "192.168.1.100",
    "port": 4370,
    "export_time": "2025-02-25 17:49:13"
  },
  "records": [
    {
      "employee_id": "123",
      "employee_name": "John Doe",
      "timestamp": "2025-02-25 09:00:00",
      "date": "2025-02-25",
      "time": "09:00:00",
      "punch_type": "Check In"
    }
  ]
}
```

## Error Handling

All API endpoints return JSON responses with the following structure:

```json
{
  "status": "success|error",
  "message": "Description of the result",
  "data": {}  // Optional data object
}
```

Common HTTP status codes:
- 200: Success
- 400: Bad Request
- 401: Unauthorized (Device not connected)
- 500: Server Error

## Security Notes

1. Device connection information is stored in server-side session
2. SSL verification is disabled for export endpoints
3. No authentication is required for the web interface
4. API tokens are not required for data export

## Troubleshooting

1. Device Connection Issues:
   - Verify IP address and port
   - Check network connectivity
   - Ensure device is powered on

2. Export Issues:
   - Verify export URL is correct
   - Check endpoint availability
   - Review response messages

3. Data Issues:
   - Clear data and reconnect device
   - Reset settings if configuration is corrupted
   - Check device time synchronization
