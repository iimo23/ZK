from flask import Flask, jsonify, request
from flask_cors import CORS
from zk import ZK, const
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
CORS(app)

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
            date = record.timestamp.strftime('%Y-%m-%d')
            daily_records[date].append(record.timestamp.strftime('%H:%M:%S'))
        
        organized_records[str(user_id)] = {
            date: {
                "check_in": min(times),
                "check_out": max(times)
            }
            for date, times in daily_records.items()
        }
    
    return organized_records

def get_status_text(status):
    """Convert status code to readable text"""
    status_dict = {
        1: "Check In",
        2: "Check Out",
        3: "Break Out",
        4: "Break In",
        5: "Overtime In",
        6: "Overtime Out",
        15: "Invalid Status"
    }
    return status_dict.get(status, "Unknown")

@app.route('/device-info', methods=['GET'])
def get_device_info():
    try:
        zk = ZK('192.168.37.11', port=4370, timeout=5)
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
        zk = ZK('192.168.37.11', port=4370, timeout=5)
        conn = zk.connect()
        
        if conn:
            users = conn.get_users()
            users_data = [{
                "uid": user.uid,
                "name": user.name,
                "privilege": "Admin" if user.privilege == const.USER_ADMIN else "User",
                "password": user.password,
                "card": user.card
            } for user in users]
            conn.disconnect()
            return jsonify({"status": "success", "data": users_data})
        
        return jsonify({"status": "error", "message": "Could not connect to device"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/attendance', methods=['GET'])
def get_attendance():
    try:
        zk = ZK('192.168.37.11', port=4370, timeout=5)
        conn = zk.connect()
        
        if conn:
            # Get users for mapping
            users = {str(user.uid): user.name for user in conn.get_users()}
            
            # Get attendance records
            attendance = conn.get_attendance()
            
            # Group records by date and user
            daily_records = {}
            
            # First, sort all records by timestamp
            sorted_records = sorted(attendance, key=lambda x: x.timestamp)
            
            for record in sorted_records:
                attendancedate = record.timestamp.strftime('%Y-%m-%d')
                user_id = str(record.user_id)
                punchtime = record.punch
                
                if attendancedate not in daily_records:
                    daily_records[attendancedate] = {}
                
                if user_id not in daily_records[attendancedate]:
                    daily_records[attendancedate][user_id] = {
                        "user_id": user_id,
                        "user_name": users.get(user_id, f"Unknown User {user_id}"),
                        "attendance_records": []
                    }
                
                # Add the record with its punch type
                daily_records[attendancedate][user_id]["attendance_records"].append({
                    "timestamp": record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    "punch_type": "Check Out" if punchtime == 1 else "Check In",
                    "punchtime": punchtime
                })
            
            # Format the final output
            attendance_data = []
            for attendancedate in sorted(daily_records.keys(), reverse=True):
                user_records = []
                
                for user_id, data in daily_records[attendancedate].items():
                    # Sort records by timestamp
                    data["attendance_records"].sort(key=lambda x: x["timestamp"])
                    
                    user_records.append({
                        "user_id": data["user_id"],
                        "user_name": data["user_name"],
                        "attendance_records": data["attendance_records"]
                    })
                
                attendance_data.append({
                    "attendancedate": attendancedate,
                    "records": user_records,
                    "total_users": len(user_records)
                })
            
            conn.disconnect()
            return jsonify({
                "status": "success",
                "data": attendance_data,
                "total_days": len(attendance_data)
            })
        
        return jsonify({"status": "error", "message": "Could not connect to device"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/user/<user_id>', methods=['GET'])
def get_user_by_id(user_id):
    try:
        zk = ZK('192.168.37.11', port=4370, timeout=5)
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
            daily_records = defaultdict(list)
            for record in user_attendance:
                date = record.timestamp.strftime('%Y-%m-%d')
                daily_records[date].append(record.timestamp.strftime('%H:%M:%S'))
            
            # Format the response
            user_data = {
                "user_info": {
                    "uid": user.uid,
                    "name": user.name,
                    "privilege": "Admin" if user.privilege == const.USER_ADMIN else "User",
                    "password": user.password,
                    "card": user.card
                },
                "attendance": {
                    date: {
                        "check_in": min(times),
                        "check_out": max(times)
                    }
                    for date, times in daily_records.items()
                },
                "total_attendance_records": len(user_attendance)
            }
            
            conn.disconnect()
            return jsonify({
                "status": "success",
                "data": user_data
            })
        
        return jsonify({"status": "error", "message": "Could not connect to device"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/attendance/search', methods=['GET'])
def search_attendance():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        start_datetime = None
        end_datetime = datetime.now()
        
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid start_date format (YYYY-MM-DD)"}), 400
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid end_date format (YYYY-MM-DD)"}), 400
        
        if start_datetime and start_datetime > end_datetime:
            return jsonify({"status": "error", "message": "start_date cannot be later than end_date"}), 400
        
        zk = ZK('192.168.37.11', port=4370, timeout=5)
        conn = zk.connect()
        
        if not conn:
            return jsonify({"status": "error", "message": "Could not connect to device"})
        
        users = {str(user.uid): user.name for user in conn.get_users()}
        attendance = conn.get_attendance()
        daily_records = {}
        
        for record in sorted(
            [r for r in attendance if (not start_datetime or start_datetime <= r.timestamp) 
             and (r.timestamp <= end_datetime)],
            key=lambda x: x.timestamp
        ):
            attendancedate = record.timestamp.strftime('%Y-%m-%d')
            user_id = str(record.user_id)
            
            if attendancedate not in daily_records:
                daily_records[attendancedate] = {}
            
            if user_id not in daily_records[attendancedate]:
                daily_records[attendancedate][user_id] = {
                    "user_id": user_id,
                    "user_name": users.get(user_id, f"Unknown User {user_id}"),
                    "attendance_records": []
                }
            
            daily_records[attendancedate][user_id]["attendance_records"].append({
                "timestamp": record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "punch_type": "Check Out" if record.punch == 1 else "Check In",
                "punchtime": record.punch
            })
        
        attendance_data = []
        for attendancedate in sorted(daily_records.keys(), reverse=True):
            user_records = []
            for user_id, data in daily_records[attendancedate].items():
                data["attendance_records"].sort(key=lambda x: x["timestamp"])
                user_records.append(data)
            
            attendance_data.append({
                "attendancedate": attendancedate,
                "records": user_records,
                "total_users": len(user_records)
            })
        
        conn.disconnect()
        
        return jsonify({
            "status": "success",
            "data": attendance_data,
            "total_days": len(attendance_data),
            "search_params": {
                "start_date": start_date or "All past records",
                "end_date": end_date or end_datetime.strftime('%Y-%m-%d')
            }
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/attendance/user', methods=['GET'])
def search_user_attendance():
    try:
        user_id = request.args.get('user_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not user_id:
            return jsonify({"status": "error", "message": "user_id is required"}), 400
            
        start_datetime = None
        end_datetime = datetime.now()
        
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid start_date format (YYYY-MM-DD)"}), 400
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid end_date format (YYYY-MM-DD)"}), 400
        
        if start_datetime and start_datetime > end_datetime:
            return jsonify({"status": "error", "message": "start_date cannot be later than end_date"}), 400
        
        zk = ZK('192.168.37.11', port=4370, timeout=5)
        conn = zk.connect()
        
        if not conn:
            return jsonify({"status": "error", "message": "Could not connect to device"})
        
        users = {str(user.uid): user.name for user in conn.get_users()}
        if user_id not in users:
            conn.disconnect()
            return jsonify({"status": "error", "message": f"User ID {user_id} not found"}), 404
            
        attendance = conn.get_attendance()
        daily_records = {}
        
        # Filter records by user_id and date range
        for record in sorted(
            [r for r in attendance 
             if str(r.user_id) == user_id
             and (not start_datetime or start_datetime <= r.timestamp)
             and (r.timestamp <= end_datetime)],
            key=lambda x: x.timestamp
        ):
            attendancedate = record.timestamp.strftime('%Y-%m-%d')
            
            if attendancedate not in daily_records:
                daily_records[attendancedate] = []
            
            daily_records[attendancedate].append({
                "timestamp": record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "punch_type": "Check Out" if record.punch == 1 else "Check In",
                "punchtime": record.punch
            })
        
        # Format the final output
        attendance_data = []
        for attendancedate in sorted(daily_records.keys(), reverse=True):
            attendance_data.append({
                "attendancedate": attendancedate,
                "attendance_records": sorted(daily_records[attendancedate], key=lambda x: x["timestamp"]),
                "total_records": len(daily_records[attendancedate])
            })
        
        conn.disconnect()
        
        return jsonify({
            "status": "success",
            "user_info": {
                "user_id": user_id,
                "user_name": users[user_id]
            },
            "data": attendance_data,
            "total_days": len(attendance_data),
            "search_params": {
                "start_date": start_date or "All past records",
                "end_date": end_date or end_datetime.strftime('%Y-%m-%d')
            }
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
