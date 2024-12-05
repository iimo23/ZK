from zk import ZK, const
from datetime import datetime
from collections import defaultdict

def organize_attendance(attendance_records):
    """Organize attendance records by user and date"""
    # Sort records by user and timestamp
    user_records = defaultdict(list)
    for record in attendance_records:
        user_records[record.user_id].append(record)
    
    # For each user, pair check-ins with check-outs
    organized_records = {}
    for user_id, records in user_records.items():
        # Sort records by timestamp
        records.sort(key=lambda x: x.timestamp)
        daily_records = defaultdict(list)
        
        # Group by date
        for record in records:
            date = record.timestamp.strftime('%Y-%m-%d')
            daily_records[date].append(record.timestamp)
        
        organized_records[user_id] = daily_records
    
    return organized_records

def connect_to_device(ip='192.168.37.11', port=4370):
    """
    Connect to a ZK device using the specified IP and port
    """
    try:
        # Create a ZK instance
        zk = ZK(ip, port=port, timeout=5, password=0, force_udp=False, ommit_ping=False)
        
        # Connect to device
        conn = zk.connect()
        
        if conn:
            print(f"Connection successful to {ip}")
            
            # Get device info
            print(f"Device firmware version: {conn.get_firmware_version()}")
            print(f"Device serial number: {conn.get_serialnumber()}")
            
            # Get users and create user lookup
            users = conn.get_users()
            user_lookup = {str(user.uid): user.name for user in users}  # Convert uid to string
            
            print("\n=== User Data ===")
            print("UID    Name          Privilege    Password    Card")
            print("-" * 50)
            for user in users:
                privilege = 'Admin' if user.privilege == const.USER_ADMIN else 'User'
                print(f"{user.uid:<6} {user.name:<13} {privilege:<12} {user.password:<11} {user.card}")
            
            # Get and organize attendance records
            attendance = conn.get_attendance()
            organized_records = organize_attendance(attendance)
            
            print("\n=== Attendance Records by User ===")
            print("-" * 70)
            
            for user_id, daily_records in organized_records.items():
                user_name = user_lookup[str(user_id)]  # Convert user_id to string for lookup
                print(f"\nUser: {user_name} (ID: {user_id})")
                print("Date          check-in          check-out")
                print("-" * 50)
                
                for date, punches in daily_records.items():
                    first_punch = min(punches).strftime('%H:%M:%S')
                    last_punch = max(punches).strftime('%H:%M:%S')
                    print(f"{date}  {first_punch}           {last_punch}")
            
            print(f"\nTotal Users: {len(users)}")
            print(f"Total Attendance Records: {len(attendance)}")
            
            # Disconnect
            conn.disconnect()
            return True
            
    except Exception as e:
        print(f"Error connecting to device: {str(e)}")
        return False

if __name__ == "__main__":
    # Try to connect to the device
    connect_to_device()
