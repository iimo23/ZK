# ZK Attendance API

A Flask-based REST API for managing attendance records from ZK biometric devices.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure device settings in api.py:
```python
IP_ADDRESS = '192.168.37.10'
PORT = 4370
TIMEOUT = 5
```

## API Endpoints

### 1. Get Device Information
```
GET /device-info
```
Returns device firmware version and serial number.

Response:
```json
{
  "status": "success",
  "data": {
    "firmware_version": "6.60.401.5",
    "serial_number": "ABC123456789"
  }
}
```

### 2. Get All Users
```
GET /users
```
Returns list of all users registered in the device.

Response:
```json
{
  "status": "success",
  "data": [
    {
      "uid": "1",
      "name": "John Doe",
      "privilege": "User",
      "password": "1234",
      "card": "0"
    }
  ]
}
```

### 3. Get All Attendance Records
```
GET /attendance
```
Returns all attendance records with punch types.

Response:
```json
{
  "data": [
    {
      "emp_no": "1",
      "device_id": "ABC123456789",
      "punch_type": "1",  // 1=Check In, 2=Check Out, 3-6=Other punch types
      "punch_date": "2024-12-02",
      "punch_time": "2024-12-02 10:14:19"
    }
  ]
}
```

Punch Type Values:
- "1": Check In
- "2": Check Out
- "3": Punch Type 3
- "4": Punch Type 4
- "5": Punch Type 5
- "6": Punch Type 6

### 4. Get User Information and Attendance
```
GET /user/<user_id>
```
Returns information about a specific user and their attendance records.

Response:
```json
{
  "status": "success",
  "data": {
    "user_info": {
      "uid": "1",
      "name": "John Doe",
      "privilege": "User",
      "password": "1234",
      "card": "0"
    },
    "attendance": {
      "2024-12-02": {
        "records": [
          {
            "time": "10:14:19",
            "punch_type": "1"
          }
        ]
      }
    },
    "total_attendance_records": 1
  }
}
```

### 5. Add Users to Device
```
POST /add-users
```
Adds new users to the device from a URL that returns a JSON array of users.

Request Body:
```json
{
  "url": "https://your-api-url/users"
}
```

The URL should return a JSON array of users in the following format:
```json
[
  {
    "emp_id": "123",
    "name": "John Doe"
  },
  {
    "emp_id": "456",
    "name": "Jane Smith"
  }
]
```

Response:
```json
{
  "status": "success",
  "data": {
    "added_users": 5,
    "failed_users": [
      {
        "emp_id": "123",
        "name": "John Doe",
        "error": "Error message"
      }
    ]
  }
}
```

### 5. Add Multiple Users
```
POST /users
```
Add multiple users to the device. Request body should contain an array of user objects.

Request Body:
```json
{
  "users": [
    {
      "emp_no": "123",
      "name": "John Doe",
      "privilege": "User",
      "password": "1234"
    }
  ]
}
```

### 6. Add Single User
```
POST /user
```
Add a single user to the device.

Request Body:
```json
{
  "emp_no": "123",
  "name": "John Doe",
  "privilege": "User",
  "password": "1234"
}
```

### 7. Delete User
```
DELETE /user/<emp_no>
```
Delete a user from the device by their employee number.

Response:
```json
{
  "status": "success",
  "message": "User deleted successfully"
}
```

## Error Handling

All endpoints return error responses in the following format:
```json
{
  "status": "error",
  "message": "Error description"
}
```

Common error scenarios:
- Device connection failure
- Invalid user ID
- Invalid date format
- User not found

## Notes
- The device connection settings (IP_ADDRESS, PORT, TIMEOUT) must be configured correctly in the api.py file
- User privilege levels: "User", "Admin", "Supervisor"
- All timestamps are returned in the local device timezone
- The API uses Flask and requires Python 3.6 or higher

## License
This project is licensed under the MIT License.
