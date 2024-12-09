# ZK Attendance API

A Flask-based REST API for managing attendance records from ZK biometric devices.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure device settings in api.py:
```python
IP_ADDRESS = '192.168.37.11'
PORT = 4370
TIMEOUT = 5
```

## API Endpoints

### 1. Get All Attendance Records
```
GET /attendance
```
Returns all attendance records grouped by date and user.

### 2. Search Attendance by Date Range
```
GET /attendance/search
```
Parameters:
- start_date (optional): Start date in YYYY-MM-DD format
- end_date (optional): End date in YYYY-MM-DD format

If no dates provided, returns all records.
If only start_date, returns records from that date to now.
If only end_date, returns all records up to that date.

### 3. Search Attendance by User
```
GET /attendance/user
```
Parameters:
- user_id (required): User ID to search for
- start_date (optional): Start date in YYYY-MM-DD format
- end_date (optional): End date in YYYY-MM-DD format

### 4. Get User Information
```
GET /user/<user_id>
```
Returns information about a specific user.

### 5. Get All Users
```
GET /users
```
Returns list of all users registered in the device.

## Response Format

### Attendance Records
```json
{
  "status": "success",
  "data": [
    {
      "attendancedate": "2024-12-08",
      "records": [
        {
          "user_id": "123",
          "user_name": "John Doe",
          "attendance_records": [
            {
              "timestamp": "2024-12-08 09:00:00",
              "punch_type": "Check In",
              "punchtime": 0
            }
          ]
        }
      ],
      "total_users": 1
    }
  ],
  "total_days": 1
}
```

### User Records
```json
{
  "status": "success",
  "user_info": {
    "user_id": "123",
    "user_name": "John Doe"
  },
  "data": [
    {
      "attendancedate": "2024-12-08",
      "attendance_records": [
        {
          "timestamp": "2024-12-08 09:00:00",
          "punch_type": "Check In",
          "punchtime": 0
        }
      ],
      "total_records": 1
    }
  ]
}
```

## Record Types
- Check In (punchtime: 0)
- Check Out (punchtime: 1)

## Dependencies
- Flask (3.1.0)
- pyzk (0.9)
- Flask-CORS (5.0.0)

## Error Handling
All endpoints return appropriate HTTP status codes and error messages:
```json
{
  "status": "error",
  "message": "Error description"
}
```

Common status codes:
- 200: Success
- 400: Bad Request (invalid parameters)
- 404: Not Found (user or resource not found)
- 500: Server Error
