# ZK Attendance System

A streamlined system for connecting to ZK biometric devices, retrieving attendance data, and automatically synchronizing it with external APIs.

## Core Functionality

- **Device Connection**
  - Connect to ZK biometric devices
  - Retrieve device information
  - Get users from the device
  - Get attendance records from the device

- **API Integration**
  - Send attendance data to external API
  - Format records according to API requirements
  - Handle API responses and errors
  - Support for batch and individual record sending

- **Automatic Synchronization**
  - Background scheduler that runs every minute
  - Sync attendance data to API
  - Track which records have been sent to avoid duplicates
  - Filter records by date

- **Web Interface**
  - Endpoints for device connection
  - Endpoints for viewing and exporting data
  - API endpoints for programmatic access
  - User management capabilities

## Setup

### Prerequisites

- Python 3.8 or higher
- Network access to ZK biometric device
- Internet connection for API synchronization

### Dependencies

The system relies on the following key dependencies:
- Flask - Web framework
- APScheduler - Background task scheduling
- pyzk/zk - ZK device communication libraries
- Requests - HTTP client for API integration

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/zk-attendance-system.git
cd zk-attendance-system
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Access the web interface:
```
http://localhost:5000
```

### Configuration

- Default device IP: 192.168.37.10
- Default port: 4370
- Default timeout: 5 seconds

These settings can be modified through the web interface or by editing the `config.json` file.

## Automatic Synchronization

The system automatically synchronizes attendance data with the configured API endpoint using a background scheduler. This ensures that all attendance records are promptly sent to your external system.

Key features of the synchronization:
- Runs in the background using APScheduler
- Tracks which records have been sent using a set (`sync_records_sent`) to avoid duplicates
- Supports both batch sending and individual record sending
- Falls back to individual record sending if batch sending fails
- Logs all sync activities for troubleshooting
- Filters records by date to ensure only relevant data is sent

## System Architecture

The ZK Attendance System is built around a Flask web application with the following components:

### 1. Device Connection

The system connects to ZK biometric devices using the `zk` library. The connection is managed through:
- Direct IP connection with configurable port and timeout
- Device manager for handling multiple devices
- Connection status tracking

### 2. User Management

The system provides APIs for:
- Retrieving users from the device
- Adding new users to the device
- Adding users in bulk from an external API URL
- Deleting users from the device

### 3. Attendance Data Processing

The system processes attendance data by:
- Retrieving raw attendance records from the device
- Formatting records with proper date/time and punch type information
- Organizing records by user and date
- Filtering records based on date ranges

### 4. API Integration

The system integrates with external APIs by:
- Formatting attendance records according to API requirements
- Supporting batch and individual record sending
- Handling API responses and errors
- Tracking sent records to avoid duplicates

### 5. Background Scheduler

The system uses APScheduler to:
- Run synchronization tasks in the background
- Schedule regular attendance data syncs
- Track synchronization status and history

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
Returns list of all users from the connected device.

```
POST /api/user
```
Add a new user to the device.

```
POST /api/add-users-from-url
```
Add multiple users to the device by fetching data from an external API URL.

### Attendance Management

```
GET /api/attendance
```
Get attendance records with optional filters:
- start_date
- end_date
- emp_no

```
POST /api/send-attendance
```
Send attendance data to the configured API endpoint with filters:
- start_date
- end_date
- emp_no

### Configuration Management

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

## Data Formats

### Attendance Record Format

Each attendance record is formatted for API submission as follows:

```json
{
  "employee_id": "123",
  "employee_name": "John Doe",
  "timestamp": "2025-05-04 09:00:00",
  "date": "2025-05-04",
  "time": "09:00:00",
  "punch_type": "Check In"
}
```

### Batch Export Format

When sending multiple records in a batch:

```json
{
  "device_info": {
    "ip": "192.168.37.10",
    "port": 4370,
    "export_time": "2025-05-04 17:49:13"
  },
  "records": [
    {
      "employee_id": "123",
      "employee_name": "John Doe",
      "timestamp": "2025-05-04 09:00:00",
      "date": "2025-05-04",
      "time": "09:00:00",
      "punch_type": "Check In"
    },
    {
      "employee_id": "456",
      "employee_name": "Jane Smith",
      "timestamp": "2025-05-04 09:15:00",
      "date": "2025-05-04",
      "time": "09:15:00",
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

## Implementation Details

1. **Device Connection**
   - Uses the ZK library to communicate with biometric devices
   - Supports connection via IP address and port
   - Handles connection timeouts and errors
   - Maintains connection state

2. **Record Tracking**
   - Uses a set (`sync_records_sent`) to track which records have been sent
   - Prevents duplicate record submission
   - Maintains record history

3. **Background Scheduler**
   - Uses APScheduler for background tasks
   - Runs synchronization tasks automatically
   - Handles scheduler shutdown on application exit

4. **Logging**
   - Comprehensive logging system
   - Logs device connections, data retrieval, and API interactions
   - Logs errors and exceptions for troubleshooting

## Troubleshooting

1. Device Connection Issues:
   - Verify IP address and port in config.json
   - Check network connectivity
   - Ensure device is powered on
   - Check the application logs for connection errors

2. API Integration Issues:
   - Verify export URL is correct in export_config.json
   - Check endpoint availability
   - Review response messages in the logs
   - Ensure proper data format is being sent

3. Synchronization Issues:
   - Check if the scheduler is running
   - Verify that records are being retrieved from the device
   - Check for API errors in the logs
   - Ensure the system clock is synchronized
