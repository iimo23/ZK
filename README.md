# ZK Tech Device API

This Python project provides a REST API for interacting with ZK Tech biometric devices (fingerprint scanners, face recognition devices, etc.) using the `pyzk` library and Flask.

## Requirements

- Python 3.7 or higher
- pip (Python package manager)

### Required Packages
```bash
pyzk==0.9          # ZK device communication library
flask==3.1.0       # Web framework
flask-cors==5.0.0  # Cross-Origin Resource Sharing
werkzeug==3.1.3    # WSGI web application library
itsdangerous==2.2.0# Security functions
click>=8.1.3       # CLI toolkit
blinker>=1.9.0     # Event dispatching
Jinja2>=3.1.2      # Template engine
```

## Installation

1. Clone or download this repository
2. Install the required packages:
```bash
python -m pip install -r requirements.txt
```

## Configuration

The default device configuration is:
- IP Address: 192.168.37.11
- Port: 4370
- Timeout: 5 seconds

To modify these settings, update the connection parameters in `api.py`.

## Running the Server

Start the Flask server:
```bash
python api.py
```
The server will run on `http://localhost:5000`

## API Endpoints

### 1. Get Device Information
```
GET /device-info
```
Returns device firmware version and serial number.

Example Response:
```json
{
    "status": "success",
    "data": {
        "firmware_version": "Ver 6.60 Apr 13 2022",
        "serial_number": "RKQ4235101028"
    }
}
```

### 2. Get All Users
```
GET /users
```
Returns list of all users registered in the device.

Example Response:
```json
{
    "status": "success",
    "data": [
        {
            "uid": 1,
            "name": "mohammed",
            "privilege": "Admin",
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
Returns attendance records for all users, organized by user and date.

Example Response:
```json
{
    "status": "success",
    "data": {
        "1": {
            "user_name": "mohammed",
            "records": {
                "2024-12-02": {
                    "check_in": "10:14:19",
                    "check_out": "11:03:31"
                }
            }
        }
    },
    "total_records": 15
}
```

### 4. Get User by ID
```
GET /user/<user_id>
```
Returns specific user information and their attendance records.

Example Response:
```json
{
    "status": "success",
    "data": {
        "user_info": {
            "uid": 1,
            "name": "mohammed",
            "privilege": "Admin",
            "password": "1234",
            "card": "0"
        },
        "attendance": {
            "2024-12-02": {
                "check_in": "10:14:19",
                "check_out": "11:03:31"
            }
        },
        "total_attendance_records": 15
    }
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
- User not found
- Invalid request parameters

## Testing

You can test the API using tools like Postman or curl. Make sure the device is powered on and accessible on the network before making requests.
