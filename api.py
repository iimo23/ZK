from flask import Flask, jsonify, request
from flask_cors import CORS
from zk import ZK, const
from datetime import datetime
from collections import defaultdict
import requests

app = Flask(__name__)
CORS(app)

def get_punch_type_text(punch_type):
    """Convert punch type to readable text"""
    punch_dict = {
        0: "1",
        1: "2",
        2: "3",
        3: "4",
        4: "5",
        5: "6"
    }
    return punch_dict.get(punch_type, "Unknown")

def organize_attendance(attendance_records):
    """Organize attendance records by user and date"""
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
            date: {
                "records": sorted(times, key=lambda x: x['time'])
            }
            for date, times in daily_records.items()
        }
    
    return organized_records

@app.route('/device-info', methods=['GET'])
def get_device_info():
    try:
        zk = ZK('192.168.37.10', port=4370, timeout=5)
        conn = zk.connect()
        
        if conn:
            info = {
                "firmware_version": conn.get_firmware_version(),
                "serial_number": conn.get_serialnumber()
            }
            conn.disconnect()
            return jsonify({"status": "success", "data": info})
        
        return jsonify({"status": "error", "message": "Could not connect to device"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/users', methods=['GET'])
def get_users():
    try:
        zk = ZK('192.168.37.10', port=4370, timeout=5)
        conn = zk.connect()
        
        if not conn:
            return jsonify({"status": "error", "message": "Could not connect to device"}), 500
            
        try:
            users = conn.get_users()
            user_list = []
            
            for user in users:
                print(f"Raw user data - uid: {user.uid}, user_id: {user.user_id}, name: {user.name}, privilege: {user.privilege}")
                user_list.append({
                    'uid': user.uid,
                    'emp_no': user.user_id,
                    'name': user.name,
                    'privilege': user.privilege,
                })
            
            return jsonify({
                "status": "success",
                "data": user_list
            })
            
        finally:
            conn.disconnect()
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/user/<uid>', methods=['GET'])
def get_user_details(uid):
    try:
        zk = ZK('192.168.37.10', port=4370, timeout=5)
        conn = zk.connect()
        
        if not conn:
            return jsonify({"status": "error", "message": "Could not connect to device"}), 500
            
        try:
            users = conn.get_users()
            target_uid = int(uid)
            
            for user in users:
                if user.uid == target_uid:
                    print(f"Found user - Full details:")
                    print(f"UID: {user.uid}")
                    print(f"User ID: {user.user_id}")
                    print(f"Name: {user.name}")
                    print(f"Privilege: {user.privilege}")
                    print(f"Password: {user.password}")
                    print(f"Group ID: {user.group_id}")
                    
                    return jsonify({
                        "status": "success",
                        "data": {
                            'uid': user.uid,
                            'user_id': user.user_id,
                            'name': user.name,
                            'privilege': user.privilege,
                            'group_id': user.group_id
                        }
                    })
            
            return jsonify({"status": "error", "message": f"User with UID {uid} not found"}), 404
            
        finally:
            conn.disconnect()
            
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid UID format"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/attendance', methods=['GET'])
def get_attendance():
    try:
        zk = ZK('192.168.37.10', port=4370, timeout=5)
        conn = zk.connect()
        
        if conn:
            attendances = conn.get_attendance()
            attendance_data = []
            
            for attendance in attendances:
                punch = attendance.punch if hasattr(attendance, 'punch') else 0
                record = {
                    "emp_no": attendance.user_id,
                    "device_id": conn.get_serialnumber(),
                    "punch_type": get_punch_type_text(punch),
                    "punch_date": attendance.timestamp.strftime('%Y-%m-%d'),
                    "punch_time": attendance.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                attendance_data.append(record)
            
            conn.disconnect()
            return jsonify({"data": attendance_data})
        
        return jsonify({"status": "error", "message": "Could not connect to device"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/user/<user_id>', methods=['GET'])
def get_user_by_id(user_id):
    try:
        zk = ZK('192.168.37.10', port=4370, timeout=5)
        conn = zk.connect()
        
        if conn:
            # Get user information
            users = conn.get_users()
            user = next((u for u in users if str(u.uid) == str(user_id)), None)
            
            if not user:
                return jsonify({
                    "status": "error",
                    "message": f"User with ID {user_id} not found"
                }), 404
            
            # Get user's attendance records
            attendance = conn.get_attendance()
            user_attendance = [
                record for record in attendance 
                if str(record.user_id) == str(user_id)
            ]
            
            # Organize attendance records by date
            organized_records = organize_attendance(user_attendance)
            
            # Format the response
            user_data = {
                "user_info": {
                    "uid": user.uid,
                    "name": user.name,
                    "privilege": "Admin" if user.privilege == const.USER_ADMIN else "User",
                    "password": user.password,
                    "card": user.card
                },
                "attendance": organized_records[str(user_id)],
                "total_attendance_records": len(user_attendance)
            }
            
            conn.disconnect()
            return jsonify({"status": "success", "data": user_data})
        
        return jsonify({"status": "error", "message": "Could not connect to device"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/add-users-url', methods=['POST'])
def add_users():
    try:
        # Get data from request body
        request_data = request.get_json()
        print(f"Received request data: {request_data}")
        
        if not request_data:
            return jsonify({"status": "error", "message": "Request body is required"}), 400
            
        # Get URL from request body
        url = request_data.get('url')
        print(f"URL from request: {url}")
            
        if not url:
            return jsonify({"status": "error", "message": "url is required in request body"}), 400

        # Get users data from the URL
        try:
            print(f"Fetching data from URL: {url}")
            response = requests.get(url, verify=False)
            response.raise_for_status()
            response_data = response.json()
            print(f"Raw response data: {response_data}")

            # Check if response is wrapped in a data object
            if isinstance(response_data, dict):
                users = response_data.get('data', [])
                if not users:
                    users = response_data.get('employees', [])
            else:
                users = response_data

            if not users:
                return jsonify({"status": "error", "message": "No users data found in response"}), 500

            print(f"Extracted users data: {users}")

        except requests.RequestException as e:
            error_msg = f"Failed to fetch data from URL: {str(e)}"
            print(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500
        except ValueError as e:
            error_msg = f"Invalid JSON response from URL: {str(e)}"
            print(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500

        if not isinstance(users, list):
            error_msg = f"Invalid response format. Expected JSON array of users, got {type(users)}"
            print(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500

        # Connect to ZK device
        print("Connecting to ZK device...")
        zk = ZK('192.168.37.10', port=4370, timeout=5)
        conn = zk.connect()
        
        if not conn:
            return jsonify({"status": "error", "message": "Could not connect to device"}), 500

        try:
            print("Successfully connected to device")
            
            # Get existing users and their user_ids
            existing_users = conn.get_users()
            existing_user_ids = {user.user_id: user.uid for user in existing_users}
            used_uids = {user.uid for user in existing_users}
            print(f"Existing user_ids: {existing_user_ids}")
            print(f"Used UIDs: {used_uids}")
            
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
            
            for user in users:
                try:
                    print(f"Processing user: {user}")
                    emp_id = str(user.get('emp_id'))
                    name = user.get('fpt_emp_name', '').strip()
                    
                    if not emp_id:
                        error_msg = 'Missing emp_id field'
                        print(f"Error for user {user}: {error_msg}")
                        failed_users.append({
                            'emp_id': emp_id,
                            'name': name,
                            'error': error_msg
                        })
                        continue

                    if not name:
                        error_msg = 'Missing fpt_emp_name field'
                        print(f"Error for user {user}: {error_msg}")
                        failed_users.append({
                            'emp_id': emp_id,
                            'name': name,
                            'error': error_msg
                        })
                        continue
                    
                    # Check if user_id already exists
                    if emp_id in existing_user_ids:
                        print(f"User {emp_id} already exists with uid {existing_user_ids[emp_id]}")
                        continue
                    
                    # Get next available uid
                    new_uid = get_next_uid()
                    used_uids.add(new_uid)
                    
                    # Add new user to device
                    print(f"Adding user to device: ID={emp_id}, Name={name}, UID={new_uid}")
                    conn.set_user(
                        uid=new_uid,
                        name=name,
                        privilege=0,  # Use 0 for normal user
                        password='',
                        group_id='',
                        user_id=emp_id
                    )
                    print(f"Successfully added user: {emp_id} with uid={new_uid}")
                    success_count += 1
                    existing_user_ids[emp_id] = new_uid
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"Error processing user data: {error_msg}")
                    failed_users.append({
                        'emp_id': emp_id if 'emp_id' in locals() else 'unknown',
                        'name': name if 'name' in locals() else 'unknown',
                        'error': error_msg
                    })
            
            result = {
                "status": "success" if success_count > 0 else "error",
                "data": {
                    "added_users": success_count,
                    "failed_users": failed_users,
                    "total_processed": len(users),
                    "skipped_existing": len(users) - (success_count + len(failed_users))
                }
            }
            print(f"Final result: {result}")
            return jsonify(result)
            
        finally:
            print("Disconnecting from device")
            conn.disconnect()
            
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/add-user', methods=['POST'])
def add_single_user():
    try:
        # Get data from request body
        user_data = request.get_json()
        print(f"Received user data: {user_data}")
        
        if not user_data:
            return jsonify({"status": "error", "message": "Request body is required"}), 400
            
        # Get required fields
        emp_no = str(user_data.get('emp_no', ''))
        name = str(user_data.get('name', '')).strip()
        privilege = int(user_data.get('privilege', 0))  # 0 for normal user, 14 for admin
            
        if not emp_no:
            return jsonify({"status": "error", "message": "emp_no is required"}), 400
            
        if not name:
            return jsonify({"status": "error", "message": "name is required"}), 400
            
        if privilege not in [0, 14]:  # Only allow normal user or admin
            return jsonify({"status": "error", "message": "privilege must be 0 (normal user) or 14 (admin)"}), 400

        # Connect to ZK device
        print("Connecting to ZK device...")
        zk = ZK('192.168.37.10', port=4370, timeout=5)
        conn = zk.connect()
        
        if not conn:
            return jsonify({"status": "error", "message": "Could not connect to device"}), 500

        try:
            # Get existing users to check emp_no and find available uid
            existing_users = conn.get_users()
            existing_user_ids = {user.user_id: user.uid for user in existing_users}
            used_uids = {user.uid for user in existing_users}
            
            # Check if user already exists
            if emp_no in existing_user_ids:
                return jsonify({
                    "status": "error",
                    "message": f"User with emp_no {emp_no} already exists",
                    "existing_user": {
                        "emp_no": emp_no,
                        "uid": existing_user_ids[emp_no]
                    }
                }), 409
            
            # Find next available uid
            new_uid = 1
            while new_uid in used_uids and new_uid < 65535:
                new_uid += 1
                
            if new_uid >= 65535:
                return jsonify({"status": "error", "message": "No available UIDs in device"}), 500
            
            print(f"Adding user - emp_no: {emp_no}, name: {name}, uid: {new_uid}, privilege: {privilege}")
            
            # Add user to device
            conn.set_user(
                uid=new_uid,
                name=name,
                privilege=privilege,
                password='',
                group_id='',
                user_id=emp_no
            )
            
            return jsonify({
                "status": "success",
                "data": {
                    "message": "User added successfully",
                    "user": {
                        "emp_no": emp_no,
                        "name": name,
                        "uid": new_uid,
                        "privilege": "Admin" if privilege == 14 else "User"
                    }
                }
            })
            
        finally:
            print("Disconnecting from device")
            conn.disconnect()
            
    except ValueError as ve:
        error_msg = f"Invalid data format: {str(ve)}"
        print(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 400
    except Exception as e:
        error_msg = f"Error adding user: {str(e)}"
        print(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/delete-user/<emp_no>', methods=['DELETE'])
def delete_user(emp_no):
    try:
        print(f"Attempting to delete user with emp_no: {emp_no}")
        
        # Connect to ZK device
        zk = ZK('192.168.37.10', port=4370, timeout=5)
        conn = zk.connect()
        
        if not conn:
            return jsonify({"status": "error", "message": "Could not connect to device"}), 500

        try:
            # Get all users to find the one with matching emp_no
            users = conn.get_users()
            target_user = None
            
            for user in users:
                if user.user_id == emp_no:
                    target_user = user
                    break
            
            if not target_user:
                return jsonify({
                    "status": "error",
                    "message": f"User with emp_no {emp_no} not found"
                }), 404
            
            print(f"Found user to delete - uid: {target_user.uid}, emp_no: {target_user.user_id}, name: {target_user.name}")
            
            # Delete the user using their uid
            conn.delete_user(uid=target_user.uid)
            
            return jsonify({
                "status": "success",
                "data": {
                    "message": f"User deleted successfully",
                    "deleted_user": {
                        "emp_no": target_user.user_id,
                        "name": target_user.name,
                        "uid": target_user.uid
                    }
                }
            })
            
        finally:
            print("Disconnecting from device")
            conn.disconnect()
            
    except Exception as e:
        error_msg = f"Error deleting user: {str(e)}"
        print(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
