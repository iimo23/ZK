
from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash, has_request_context
from flask_cors import CORS
from zk import ZK, const
from datetime import datetime, timedelta
from collections import defaultdict
import requests
import logging
import os
import json
import sys
import time
import re
import threading
from functools import wraps

# Disable SSL warnings to clean up console output
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# Add context processor to provide 'now' variable to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Setup file handler with INFO level
file_handler = logging.FileHandler('app.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Setup console handler with WARNING level to reduce console output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Configure root logger
logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

# Get application logger
logger = logging.getLogger('zk-app')

# Set other loggers to WARNING level
logging.getLogger('zk').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

DEFAULT_PORT = 4370
DEFAULT_TIMEOUT = 5

# Define the exact path to config.json and devices.json
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
DEVICES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'devices.json')

# Create config directory if it doesn't exist
CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'config')
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

def get_config():
    """Get configuration from config.json file
    
    If the config file doesn't exist, creates it with default values
    """
    # Use the global CONFIG_PATH
    config_file = CONFIG_PATH
    logger.info(f"Loading config from: {config_file}")
    
    # Get registered devices if available
    registered_devices = {}
    devices_file = os.path.join(os.path.dirname(__file__), 'devices.json')
    logger.info(f"Checking for legacy devices file at: {devices_file}")
    if os.path.exists(devices_file):
        try:
            with open(devices_file, 'r') as f:
                registered_devices = json.load(f)
            logger.info(f"Loaded {len(registered_devices)} devices from legacy file")
        except Exception as e:
            logger.error(f"Error reading devices file: {str(e)}")
    
    # Default configuration
    default_config = {
        "attendance_api_url": "",  # Empty by default, will be set during first-time setup
        "registered_devices": registered_devices,
        "first_run": True  # Flag to indicate first-time run
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                
                # If config exists but doesn't have registered_devices, add them
                if "registered_devices" not in config and registered_devices:
                    config["registered_devices"] = registered_devices
                    save_config(config)
                    
                return config
        except Exception as e:
            logger.error(f"Error reading config file: {str(e)}")
            # If there's an error reading the file, create a new one with defaults
            logger.info("Creating new config file with default values")
            save_config(default_config)
            return default_config
    else:
        # First time running the app, create the config file
        logger.info("Config file not found. Creating with default values")
        save_config(default_config)
        return default_config

def save_config(config):
    """Save configuration to config.json file"""
    # Use the global CONFIG_PATH
    config_file = CONFIG_PATH
    logger.info(f"Saving config to: {config_file}")
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk
        logger.info(f"Config saved successfully to {config_file}")
    except Exception as e:
        logger.error(f"Error saving config file: {str(e)}")
        raise

def connect_to_device(device_id=None):
    """Connect to ZK device using the device manager
    
    Works both inside and outside of Flask request context.
    If device_id is provided, it will connect to that specific device.
    Otherwise, it will use the active device from the device manager.
    """
    # Import here to avoid circular imports
    from device_manager import device_manager
    
    # If no devices are registered, raise an error
    if not device_manager.get_all_devices():
        raise ValueError("No devices registered. Please add a device in the settings.")
    
    try:
        # Connect using device manager
        return device_manager.connect_to_device(device_id)
    except Exception as e:
        logger.error(f"Error connecting to device: {str(e)}")
        raise ConnectionError(f"Failed to connect to device: {str(e)}")

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
                'punch': get_punch_type_text(punch)
            })
        
        organized_records[user_id] = {
            'user_id': user_id,
            'daily_records': dict(daily_records)
        }
    
    return organized_records

