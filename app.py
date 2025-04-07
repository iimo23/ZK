from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from flask_cors import CORS
from zk import ZK, const
from datetime import datetime, timedelta
from collections import defaultdict
import requests
import logging
from functools import wraps
import os
import json
import sys
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
CORS(app)

# Configure logging
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)

# Set up app logger
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

# Suppress verbose logging from other libraries
logging.getLogger('zk').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Default device settings
DEFAULT_IP = '192.168.37.10'
DEFAULT_PORT = 4370
DEFAULT_TIMEOUT = 5

# Ensure config directory exists
CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'config')
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

# Update export config path
def get_config_path(filename):
    return os.path.join(CONFIG_DIR, filename)

# Device connection helper
def connect_to_device(ip=None, port=None, timeout=None):
    """Connect to ZK device using session information or provided credentials"""
    try:
        # First try to get credentials from headers
        if request and request.headers:
            ip = ip or request.headers.get('X-Device-IP')
            try:
                port = port or int(request.headers.get('X-Device-Port', DEFAULT_PORT))
            except (TypeError, ValueError):
                port = DEFAULT_PORT
        
        # If no headers, try session
        if not ip and 'device_ip' in session:
            ip = session.get('device_ip')
            port = session.get('device_port', DEFAULT_PORT)
        
        # Final fallback to defaults
        ip = ip or DEFAULT_IP
        port = port or DEFAULT_PORT
        timeout = timeout or DEFAULT_TIMEOUT

        logger.info(f"Attempting to connect to device at {ip}:{port} with timeout {timeout}")
        
        # Validate IP address format
        if not ip or not isinstance(ip, str):
            raise ValueError("Invalid IP address format")

        # Create ZK instance with more reliable settings
        zk = ZK(ip, 
               port=port, 
               timeout=timeout, 
               force_udp=False, 
               ommit_ping=True,  # Changed to True to avoid initial ping
               verbose=False)    # Set to False to reduce debug output
        
        # Attempt connection
        conn = zk.connect()
        if not conn:
            raise ConnectionError("Failed to establish connection - no connection object returned")
        
        # Test if connection is alive
        if not conn.is_connect:
            raise ConnectionError("Connection object created but not connected")
            
        logger.info("Successfully connected to device")
        return conn
        
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise Exception(f"Invalid connection parameters: {str(ve)}")
    except ConnectionError as ce:
        logger.error(f"Connection error: {str(ce)}")
        raise Exception(f"Failed to connect to device: {str(ce)}")
    except Exception as e:
        logger.error(f"Unexpected error during connection: {str(e)}")
        raise Exception(f"Error connecting to device: {str(e)}")

# Utility Functions (unchanged)
def get_punch_type_text(punch_type):
    punch_dict = {0: "1", 1: "2", 2: "3", 3: "4", 4: "5", 5: "6"}
    return punch_dict.get(punch_type, "Unknown")

def organize_attendance(attendance_records):
    user_records = defaultdict(list)
    for record in attendance_records:
        user_records[record.user_id].append(record)
    
    organized_records = {}
    for user_id, records in user_records.items():
        records.sort(key=lambda x: x.timestamp)
        daily_records = defaultdict(list)
        
        for record in records:
            punch = record.punch if hasattr(record, 'punch') else 0
            date = record.timestamp.strftime('%Y-%m-%d')
            daily_records[date].append({
                'time': record.timestamp.strftime('%H:%M:%S'),
                'punch_type': get_punch_type_text(punch)
            })
        
        organized_records[str(user_id)] = {
            date: {"records": sorted(times, key=lambda x: x['time'])}
            for date, times in daily_records.items()
        }
    
    return organized_records

