from flask import Flask, jsonify, request
from flask_cors import CORS
from zk import ZK, const
from datetime import datetime
from collections import defaultdict

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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
