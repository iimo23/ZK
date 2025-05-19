from flask import render_template, redirect, url_for, jsonify, request, session, flash
import logging
import threading
import os
import json
import requests
from datetime import datetime, timedelta
from flask import jsonify, request

# Import app but not the other functions to avoid circular imports
from app import app, logger, connect_to_device, get_config, save_config
from device_manager import device_manager

@app.route('/api/employees-api-url', methods=['GET'])
def get_employees_api_url():
    """Get the employees API URL from config"""
    try:
        config = get_config()
        employees_api_url = config.get('employees_api_url', '')
        return jsonify({"status": "success", "employees_api_url": employees_api_url})
    except Exception as e:
        logger.error(f"Error getting employees API URL: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Global variable to track last sync timestamp
last_sync_timestamp = None

# UI Routes
@app.route('/')
def index():
    # Direct access to dashboard without setup wizard redirect
    return render_template('index.html')

# Setup wizard route removed

@app.route('/dashboard')
def dashboard():
    return redirect(url_for('index'))

@app.route('/connect', methods=['GET', 'POST'])
def connect():
    if request.method == 'POST':
        # Check if it's a JSON request (from fetch API) or form submission
        if request.is_json:
            data = request.get_json()
            device_name = data.get('device_name', 'New Device')
            ip = data.get('device_ip')
            port = data.get('device_port', 4370)
            timeout = data.get('timeout', 5)
        else:
            device_name = request.form.get('device_name', 'New Device')
            ip = request.form.get('device_ip')
            port = request.form.get('device_port', 4370)
            timeout = request.form.get('timeout', 5)
        
        if not ip:
            if request.is_json:
                return jsonify({"status": "error", "message": "IP address is required"}), 400
            else:
                return render_template('connect.html', error="IP address is required")
        
        try:
            # Create a new device ID
            device_id = f"device_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Add device to device manager
            device_manager.add_device(
                device_id=device_id,
                name=device_name,
                ip=ip,
                port=int(port) if port else 4370,
                timeout=int(timeout) if timeout else 5
            )
            
            # Set as active device
            device_manager.set_active_device(device_id)
            
            # Test connection
            connection_success = device_manager.test_connection(device_id)
            
            if not connection_success:
                # If connection failed, remove the device and return error
                device_manager.remove_device(device_id)
                error_msg = f"Could not connect to device at {ip}"
                
                if request.is_json:
                    return jsonify({"status": "error", "message": error_msg}), 400
                else:
                    return render_template('connect.html', error=error_msg)
            
            if request.is_json:
                return jsonify({
                    "status": "success", 
                    "message": f"Connected to device at {ip}",
                    "device_id": device_id
                })
            else:
                flash(f"Successfully connected to device at {ip}", "success")
                return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            
            if request.is_json:
                return jsonify({"status": "error", "message": str(e)}), 400
            else:
                return render_template('connect.html', error=f"Connection failed: {str(e)}")
    
    return render_template('connect.html')

@app.route('/users')
def users():
    # Render the user management page
    return render_template('users.html')

@app.route('/attendance')
def attendance():
    # Redirect to dashboard as attendance page is removed in simplified version
    return redirect(url_for('index'))

@app.route('/export')
def export():
    # Redirect to api_send as export page is removed in simplified version
    return redirect(url_for('api_send'))

@app.route('/api-send')
@app.route('/api_send')
def api_send():
    # Read last successful send from config
    last_send_info = None
    try:
        config = get_config()
        last_send_info = config.get('last_successful_send')
    except Exception as e:
        last_send_info = None
    return render_template('api_send.html', last_send_info=last_send_info)

@app.route('/settings')
def settings():
    return render_template('settings.html')

# Devices page removed - functionality moved to settings page

@app.route('/spa')
def spa():
    return app.send_static_file('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return app.send_static_file(path)

# API Endpoints
@app.route('/api/config', methods=['GET'])
def get_config_api():
    try:
        config = get_config()
        return jsonify({
            "status": "success",
            "data": config
        })
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/device-info', methods=['GET'])
def device_info_api():
    try:
        # Check if we have any registered devices
        if not device_manager.get_all_devices():
            return jsonify({
                "status": "error",
                "message": "No devices registered. Please add a device in the settings."
            }), 400
        
        # Get active device
        active_device_id = device_manager.get_active_device_id()
        if not active_device_id:
            return jsonify({
                "status": "error",
                "message": "No active device selected. Please select a device in the settings."
            }), 400
            
        # Get device details
        device = device_manager.get_device(active_device_id)
        
        # Return basic info even if we can't connect to the device
        device_info = {
            "id": active_device_id,
            "name": device.get('name', 'Unknown'),
            "ip": device.get('ip', 'Unknown'),
            "port": device.get('port', 4370),
            "last_sync": last_sync_timestamp.isoformat() if last_sync_timestamp else None,
            "last_connected": device.get('last_connected', None)
        }
        
        # Try to connect to device and get more info
        try:
            conn = connect_to_device()
            try:
                # Add additional device info
                device_info.update({
                    "serial_number": conn.get_serialnumber(),
                    "firmware_version": conn.get_firmware_version(),
                    "platform": conn.get_platform(),
                    "device_name": conn.get_device_name(),
                    "workcode": conn.get_workcode()
                })
            finally:
                conn.disconnect()
            
            # Connection successful
            return jsonify({
                "status": "success",
                "device_info": device_info
            })
        except Exception as conn_error:
            logger.warning(f"Could not connect to device for additional info: {str(conn_error)}")
            # Return basic info with warning
            return jsonify({
                "status": "warning",
                "device_info": device_info,
                "message": f"Device configured but connection failed: {str(conn_error)}"
            })
    except Exception as e:
        logger.error(f"Error in device info API: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/users', methods=['GET'])
def users_api():
    try:
        # Check if we have any registered devices
        if not device_manager.get_all_devices():
            return jsonify({
                "status": "error",
                "message": "No devices registered. Please add a device in the settings."
            }), 400
        
        # Get active device
        active_device_id = device_manager.get_active_device_id()
        if not active_device_id:
            return jsonify({
                "status": "error",
                "message": "No active device selected. Please select a device in the settings."
            }), 400
        
        try:
            # Connect to device using device manager
            conn = connect_to_device()
            try:
                users = conn.get_users()
                return jsonify({
                    "status": "success",
                    "users": [{
                        "user_id": user.user_id,
                        "name": user.name,
                        "privilege": user.privilege
                    } for user in users]
                })
            finally:
                conn.disconnect()
        except Exception as conn_error:
            logger.error(f"Error connecting to device: {str(conn_error)}")
            return jsonify({"status": "error", "message": f"Error connecting to device: {str(conn_error)}"}), 500
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user_api(user_id):
    try:
        if not user_id:
            return jsonify({"status": "error", "message": "User ID is required"}), 400
        
        # Check if we have any registered devices
        if not device_manager.get_all_devices():
            return jsonify({
                "status": "error",
                "message": "No devices registered. Please add a device in the settings."
            }), 400
        
        # Get active device
        active_device_id = device_manager.get_active_device_id()
        if not active_device_id:
            return jsonify({
                "status": "error",
                "message": "No active device selected. Please select a device in the settings."
            }), 400
            
        try:
            # Connect to device using device manager
            conn = connect_to_device()
            try:
                # Get existing users to verify the user exists
                users = conn.get_users()
                user_exists = any(user.user_id == user_id for user in users)
                
                if not user_exists:
                    return jsonify({"status": "error", "message": f"User with ID {user_id} not found"}), 404
                    
                # Delete the user
                conn.delete_user(user_id=user_id)
                logger.info(f"User {user_id} deleted successfully")
                
                return jsonify({
                    "status": "success",
                    "message": f"User {user_id} deleted successfully"
                })
            finally:
                conn.disconnect()
        except Exception as conn_error:
            logger.error(f"Error connecting to device: {str(conn_error)}")
            return jsonify({"status": "error", "message": f"Error connecting to device: {str(conn_error)}"}), 500
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/attendance', methods=['GET'])
def attendance_api():
    try:
        # Check if we have any registered devices
        if not device_manager.get_all_devices():
            return jsonify({
                "status": "error",
                "message": "No devices registered. Please add a device in the settings."
            }), 400
        
        # Get active device
        active_device_id = device_manager.get_active_device_id()
        if not active_device_id:
            return jsonify({
                "status": "error",
                "message": "No active device selected. Please select a device in the settings."
            }), 400
            
        try:
            # Connect to device using device manager
            conn = connect_to_device()
            try:
                # Get all users to map user_id to names
                users = conn.get_users()
                user_map = {user.user_id: user.name for user in users}
                
                # Get attendance records
                attendance = conn.get_attendance()
                
                # Format records with names
                formatted_records = []
                for record in attendance:
                    user_id = record.user_id
                    formatted_records.append({
                        "user_id": user_id,
                        "name": user_map.get(user_id, "Unknown"),  # Get name from user map or default to "Unknown"
                        "timestamp": record.timestamp.isoformat(),
                        "status": record.status,
                        "punch": record.punch,
                        "uid": record.uid
                    })
                
                return jsonify({"status": "success", "attendance": formatted_records})
            except Exception as conn_error:
                logger.error(f"Error processing attendance data: {str(conn_error)}")
                return jsonify({"status": "error", "message": f"Error processing attendance data: {str(conn_error)}"}), 500
            finally:
                conn.disconnect()
        except Exception as conn_error:
            logger.error(f"Error connecting to device: {str(conn_error)}")
            return jsonify({"status": "error", "message": f"Error connecting to device: {str(conn_error)}"}), 500
    except Exception as e:
        logger.error(f"Error getting attendance: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/connect', methods=['POST'])
def connect_api():
    try:
        data = request.get_json()
        if not data or not data.get('device_ip'):
            return jsonify({"status": "error", "message": "IP address is required"}), 400
        
        ip = data.get('device_ip')
        port = data.get('device_port', 4370)
        timeout = data.get('timeout', 5)
        device_name = data.get('device_name', f"Device {ip}")
        device_id = data.get('device_id')
        
        # If device_id is provided, use it to connect
        if device_id:
            # Check if device exists
            device = device_manager.get_device(device_id)
            if not device:
                return jsonify({"status": "error", "message": f"Device {device_id} not found"}), 404
            
            # Set as active device
            device_manager.set_active_device(device_id)
        else:
            # Create a new device ID
            device_id = f"device_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Add device to device manager
            device_manager.add_device(
                device_id=device_id,
                name=device_name,
                ip=ip,
                port=int(port) if port else 4370,
                timeout=int(timeout) if timeout else 5
            )
            
            # Set as active device
            device_manager.set_active_device(device_id)
        
        # Connect to device using device manager
        try:
            conn = connect_to_device()
            try:
                # Get device info
                device_info = {
                    "firmware_version": conn.get_firmware_version(),
                    "serial_number": conn.get_serialnumber(),
                    "platform": conn.get_platform(),
                    "device_name": conn.get_device_name(),
                    "work_code": conn.get_workcode(),
                    "users": len(conn.get_users()),
                    "attendance": len(conn.get_attendance())
                }
                
                logger.info(f"Connected to device at {ip}:{port}")
                return jsonify({
                    "status": "success", 
                    "message": f"Connected to device at {ip}",
                    "device_info": device_info,
                    "device_id": device_id
                })
            finally:
                conn.disconnect()
        except Exception as conn_error:
            logger.error(f"Error connecting to device: {str(conn_error)}")
            # If connection failed, remove the device if it was just created
            if not data.get('device_id'):
                try:
                    device_manager.remove_device(device_id)
                    logger.info(f"Removed device {device_id} due to connection failure")
                except Exception as e:
                    logger.error(f"Error removing device: {str(e)}")
            return jsonify({"status": "error", "message": f"Error connecting to device: {str(conn_error)}"}), 500
            
    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/send-attendance', methods=['POST'])
def send_attendance_api():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({"status": "error", "message": "Start date and end date are required"}), 400
        
        # Get attendance records for the date range
        try:
            conn = connect_to_device()
            attendance_records = conn.get_attendance()
            conn.disconnect()
            
            if not attendance_records:
                return jsonify({"status": "success", "message": "No records to send", "sent_count": 0})
            
            # Filter records by date range
            start_date_obj = datetime.fromisoformat(start_date) if 'T' in start_date else datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.fromisoformat(end_date) if 'T' in end_date else datetime.strptime(end_date, '%Y-%m-%d')
            end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
            
            filtered_records = [r for r in attendance_records if start_date_obj <= r.timestamp <= end_date_obj]
            
            if not filtered_records:
                return jsonify({"status": "success", "message": "No records found in the specified date range", "sent_count": 0})
            
            # Format records for API
            formatted_records = []
            for record in filtered_records:
                formatted_records.append({
                    "user_id": record.user_id,
                    "timestamp": record.timestamp.isoformat(),
                    "status": record.status,
                    "punch": record.punch,
                    "uid": record.uid
                })
            
            # Get API URL from config
            config = get_config()
            attendance_api_url = config.get('attendance_api_url')
            
            if not attendance_api_url:
                return jsonify({"status": "error", "message": "API URL not configured"}), 400
            
            # Send records to API
            try:
                response = requests.post(attendance_api_url, json={
                    "records": formatted_records
                }, timeout=10)
                
                if response.status_code == 200:
                    return jsonify({
                        "status": "success", 
                        "message": "Records sent successfully", 
                        "sent_count": len(formatted_records)
                    })
                else:
                    return jsonify({
                        "status": "error", 
                        "message": f"API returned error: {response.text}", 
                        "status_code": response.status_code
                    }), 400
            except Exception as e:
                logger.error(f"Error sending records to API: {str(e)}")
                return jsonify({"status": "error", "message": f"Error sending records to API: {str(e)}"}), 500
        except Exception as e:
            logger.error(f"Error getting attendance records: {str(e)}")
            return jsonify({"status": "error", "message": f"Error getting attendance records: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Error in send attendance API: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def stats_api():
    try:
        # Check if device is connected
        if not session.get('device_ip'):
            return jsonify({
                "status": "success",
                "data": {
                    "today_attendance": 0,
                    "total_users": 0,
                    "present_today": 0,
                    "last_sync": None
                }
            })
        
        # Connect to device and get data
        conn = connect_to_device()
        try:
            # Get attendance records
            attendance_records = conn.get_attendance()
            
            # Filter for today's records
            today = datetime.now().strftime('%Y-%m-%d')
            today_records = [r for r in attendance_records if r.timestamp.strftime('%Y-%m-%d') == today]
            
            # Get unique users who checked in today
            present_users = set(r.user_id for r in today_records)
            
            # Get all users
            users = conn.get_users()
            
            return jsonify({
                "status": "success",
                "data": {
                    "today_attendance": len(today_records),
                    "total_users": len(users),
                    "present_today": len(present_users),
                    "last_sync": last_sync_timestamp.isoformat() if last_sync_timestamp else None
                }
            })
        finally:
            conn.disconnect()
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({
            "status": "success",
            "data": {
                "today_attendance": 0,
                "total_users": 0,
                "present_today": 0,
                "last_sync": last_sync_timestamp.isoformat() if last_sync_timestamp else None
            }
        })

@app.route('/api/config-settings', methods=['GET', 'POST'])
def config_settings_api():
    """API endpoint for managing configuration settings"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            logger.info(f"Received API config data: {data}")
            if not data:
                return jsonify({"status": "error", "message": "No data provided"}), 400

            # Get current config
            config = get_config()

            # Extract base_api_url and api_token from the request
            base_api_url = data.get('base_api_url', '').rstrip('/')
            api_token = data.get('api_token', '')

            if not base_api_url or not api_token:
                return jsonify({"status": "error", "message": "Both base_api_url and api_token are required."}), 400

            # Store base_api_url and api_token in config
            config['base_api_url'] = base_api_url
            config['api_token'] = api_token

            # Construct new API URLs
            attendance_api_url = f"{base_api_url}/attendance?token={api_token}"
            employees_api_url = f"{base_api_url}/employees?token={api_token}"
            config['attendance_api_url'] = attendance_api_url
            config['employees_api_url'] = employees_api_url

            # Save updated config
            logger.info(f"Updated config before saving: {config}")
            save_config(config)

            return jsonify({
                "status": "success",
                "message": "Configuration saved successfully"
            })
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        try:
            # Get current config
            config = get_config()
            
            return jsonify({"status": "success", "config": config})
        except Exception as e:
            logger.error(f"Error getting configuration: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/export-config', methods=['GET', 'POST'])
def export_config_api():
    """Redirect to the new config-settings endpoint for backward compatibility"""
    return config_settings_api()


@app.route('/api/test-connection', methods=['POST'])
def test_connection_api():
    try:
        data = request.get_json()
        if not data or not data.get('attendance_api_url'):
            return jsonify({"status": "error", "message": "API URL is required"}), 400
        
        attendance_api_url = data.get('attendance_api_url')
        
        # Try to connect to the API
        try:
            response = requests.get(attendance_api_url, timeout=5)
            if response.status_code == 200:
                return jsonify({"status": "success", "message": "Connection successful"})
            else:
                return jsonify({"status": "error", "message": f"API returned status code: {response.status_code}"}), 400
        except requests.exceptions.RequestException as e:
            return jsonify({"status": "error", "message": f"Connection error: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Error testing connection: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Device Management API Endpoints

@app.route('/api/devices', methods=['GET'])
def get_devices_api():
    try:
        # Get all registered devices
        devices = device_manager.get_all_devices()
        
        # Get active device ID
        active_device_id = device_manager.get_active_device_id()
        
        return jsonify({
            "status": "success",
            "devices": devices,
            "active_device": active_device_id
        })
    except Exception as e:
        logger.error(f"Error getting devices: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/devices', methods=['POST'])
def add_device_api():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        device_id = data.get('device_id')
        name = data.get('name')
        ip = data.get('ip')
        port = data.get('port', 4370)
        timeout = data.get('timeout', 5)
        
        if not device_id or not name or not ip:
            return jsonify({"status": "error", "message": "Device ID, name, and IP address are required"}), 400
        
        # Add device to manager
        device_manager.add_device(device_id, name, ip, port, timeout)
        
        # Test connection
        connection_success = device_manager.test_connection(device_id)
        
        if connection_success:
            # Set as active device
            device_manager.set_active_device(device_id)
            return jsonify({
                "status": "success",
                "message": f"Device {name} added successfully and set as active",
                "device_id": device_id
            })
        else:
            return jsonify({
                "status": "warning",
                "message": f"Device {name} added but connection test failed",
                "device_id": device_id
            })
    except Exception as e:
        logger.error(f"Error adding device: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/devices/<device_id>', methods=['GET'])
def get_device_api(device_id):
    try:
        device = device_manager.get_device(device_id)
        if not device:
            return jsonify({"status": "error", "message": f"Device {device_id} not found"}), 404
        
        return jsonify({
            "status": "success",
            "device": device
        })
    except Exception as e:
        logger.error(f"Error getting device: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/devices/<device_id>', methods=['PUT'])
def update_device_api(device_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        device = device_manager.get_device(device_id)
        if not device:
            return jsonify({"status": "error", "message": f"Device {device_id} not found"}), 404
        
        # Update device properties
        name = data.get('name', device['name'])
        ip = data.get('ip', device['ip'])
        port = data.get('port', device['port'])
        timeout = data.get('timeout', device['timeout'])
        
        # Update device in manager
        device_manager.add_device(device_id, name, ip, port, timeout)
        
        return jsonify({
            "status": "success",
            "message": f"Device {name} updated successfully",
            "device_id": device_id
        })
    except Exception as e:
        logger.error(f"Error updating device: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/devices/<device_id>', methods=['DELETE'])
def delete_device_api(device_id):
    try:
        if not device_manager.get_device(device_id):
            return jsonify({"status": "error", "message": f"Device {device_id} not found"}), 404
        
        # Remove device from manager
        device_manager.remove_device(device_id)
        
        return jsonify({
            "status": "success",
            "message": f"Device {device_id} deleted successfully"
        })
    except Exception as e:
        logger.error(f"Error deleting device: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/devices/<device_id>/set-active', methods=['POST'])
def set_active_device_api(device_id):
    try:
        if not device_manager.get_device(device_id):
            return jsonify({"status": "error", "message": f"Device {device_id} not found"}), 404
        
        # Set as active device
        device_manager.set_active_device(device_id)
        
        return jsonify({
            "status": "success",
            "message": f"Device {device_id} set as active"
        })
    except Exception as e:
        logger.error(f"Error setting active device: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/devices/<device_id>/test-connection', methods=['POST'])
def test_device_connection_api(device_id):
    try:
        if not device_manager.get_device(device_id):
            return jsonify({"status": "error", "message": f"Device {device_id} not found"}), 404
        
        # Test connection
        connection_success = device_manager.test_connection(device_id)
        
        if connection_success:
            return jsonify({
                "status": "success",
                "message": f"Connection to device {device_id} successful"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Connection to device {device_id} failed"
            }), 400
    except Exception as e:
        logger.error(f"Error testing device connection: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Setup API endpoint removed