def require_device_connection(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Import here to avoid circular imports
        from device_manager import device_manager
        
        # Check if we have any registered devices
        if not device_manager.get_all_devices():
            return jsonify({"status": "error", "message": "No devices registered. Please add a device in the settings."}), 400
        
        # Check if we have an active device
        active_device_id = device_manager.get_active_device_id()
        if not active_device_id:
            return jsonify({"status": "error", "message": "No active device selected. Please select a device in the settings."}), 400
        
        # All checks passed, continue with the function
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/device-info', methods=['GET'])
@require_device_connection
def get_device_info():
    try:
        conn = connect_to_device()
        info = conn.get_device_info()
        
        device_info = {
            "status": "success",
            "serial_number": info.serial_number,
            "oem_vendor": info.oem_vendor,
            "platform": info.platform,
            "firmware_version": info.firmware_version,
            "mac": info.mac
        }
        
        conn.disconnect()
        return jsonify(device_info)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/users', methods=['GET'])
@require_device_connection
def get_users():
    try:
        conn = connect_to_device()
        try:
            logger.info("Connected to device, fetching users...")
            users = conn.get_users()
            
            if not users:
                logger.warning("No users found on device")
                return jsonify({"status": "success", "users": []})
            
            logger.info(f"Found {len(users)} users")
            
            formatted_users = []
            for user in users:
                formatted_users.append({
                    "id": user.user_id,
                    "name": user.name,
                    "uid": user.uid,
                    "privilege": user.privilege,
                    "password": user.password if hasattr(user, 'password') else "",
                    "group_id": user.group_id if hasattr(user, 'group_id') else "",
                    "card": user.card if hasattr(user, 'card') else ""
                })
            
            logger.info(f"Successfully processed {len(formatted_users)} users")
            return jsonify({"status": "success", "users": formatted_users})
        finally:
            conn.disconnect()
            logger.info("Device disconnected")
    except Exception as e:
        error_msg = f"Error fetching users: {str(e)}"
        logger.error(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/api/attendance', methods=['GET'])
@require_device_connection
def get_attendance():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        emp_no = request.args.get('emp_no')
        
        logger.info(f"Getting attendance records: start_date={start_date}, end_date={end_date}, emp_no={emp_no}")
        
        conn = connect_to_device()
        try:
            attendance_records = conn.get_attendance()
            logger.info(f"Retrieved {len(attendance_records)} attendance records")
            
            if not attendance_records:
                return jsonify({"status": "success", "records": []})
            
            filtered_records = attendance_records
            if start_date or end_date:
                filtered_records = []
                start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else datetime.min
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date else datetime.max
                
                if end_date:
                    end_dt = end_dt.replace(hour=23, minute=59, second=59)
                
                for record in attendance_records:
                    if start_dt <= record.timestamp <= end_dt:
                        filtered_records.append(record)
            
            if emp_no:
                filtered_records = [r for r in filtered_records if str(r.user_id) == emp_no]
            
            formatted_records = []
            for record in filtered_records:
                formatted_records.append({
                    "user_id": record.user_id,
                    "timestamp": record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    "punch": get_punch_type_text(record.punch if hasattr(record, 'punch') else 0),
                    "status": record.status if hasattr(record, 'status') else 0,
                    "punch_type": record.punch if hasattr(record, 'punch') else 0
                })
            
            return jsonify({"status": "success", "attendance": formatted_records})
        finally:
            conn.disconnect()
            logger.info("Device disconnected")
    except Exception as e:
        error_msg = f"Error fetching attendance: {str(e)}"
        logger.error(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/api/users', methods=['POST'])
@require_device_connection
def add_user():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        user_id = data.get('id')
        name = data.get('name')
        
        if not user_id or not name:
            return jsonify({"status": "error", "message": "User ID and name are required"}), 400
        
        conn = connect_to_device()
        try:
            conn.set_user(
                user_id=user_id,
                name=name,
                privilege=data.get('privilege', 0),
                password=data.get('password', ''),
                group_id=data.get('group_id', 0),
                card=data.get('card', 0)
            )
            
            logger.info(f"User added successfully: ID={user_id}, Name={name}")
            return jsonify({"status": "success", "message": f"User {name} added successfully"})
        finally:
            conn.disconnect()
            logger.info("Device disconnected")
    except Exception as e:
        error_msg = f"Error adding user: {str(e)}"
        logger.error(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500


@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    try:
        data = request.json or {}
        ip = data.get('ip') or request.headers.get('X-Device-IP')
        port = data.get('port') or request.headers.get('X-Device-Port')
        timeout = data.get('timeout') or request.headers.get('X-Device-Timeout')
        
        if not ip:
            return jsonify({"status": "error", "message": "IP address is required"}), 400
        
        try:
            conn = connect_to_device(ip, port, timeout)
            info = conn.get_device_info()
            
            session['device_ip'] = ip
            if port:
                session['device_port'] = int(port)
            if timeout:
                session['device_timeout'] = int(timeout)
            
            conn.disconnect()
            return jsonify({
                "status": "success", 
                "message": f"Successfully connected to device at {ip}",
                "device_info": {
                    "serial_number": info.serial_number,
                    "firmware_version": info.firmware_version
                }
            })
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/send-attendance', methods=['POST'])
@require_device_connection
def send_attendance():
    try:
        from datetime import datetime
        # Get request parameters
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        # Read API URL from config using the get_config function
        config = get_config()
        api_url = config.get('attendance_api_url')
        logger.info(f"Retrieved config from get_config() function")
        
        # Placeholder for API logic - will be implemented below

        if api_url:
            logger.info(f"Using attendance API URL from config: {api_url}")
        else:
            logger.warning("API URL not found in configuration")
        
        # Validate API URL
        if not api_url:
            return jsonify({"status": "error", "message": "No API URL configured. Please set 'attendance_api_url' in config.json. Application directory: " + base_dir}), 400
            
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
                    "device_id": "111",  # Use the specified device ID
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
                    
                    # Save last_successful_send info to config.json
                    last_send_info = {
                        "last_send_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "last_send_data": {
                            "count": len(formatted_records),
                            "summary": f"Sent {len(formatted_records)} records",
                            "records_preview": formatted_records[:10]  # Store up to 10 records for display
                        }
                    }
                    config['last_successful_send'] = last_send_info
                    save_config(config)
                    logger.info("last_successful_send updated in config.json after batch send")
                    
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
                    successful_records_list = []  # Store the actual successful records
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
                                successful_records_list.append(record)  # Store the successful record
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
                        # Save last_successful_send info to config.json for individual records
                        last_send_info = {
                            "last_send_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "last_send_data": {
                                "count": successful_records,
                                "summary": f"Sent {successful_records} out of {len(formatted_records)} records individually",
                                "records_preview": successful_records_list[:10]  # Store up to 10 records for display
                            }
                        }
                        config['last_successful_send'] = last_send_info
                        save_config(config)
                        logger.info("last_successful_send updated in config.json after individual sends")
                        
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

def format_attendance_record(record):
    """Format a single attendance record for API submission."""
    return {
        "emp_no": int(record.user_id),
        "device_id": "111",
        "punch_type": get_punch_type_text(record.punch if hasattr(record, 'punch') else 0),
        "punch_date": record.timestamp.strftime('%Y-%m-%d'),
        "punch_time": record.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    }

def send_records_to_api(api_url, records, record_ids=None, is_batch=True):
    """Send attendance records to API, either as batch or individual record."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "data": records if is_batch else [records]
    }
    
    try:
        logger.info(f"Sending API request to: {api_url}")
        logger.debug(f"API request payload: {json.dumps(payload)[:200]}...")
        
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            verify=False,  # For development environments
            timeout=30
        )
        
        logger.info(f"API response status: {response.status_code}")
        try:
            logger.debug(f"API response content: {response.text[:200]}...")
        except:
            logger.debug("Could not log API response content")
        
        success = response.status_code in (200, 201, 202)
        return success, response
    except Exception as e:
        logger.error(f"API request error: {str(e)}")
        return False, None


@app.route('/api/add-users-from-url', methods=['POST'])
@require_device_connection
def add_users_from_url():
    """Add users to the ZK device by fetching data from an API URL
    
    Expected request format:
    {
        "url": "https://example.com/api/employees?api_token=your_token_here"
    }
    
    The API should return JSON data containing user records with emp_id and fpt_emp_name fields.
    The function will add each user to the device using their emp_id as the user_id.
    """
    try:
        # Get URL from request
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"status": "error", "message": "URL is required"}), 400
            
        url = data['url']
        logger.info(f"Fetching user data from URL: {url}")
        
        # Make the API request
        try:
            logger.info(f"Fetching data from URL: {url}")
            response = requests.get(url, verify=False)
            response.raise_for_status()
            response_data = response.json()
            logger.info(f"Received API response")

            # Extract users from the response
            users = []
            
            # Check if response is wrapped in a data object
            if isinstance(response_data, dict):
                if 'data' in response_data and isinstance(response_data['data'], list):
                    users = response_data['data']
                elif 'employees' in response_data and isinstance(response_data['employees'], list):
                    users = response_data['employees']
                elif 'emp_id' in response_data:
                    # Single user in response
                    users = [response_data]
                else:
                    # Try other common field names
                    for field in ['users', 'items', 'records']:
                        if field in response_data and isinstance(response_data[field], list):
                            users = response_data[field]
                            break
            elif isinstance(response_data, list):
                users = response_data

            if not users:
                return jsonify({"status": "error", "message": "No users data found in response"}), 400

            logger.info(f"Found {len(users)} users in API response")

            # Connect to device using the existing connection method
            conn = connect_to_device()
            
            try:
                # Get existing users and their user_ids
                existing_users = conn.get_users()
                existing_user_ids = {user.user_id: user.uid for user in existing_users}
                used_uids = {user.uid for user in existing_users}
                logger.info(f"Found {len(existing_users)} existing users on device")
                
                # Find next available uid starting from 1
                def get_next_uid():
                    uid = 1
                    while uid in used_uids and uid < 65535:
                        uid += 1
                    if uid >= 65535:
                        raise Exception("No available UIDs")
                    return uid
                
                # Process each user
                success_count = 0
                failed_users = []
                skipped_count = 0
                
                for user in users:
                    try:
                        # Skip detailed user logging to reduce console output
                        
                        # Get emp_id (required field)
                        emp_id = user.get('emp_id')
                        if not emp_id:
                            logger.warning(f"Missing emp_id for user: {user}")
                            failed_users.append({
                                'emp_id': None,
                                'name': None,
                                'error': 'Missing emp_id field',
                                'user_data': user
                            })
                            continue

                        # Convert emp_id to string
                        if not isinstance(emp_id, str):
                            emp_id = str(emp_id)
                        
                        # Get name from fpt_emp_name (can be null/empty)
                        # We'll use whatever value is provided, even if empty
                        name = user.get('fpt_emp_name', '')
                        if name is None:
                            name = ''  # Ensure name is at least an empty string, not None
                            
                        # Convert name to string if it's not already
                        if not isinstance(name, str):
                            name = str(name)
                        
                        # Check if user_id already exists
                        if emp_id in existing_user_ids:
                            # User already exists, skip without detailed logging
                            skipped_count += 1
                            continue
                        
                        # Get next available uid
                        new_uid = get_next_uid()
                        used_uids.add(new_uid)
                        
                        # Add new user to device
                        conn.set_user(
                            uid=new_uid,
                            name=name,
                            privilege=0,  # Use 0 for normal user
                            password='',
                            group_id='',
                            user_id=emp_id
                        )
                        # User added successfully
                        success_count += 1
                        existing_user_ids[emp_id] = new_uid
                        
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Error processing user: {error_msg}")
                        failed_users.append({
                            'emp_id': emp_id if 'emp_id' in locals() else None,
                            'name': name if 'name' in locals() else None,
                            'error': error_msg,
                            'user_data': user
                        })
            finally:
                # Always disconnect from device
                conn.disconnect()
                logger.info("Device disconnected")
            
            # Return results
            return jsonify({
                "status": "success" if success_count > 0 else "error",
                "message": f"Added {success_count} out of {len(users)} users to the device",
                "success_count": success_count,
                "failed_count": len(failed_users),
                "skipped_count": skipped_count,
                "failed_users": failed_users
            })
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch data from URL: {str(e)}"
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500
        except ValueError as e:
            error_msg = f"Invalid JSON response from URL: {str(e)}"
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500
            
    except Exception as e:
        error_msg = f"Unexpected error in add_users_from_url: {str(e)}"
        logger.error(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500


from device_manager import device_manager

# Define cleanup function to ensure proper shutdown
def cleanup_on_exit():
    # Force save devices to ensure they persist
    logger.info("Saving device configuration before exit")
    try:
        device_manager.save_devices()
        logger.info(f"Successfully saved {len(device_manager.devices)} devices before exit")
    except Exception as e:
        logger.error(f"Error saving devices on exit: {str(e)}")

# Register cleanup function to run on exit
import atexit
atexit.register(cleanup_on_exit)

# Import routes after all app setup is complete to avoid circular imports
from routes import *

if __name__ == '__main__':
    try:
        app.run(debug=True, port=5000, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Application shutdown requested. Exiting...")
    except Exception as e:
        logger.error(f"Error in application: {str(e)}")
    finally:
        logger.info("Application shutdown complete")