# Add session check decorator
def require_device_connection(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check headers first
        if request.headers.get('X-Device-IP'):
            return f(*args, **kwargs)
        # Then check session
        if 'device_ip' in session:
            return f(*args, **kwargs)
        return jsonify({
            "status": "error", 
            "message": "No device connected. Please provide device information via headers (X-Device-IP, X-Device-Port) or connect through the web interface."
        }), 401
    return decorated_function

# API Endpoints
@app.route('/api/device-info', methods=['GET'])
@require_device_connection
def get_device_info():
    try:
        conn = connect_to_device()
        try:
            info = {
                "status": "Connected",
                "firmware": conn.get_firmware_version(),
                "serial": conn.get_serialnumber(),
                "platform": conn.get_platform(),
                "device_name": conn.get_device_name(),
                "ip": session.get('device_ip') or request.headers.get('X-Device-IP'),
                "port": session.get('device_port') or request.headers.get('X-Device-Port', 4370)
            }
            return jsonify({"status": "success", "data": info})
        finally:
            conn.disconnect()
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/users', methods=['GET'])
@require_device_connection
def get_users():
    try:
        logger.info("Attempting to get users")
        conn = connect_to_device()
        try:
            logger.info("Connected to device, fetching users...")
            users = conn.get_users()
            
            if not users:
                logger.warning("No users found in the device")
                return jsonify({"status": "success", "data": [], "message": "No users found in the device"})
                
            logger.info(f"Found {len(users)} users")
            
            # Debug output for troubleshooting
            for i, user in enumerate(users):
                logger.info(f"User {i+1}: ID={user.user_id}, Name={user.name}, UID={user.uid}, Privilege={user.privilege}")
            
            user_list = []
            for user in users:
                try:
                    # Ensure all fields are properly converted to strings
                    user_data = {
                        'uid': str(user.uid) if hasattr(user, 'uid') else 'N/A',
                        'emp_no': str(user.user_id) if hasattr(user, 'user_id') else 'N/A',
                        'name': str(user.name) if hasattr(user, 'name') else 'N/A',
                        'privilege': int(user.privilege) if hasattr(user, 'privilege') else 0,
                    }
                    user_list.append(user_data)
                    logger.debug(f"Processed user: {user_data}")
                except Exception as ae:
                    logger.error(f"Error processing user data: {str(ae)}")
                    continue
                    
            logger.info(f"Successfully processed {len(user_list)} users")
            return jsonify({
                "status": "success", 
                "data": user_list,
                "count": len(user_list)
            })
        except Exception as e:
            error_msg = f"Error getting users: {str(e)}"
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500
        finally:
            try:
                conn.disconnect()
                logger.info("Device disconnected")
            except Exception as e:
                logger.warning(f"Error disconnecting from device: {str(e)}")
    except Exception as e:
        error_msg = f"Error in users endpoint: {str(e)}"
        logger.error(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/api/attendance', methods=['GET', 'POST'])
@require_device_connection
def get_attendance():
    try:
        # Handle both GET and POST requests
        if request.method == 'POST':
            data = request.get_json()
            start_date = data.get('start_date') if data else None
            end_date = data.get('end_date') if data else None
            emp_no = data.get('emp_no') if data else None
        else:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            emp_no = request.args.get('emp_no')
        
        logger.info(f"Getting attendance records: start_date={start_date}, end_date={end_date}, emp_no={emp_no}")
        
        conn = connect_to_device()
        try:
            attendance = conn.get_attendance()
            records = []
            
            for record in attendance:
                # Create basic record
                record_data = {
                    'emp_no': str(record.user_id),
                    'name': str(record.user_id),  # Will be updated with real name
                    'punch_time': record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'punch_type': get_punch_type_text(record.punch if hasattr(record, 'punch') else 0),
                    'punch_date': record.timestamp.strftime('%Y-%m-%d'),
                    'terminal_id': "ZK",
                    'source': "ZK_DEVICE"
                }
                
                # Apply date filter if specified
                if start_date and end_date:
                    record_date = record.timestamp.strftime('%Y-%m-%d')
                    if record_date < start_date or record_date > end_date:
                        continue
                
                # Apply employee filter if specified
                if emp_no and str(record.user_id) != str(emp_no):
                    continue
                
                records.append(record_data)
            
            # Sort records by timestamp in descending order
            records.sort(key=lambda x: x['punch_time'], reverse=True)
            
            # Update names from users list
            try:
                users = conn.get_users()
                user_dict = {str(user.user_id): user.name for user in users}
                for record in records:
                    record['name'] = user_dict.get(str(record['emp_no']), str(record['emp_no']))
            except Exception as e:
                logger.warning(f"Failed to get user names: {e}")
            
            logger.info(f"Retrieved {len(records)} attendance records")
            return jsonify({"status": "success", "records": records})
        finally:
            conn.disconnect()
    except Exception as e:
        logger.error(f"Error getting attendance: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/user', methods=['POST'])
@require_device_connection
def add_user():
    try:
        logger.info("Attempting to add user")
        if not request.is_json:
            return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        
        if not all(key in data for key in ['emp_no', 'name', 'privilege']):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
        
        conn = connect_to_device()
        
        try:
            conn.set_user(
                uid=int(data['emp_no']),
                name=data['name'],
                privilege=int(data['privilege']),
                password='',
                group_id='',
                user_id=data['emp_no']
            )
            logger.info("User added successfully")
            return jsonify({"status": "success", "message": "User added successfully"})
        except Exception as e:
            error_msg = f"Error adding user: {str(e)}"
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500
        finally:
            try:
                conn.disconnect()
                logger.info("Device disconnected")
            except:
                logger.warning("Error disconnecting from device")
    except Exception as e:
        error_msg = f"Error in add user endpoint: {str(e)}"
        logger.error(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/api/user/<emp_no>', methods=['DELETE'])
@require_device_connection
def delete_user(emp_no):
    try:
        logger.info("Attempting to delete user")
        conn = connect_to_device()
        try:
            conn.delete_user(user_id=emp_no)
            logger.info("User deleted successfully")
            return jsonify({"status": "success", "message": "User deleted successfully"})
        except Exception as e:
            error_msg = f"Error deleting user: {str(e)}"
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500
        finally:
            try:
                conn.disconnect()
                logger.info("Device disconnected")
            except:
                logger.warning("Error disconnecting from device")
    except Exception as e:
        error_msg = f"Error in delete user endpoint: {str(e)}"
        logger.error(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/api/add-users-url', methods=['POST'])
@require_device_connection
def add_users():
    # Unchanged code omitted for brevity
    pass  # Replace with your existing implementation

@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    # Get device info from form data or headers
    ip = request.form.get('ip') or request.headers.get('X-Device-IP')
    try:
        port = int(request.form.get('port', 4370)) if request.form.get('port') else int(request.headers.get('X-Device-Port', 4370))
    except (TypeError, ValueError):
        port = 4370
    
    if not ip:
        return jsonify({"status": "error", "message": "Device IP is required"}), 400
    
    try:
        zk = ZK(ip, port=port)
        conn = zk.connect()
        
        info = {
            "status": "Connected",
            "firmware": conn.get_firmware_version(),
            "serial": conn.get_serialnumber(),
            "platform": conn.get_platform(),
            "device_name": conn.get_device_name(),
        }
        conn.disconnect()
        return jsonify({"status": "success", "data": info})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# Configuration endpoints
@app.route('/api/export-config', methods=['GET', 'POST'])
def export_config():
    config_file = get_config_path('export_config.json')
    if request.method == 'POST':
        try:
            config = request.get_json()
            with open(config_file, 'w') as f:
                json.dump(config, f)
            return jsonify({"status": "success", "message": "Export configuration saved"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            return jsonify({"status": "success", "data": config})
        except FileNotFoundError:
            return jsonify({"status": "success", "data": {
                "export_url": "",
                "auto_export": False
            }})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

# Export endpoint
@app.route('/api/export-attendance', methods=['POST'])
@require_device_connection
def export_attendance():
    try:
        # Get export configuration
        config_file = get_config_path('export_config.json')
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            return jsonify({
                "status": "error",
                "message": "Export configuration not found. Please configure export settings first."
            }), 400

        export_url = config.get('export_url')
        if not export_url:
            return jsonify({
                "status": "error",
                "message": "Export URL must be configured"
            }), 400

        # Get request data
        request_data = request.get_json() or {}
        selected_records = request_data.get('records', [])

        # If no records provided, get all attendance
        if not selected_records:
            conn = connect_to_device()
            try:
                attendance = conn.get_attendance()
                users = {str(user.user_id): user.name for user in conn.get_users()}
                
                # Format data for export
                records = []
                for record in attendance:
                    record_data = {
                        'employee_id': str(record.user_id),
                        'employee_name': users.get(str(record.user_id), 'Unknown'),
                        'timestamp': record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'date': record.timestamp.strftime('%Y-%m-%d'),
                        'time': record.timestamp.strftime('%H:%M:%S'),
                        'punch_type': get_punch_type_text(record.punch if hasattr(record, 'punch') else 0)
                    }
                    records.append(record_data)
            finally:
                conn.disconnect()
        else:
            records = selected_records

        # Sort records by timestamp
        records.sort(key=lambda x: x['timestamp'], reverse=True)

        # Prepare export data
        export_data = {
            'device_info': {
                'ip': session.get('device_ip'),
                'port': session.get('device_port'),
                'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'records': records
        }

        # Send data to external endpoint
        response = requests.post(
            export_url,
            json=export_data,
            verify=False  # Skip SSL verification
        )

        if response.ok:
            return jsonify({
                "status": "success", 
                "message": "Data exported successfully",
                "records_count": len(records)
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Export failed: {response.text}"
            }), 500

    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Add system settings endpoints
@app.route('/api/clear-data', methods=['POST'])
@require_device_connection
def clear_data():
    try:
        # Clear config files
        for file in os.listdir(CONFIG_DIR):
            os.remove(os.path.join(CONFIG_DIR, file))
        return jsonify({"status": "success", "message": "All data cleared successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reset-settings', methods=['POST'])
def reset_settings():
    try:
        # Reset export config
        config_file = get_config_path('export_config.json')
        if os.path.exists(config_file):
            os.remove(config_file)
        return jsonify({"status": "success", "message": "Settings reset successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# UI Endpoints
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/connect', methods=['GET', 'POST'])
def connect():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "No data provided"}), 400
            
            # Get connection parameters
            ip = data.get('ip')
            if not ip:
                return jsonify({"status": "error", "message": "IP address is required"}), 400
            
            try:
                port = int(data.get('port', 4370))
                timeout = int(data.get('timeout', 5))
            except ValueError:
                return jsonify({"status": "error", "message": "Port and timeout must be numbers"}), 400
            
            # Store connection details in session
            session['device_ip'] = ip
            session['device_port'] = port
            session['device_timeout'] = timeout
            
            # Try to connect to the device
            logger.info(f"Attempting to connect to device at {ip}:{port}")
            try:
                zk = ZK(ip, port=port, timeout=timeout)
                conn = zk.connect()
                
                # Get basic device info
                device_info = {
                    "firmware_version": conn.get_firmware_version(),
                    "serial_number": "Unknown",  # Not directly available
                    "platform": "ZKTeco Device",
                    "oem_vendor": "ZKTeco",
                    "mac": "Unknown"  # Not directly available
                }
                
                # Try to get additional info if available
                try:
                    device_info["serial_number"] = conn.get_serialnumber()
                except:
                    pass
                
                # Disconnect
                conn.disconnect()
                
                logger.info(f"Successfully connected to device: {device_info}")
                
                return jsonify({
                    "status": "success",
                    "message": "Successfully connected to device",
                    "device_info": device_info
                })
            except Exception as e:
                logger.error(f"Failed to connect to device: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": f"Failed to connect to device: {str(e)}"
                }), 400
        except Exception as e:
            logger.error(f"Error in connect endpoint: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Error processing request: {str(e)}"
            }), 500
    
    return render_template('connect.html')

@app.route('/disconnect')
def disconnect():
    # Clear session data
    session.pop('device_ip', None)
    session.pop('device_port', None)
    session.pop('device_timeout', None)
    
    return redirect(url_for('index'))

@app.route('/device')
def device():
    return render_template('device.html')

@app.route('/users')
def users():
    return render_template('users.html')

@app.route('/export')
def export():
    return render_template('export.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

# Add API endpoint for config
@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    config_file = 'export_config.json'
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Validate required fields
            if not data.get('attendance_api_url'):
                return jsonify({"status": "error", "message": "Attendance API URL is required"}), 400
                
            if not data.get('export_url'):
                return jsonify({"status": "error", "message": "Export API URL is required"}), 400
            
            # Read existing config if available
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
            except:
                config = {}
            
            # Update config with new values
            config['attendance_api_url'] = data.get('attendance_api_url')
            config['export_url'] = data.get('export_url')
            config['api_token'] = data.get('api_token', '')
            
            # Save updated config
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            return jsonify({"status": "success", "message": "Configuration saved successfully"})
            
        except Exception as e:
            return jsonify({"status": "error", "message": f"Failed to save configuration: {str(e)}"}), 500
    
    # GET request - return current config
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return jsonify(config)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to load configuration: {str(e)}"}), 500

@app.route('/api/send-attendance', methods=['POST'])
@require_device_connection
def send_attendance():
    try:
        # Get request parameters
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        # Read API URL from config file
        api_url = None
        try:
            with open('export_config.json', 'r') as f:
                config = json.load(f)
                if 'attendance_api_url' in config:
                    api_url = config['attendance_api_url']
                    logger.info(f"Using attendance API URL from config: {api_url}")
        except Exception as e:
            logger.warning(f"Could not read export_config.json: {str(e)}")
        
        # Validate API URL
        if not api_url:
            return jsonify({"status": "error", "message": "No API URL configured. Please set 'attendance_api_url' in export_config.json"}), 400
            
        # Validate URL format
        if not api_url.startswith(('http://', 'https://')):
            return jsonify({"status": "error", "message": f"Invalid API URL format: {api_url}. URL must start with http:// or https://"}), 400
            
        # Validate parameters
        if not data.get('start_date') or not data.get('end_date'):
            return jsonify({"status": "error", "message": "Start date and end date are required"}), 400
        
        logger.info(f"Sending attendance to API: {api_url}")
        logger.info(f"Date range: {data.get('start_date')} to {data.get('end_date')}")
        
        # Connect to device and get attendance records
        logger.info(f"Fetching attendance records from {data.get('start_date')} to {data.get('end_date')}")
        conn = connect_to_device()
        
        try:
            # Get all attendance records
            attendance_records = conn.get_attendance()
            logger.info(f"Retrieved {len(attendance_records) if attendance_records else 0} total attendance records")
            
            if not attendance_records:
                return jsonify({
                    "status": "success", 
                    "message": "No attendance records found in the specified date range",
                    "records_sent": 0
                })
            
            # Filter records by date range
            filtered_records = []
            for record in attendance_records:
                record_date = record.timestamp.strftime('%Y-%m-%d')
                if data.get('start_date') <= record_date <= data.get('end_date'):
                    filtered_records.append(record)
            
            logger.info(f"Filtered to {len(filtered_records)} records within date range {data.get('start_date')} to {data.get('end_date')}")
            
            if not filtered_records:
                return jsonify({
                    "status": "success", 
                    "message": "No attendance records found in the specified date range",
                    "records_sent": 0
                })
                
            # Format records for API according to the required format
            formatted_records = []
            for record in filtered_records:
                formatted_record = {
                    "emp_no": int(record.user_id),  # Convert to integer
                    "device_id": "FHGI9983",  # Use the specified device ID
                    "punch_type": get_punch_type_text(record.punch if hasattr(record, 'punch') else 0),
                    "punch_date": record.timestamp.strftime('%Y-%m-%d'),
                    "punch_time": record.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                formatted_records.append(formatted_record)
            
            # Log a sample record for debugging
            if formatted_records:
                logger.info(f"Sample record format: {json.dumps(formatted_records[0])}")
            
            # Prepare API request
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Use the exact format specified
            payload = {
                "data": formatted_records
            }
            
            logger.info(f"Sending {len(formatted_records)} records to API with specified format")
            logger.info(f"Payload structure: {json.dumps(payload)[:200]}...")
            
            try:
                # Make the API request
                logger.info(f"Sending POST request to: {api_url}")
                logger.info(f"Headers: {headers}")
                
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    verify=False,
                    timeout=30
                )
                
                logger.info(f"API response status: {response.status_code}")
                logger.info(f"API response content: {response.text[:500]}")
                
                if response.status_code in (200, 201, 202):
                    try:
                        response_data = response.json()
                        logger.info(f"Response parsed as JSON: {json.dumps(response_data)[:500]}")
                    except:
                        response_data = response.text
                        logger.info(f"Response is not JSON: {response_data[:500]}")
                    
                    # Consider any 2xx response as success
                    return jsonify({
                        "status": "success",
                        "message": f"Successfully sent {len(formatted_records)} attendance records to API",
                        "records_sent": len(formatted_records),
                        "api_response": response_data
                    })
                else:
                    # If the main request failed, try sending records one by one
                    logger.warning(f"Batch request failed with status {response.status_code}, trying individual records")
                    
                    successful_records = 0
                    failed_records = []
                    
                    for index, record in enumerate(formatted_records):
                        try:
                            # Try with single record wrapped in the data array
                            single_payload = {
                                "data": [record]
                            }
                            
                            logger.info(f"Sending record {index+1}/{len(formatted_records)}: {json.dumps(single_payload)}")
                            
                            single_response = requests.post(
                                api_url,
                                headers=headers,
                                json=single_payload,
                                verify=False,
                                timeout=30
                            )
                            
                            logger.info(f"Record {index+1} - API response status: {single_response.status_code}")
                            logger.info(f"Record {index+1} - API response content: {single_response.text[:200]}")
                            
                            if single_response.status_code in (200, 201, 202):
                                successful_records += 1
                                logger.info(f"Successfully sent record for emp_no {record['emp_no']}")
                            else:
                                logger.warning(f"Failed to send record for emp_no {record['emp_no']}: {single_response.status_code}")
                                failed_records.append({
                                    "emp_no": record['emp_no'],
                                    "status_code": single_response.status_code,
                                    "response": single_response.text[:100]
                                })
                        except Exception as e:
                            error_msg = str(e)
                            logger.error(f"Error sending individual record: {error_msg}")
                            failed_records.append({
                                "emp_no": record['emp_no'],
                                "error": error_msg
                            })
                        
                        # Don't overwhelm the API
                        time.sleep(0.5)
                    
                    if successful_records > 0:
                        return jsonify({
                            "status": "partial_success",
                            "message": f"Successfully sent {successful_records} out of {len(formatted_records)} attendance records to API individually",
                            "records_sent": successful_records,
                            "records_failed": len(formatted_records) - successful_records,
                            "total_records": len(formatted_records),
                            "failed_records": failed_records if failed_records else None
                        })
                    else:
                        return jsonify({
                            "status": "error",
                            "message": "Failed to send any attendance records to API",
                            "api_url": api_url,
                            "records_count": len(formatted_records),
                            "api_response": response.text[:500],
                            "failed_records": failed_records
                        }), 500
            except Exception as e:
                error_msg = f"Error sending attendance records to API: {str(e)}"
                logger.error(error_msg)
                return jsonify({"status": "error", "message": error_msg}), 500
                
        except Exception as e:
            error_msg = f"Error processing attendance records: {str(e)}"
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500
        finally:
            try:
                conn.disconnect()
                logger.info("Device disconnected")
            except Exception as e:
                logger.warning(f"Error disconnecting from device: {str(e)}")
    except Exception as e:
        error_msg = f"Error in send_attendance endpoint: {str(e)}"
        logger.error(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/api/test-api-connection', methods=['POST'])
def test_api_connection():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        api_url = data.get('api_url')
        api_token = data.get('api_token')
        
        # Read token from export_config.json if available
        try:
            with open('export_config.json', 'r') as f:
                config = json.load(f)
                if 'api_token' in config and not api_token:
                    api_token = config['api_token']
                    logger.info(f"Using token from export_config.json: {api_token[:10]}...")
                if 'export_url' in config and not api_url:
                    api_url = config['export_url']
                    logger.info(f"Using URL from export_config.json: {api_url}")
        except Exception as e:
            logger.warning(f"Could not read export_config.json: {str(e)}")
        
        # Validate parameters
        if not api_url:
            return jsonify({"status": "error", "message": "API URL is required"}), 400
            
        # Prepare test results
        test_results = []
        
        # Test 1: GET request to API URL
        try:
            # Check if token should be in URL or in payload
            url_has_token = "api_token=" in api_url
            test_url = api_url
            if not url_has_token and api_token:
                if "?" in api_url:
                    test_url = f"{api_url}&api_token={api_token}"
                else:
                    test_url = f"{api_url}?api_token={api_token}"
            
            logger.info(f"Testing GET request to {test_url}")
            
            response = requests.get(
                test_url,
                headers={"Accept": "application/json"},
                verify=False,
                timeout=10
            )
            
            test_results.append({
                "method": "GET",
                "url": test_url,
                "status": response.status_code,
                "response": response.text[:200] + ("..." if len(response.text) > 200 else "")
            })
            
            logger.info(f"GET test result: {response.status_code}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"GET test error: {error_msg}")
            test_results.append({
                "method": "GET",
                "url": test_url,
                "status": "Error",
                "response": error_msg
            })
        
        # Test 2: POST request with empty payload
        try:
            logger.info(f"Testing POST request to {test_url} with empty payload")
            
            response = requests.post(
                test_url,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                json={},
                verify=False,
                timeout=10
            )
            
            test_results.append({
                "method": "POST (Empty)",
                "url": test_url,
                "status": response.status_code,
                "response": response.text[:200] + ("..." if len(response.text) > 200 else "")
            })
            
            logger.info(f"POST empty test result: {response.status_code}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"POST empty test error: {error_msg}")
            test_results.append({
                "method": "POST (Empty)",
                "url": test_url,
                "status": "Error",
                "response": error_msg
            })
        
        # Test 3: POST request with sample payload
        try:
            logger.info(f"Testing POST request to {test_url} with sample payload")
            
            # Sample attendance record
            sample_record = {
                "emp_no": "12345",
                "punch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "punch_type": "IN",
                "terminal_id": "ZK",
                "source": "ZK_DEVICE"
            }
            
            # Try different payload formats
            payloads = [
                # Format 1: Direct array
                ("Direct array", sample_record),
                # Format 2: Using "attendance" key
                ("Attendance key", {"attendance": [sample_record]}),
                # Format 3: Using "data" key
                ("Data key", {"data": [sample_record]}),
                # Format 4: Using "records" key
                ("Records key", {"records": [sample_record]})
            ]
            
            # Try each payload format
            for name, payload in payloads:
                try:
                    response = requests.post(
                        test_url,
                        headers={"Content-Type": "application/json", "Accept": "application/json"},
                        json=payload,
                        verify=False,
                        timeout=10
                    )
                    
                    test_results.append({
                        "method": f"POST ({name})",
                        "url": test_url,
                        "status": response.status_code,
                        "response": response.text[:200] + ("..." if len(response.text) > 200 else "")
                    })
                    
                    logger.info(f"POST {name} test result: {response.status_code}")
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"POST {name} test error: {error_msg}")
                    test_results.append({
                        "method": f"POST ({name})",
                        "url": test_url,
                        "status": "Error",
                        "response": error_msg
                    })
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"POST sample test error: {error_msg}")
            test_results.append({
                "method": "POST (Sample)",
                "url": test_url,
                "status": "Error",
                "response": error_msg
            })
        
        # Determine overall status
        success_count = sum(1 for result in test_results if isinstance(result["status"], int) and 200 <= result["status"] < 300)
        
        if success_count > 0:
            overall_status = "success"
            message = f"API connection test completed with {success_count} successful tests out of {len(test_results)}"
        else:
            overall_status = "error"
            message = "API connection test failed. No successful connections established."
        
        return jsonify({
            "status": overall_status,
            "message": message,
            "test_results": test_results,
            "api_url": api_url
        })
        
    except Exception as e:
        error_msg = f"Error in test_api_connection endpoint: {str(e)}"
        logger.error(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/api/sync', methods=['POST'])
def sync_data():
    try:
        logger.info("Attempting to sync data")
        ip = request.form.get('ip', DEFAULT_IP)
        conn = connect_to_device(ip=ip)
        try:
            attendance_data = [{
                "emp_no": attendance.user_id,
                "punch_type": get_punch_type_text(attendance.punch if hasattr(attendance, 'punch') else 0),
                "punch_time": attendance.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            } for attendance in conn.get_attendance()]
            logger.info("Attendance data retrieved successfully")
            external_api_url = "http://external-api.example.com/sync"
            response = requests.post(external_api_url, json=attendance_data, timeout=10)
            logger.info("Data synced successfully")
            return jsonify({"status": "success", "external_response": response.text})
        except Exception as e:
            error_msg = f"Error syncing data: {str(e)}"
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500
        finally:
            try:
                conn.disconnect()
                logger.info("Device disconnected")
            except:
                logger.warning("Error disconnecting from device")
    except Exception as e:
        error_msg = f"Error in sync data endpoint: {str(e)}"
        logger.error(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

if __name__ == '__main__':
    try:
        # Use threaded=True for better handling of termination
        app.run(debug=True, port=5000, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        logger.info("Application shutdown requested. Exiting...")
    except Exception as e:
        # Log any other exceptions during startup/shutdown
        logger.error(f"Error in application: {str(e)}")
    finally:
        # Perform any cleanup needed
        logger.info("Application shutdown complete")