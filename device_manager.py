"""
Device Manager for ZK Attendance System
Handles multiple device connections and operations
"""
import logging
import json
import os
import sys
import tempfile
from zk import ZK
from flask import session, request, has_request_context
from datetime import datetime

# Get application data directory
def get_app_data_directory():
    """Get the appropriate directory for application data files
    This works both for development and when packaged as an executable
    """
    # For development, prioritize using the script directory first
    if not getattr(sys, 'frozen', False):
        # When running as a script
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            logger.info(f"Using script directory for app data: {script_dir}")
            return script_dir
        except Exception as e:
            logger.warning(f"Could not use script directory for app data: {str(e)}")
    
    try:
        # Next, try to use a fixed location in the user's home directory
        # This is the most reliable approach for executables
        user_home = os.path.expanduser('~')
        app_data_dir = os.path.join(user_home, 'ZK_Attendance_System')
        
        # Ensure the directory exists
        if not os.path.exists(app_data_dir):
            os.makedirs(app_data_dir)
            
        # Test if the directory is writable by creating a test file
        test_file = os.path.join(app_data_dir, 'write_test.tmp')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)  # Clean up the test file
            logger.info(f"Using home directory for app data: {app_data_dir}")
            return app_data_dir
        except Exception:
            # If we can't write to the home directory, fall back to other options
            pass
    except Exception as e:
        logger.warning(f"Could not use home directory for app data: {str(e)}")
    
    # If previous approaches fail, try the executable directory (for bundled exe)
    if getattr(sys, 'frozen', False):
        # When running as a bundled exe
        try:
            exe_dir = os.path.dirname(sys.executable)
            # Test if the directory is writable
            test_file = os.path.join(exe_dir, 'write_test.tmp')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)  # Clean up the test file
            logger.info(f"Using executable directory for app data: {exe_dir}")
            return exe_dir
        except Exception as e:
            logger.warning(f"Could not use executable directory for app data: {str(e)}")
    
    # Last resort: use a temp directory
    temp_dir = os.path.join(tempfile.gettempdir(), 'zk_attendance_system')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    logger.warning(f"Using temporary directory for app data: {temp_dir}")
    return temp_dir

# Configure logging
logger = logging.getLogger('device_manager')

# Set device_manager logger to WARNING level for console output
# This will reduce console messages while still logging to file
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
        logger.setLevel(logging.WARNING)

# Define the exact path to config.json and devices.json
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
DEVICES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'devices.json')

# Default device settings
DEFAULT_IP = '192.168.1.201'
DEFAULT_PORT = 4370
DEFAULT_TIMEOUT = 5

class DeviceManager:
    """Manages multiple ZK device connections and operations"""
    
    def __init__(self):
        self.devices = {}
        self.active_device = None
        self.load_devices()
    
    def load_devices(self):
        """Load saved devices from main config file"""
        # Use the global CONFIG_PATH
        config_file = CONFIG_PATH
        logger.info(f"Loading devices from config file: {config_file}")
        
        if os.path.exists(config_file) and os.path.getsize(config_file) > 0:
            try:
                with open(config_file, 'r') as f:
                    file_content = f.read().strip()
                    if not file_content:  # Check if file is empty after stripping whitespace
                        logger.warning(f"Config file exists but is empty: {config_file}")
                        self._load_from_legacy_file()
                        return
                        
                    # Reset file pointer to beginning
                    f.seek(0)
                    config = json.load(f)
                    # Load registered devices
                    if 'registered_devices' in config and isinstance(config['registered_devices'], dict):
                        self.devices = config['registered_devices']
                        logger.info(f"Loaded {len(self.devices)} devices from main config")
                        
                        # Log the loaded devices for debugging
                        for device_id, device in self.devices.items():
                            logger.info(f"Loaded device: ID={device_id}, Name={device.get('name')}, IP={device.get('ip')}")
                        
                        # Load active device if it exists
                        if 'active_device' in config and config['active_device'] in self.devices:
                            self.active_device = config['active_device']
                            logger.info(f"Loaded active device {self.active_device} from config")
                    else:
                        logger.warning("No registered_devices found in config.json or invalid format")
                        # Try to load from old devices.json for backward compatibility
                        self._load_from_legacy_file()
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error loading devices from config: {str(e)}")
                # Try to create a valid config file
                try:
                    # Create a backup of the corrupted file
                    backup_file = f"{config_file}.bak"
                    if os.path.exists(config_file):
                        with open(config_file, 'r') as src, open(backup_file, 'w') as dst:
                            dst.write(src.read())
                        logger.info(f"Created backup of corrupted config file: {backup_file}")
                    
                    # Create a new valid config file
                    with open(config_file, 'w') as f:
                        json.dump({'registered_devices': {}}, f, indent=4)
                    logger.info(f"Created new empty config file after JSON decode error")
                except Exception as e2:
                    logger.error(f"Failed to create new config file: {str(e2)}")
                
                # Try to load from old devices.json for backward compatibility
                self._load_from_legacy_file()
            except Exception as e:
                logger.error(f"Error loading devices from config: {str(e)}")
                # Try to load from old devices.json for backward compatibility
                self._load_from_legacy_file()
        else:
            logger.warning(f"Config file not found at {config_file}, trying legacy devices.json")
            # Try to load from old devices.json for backward compatibility
            self._load_from_legacy_file()
            
    def _load_from_legacy_file(self):
        """Load devices from legacy devices.json file for backward compatibility"""
        # Use the global DEVICES_PATH
        devices_file = DEVICES_PATH
        logger.info(f"Trying to load devices from legacy file: {devices_file}")
        
        if os.path.exists(devices_file):
            try:
                with open(devices_file, 'r') as f:
                    self.devices = json.load(f)
                logger.info(f"Loaded {len(self.devices)} devices from legacy devices.json")
            except Exception as e:
                logger.error(f"Error loading devices from legacy file: {str(e)}")
                self.devices = {}
    
    def save_devices(self):
        """Save devices to main config file"""
        # Use the global CONFIG_PATH
        config_file = CONFIG_PATH
        logger.info(f"Saving devices to config file: {config_file}")
        
        try:
            # Load current config
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
                
            # Update registered_devices in config
            config['registered_devices'] = self.devices
            
            # Save active device to config
            if self.active_device:
                config['active_device'] = self.active_device
                logger.info(f"Saving active device {self.active_device} to config")
            
            # Ensure the file is properly closed and flushed to disk
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
                
            logger.info(f"Saved {len(self.devices)} devices to main config at {config_file}")
            
            # Also save to legacy file for backward compatibility
            self._save_to_legacy_file()
            
            # Verify the save was successful by reading back the file
            try:
                # Make sure the file exists and has content before trying to load it
                if os.path.exists(config_file) and os.path.getsize(config_file) > 0:
                    with open(config_file, 'r') as f:
                        saved_config = json.load(f)
                        if 'registered_devices' in saved_config and saved_config['registered_devices'] == self.devices:
                            logger.info("Device save verification successful")
                        else:
                            logger.warning("Device save verification failed - data mismatch")
                else:
                    logger.warning(f"Device save verification failed: File is empty or does not exist")
            except Exception as e:
                logger.warning(f"Device save verification failed: {str(e)}")
                # If verification fails, try to recreate the file with the current data
                try:
                    with open(config_file, 'w') as f:
                        json.dump({'registered_devices': self.devices}, f, indent=4)
                        f.flush()
                        os.fsync(f.fileno())
                    logger.info("Recreated config file after verification failure")
                except Exception as e2:
                    logger.error(f"Failed to recreate config file: {str(e2)}")
        
        except Exception as e:
            logger.error(f"Error saving devices to main config: {str(e)}")
            # Try saving to legacy file as fallback
            self._save_to_legacy_file()
    
    def _save_to_legacy_file(self):
        """Save devices to legacy devices.json file for backward compatibility"""
        # Use the global DEVICES_PATH
        devices_file = DEVICES_PATH
        logger.info(f"Saving devices to legacy file: {devices_file}")
        
        try:
            with open(devices_file, 'w') as f:
                json.dump(self.devices, f, indent=4)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            logger.info(f"Saved {len(self.devices)} devices to legacy devices.json at {devices_file}")
        except Exception as e:
            logger.error(f"Error saving devices to legacy file: {str(e)}")
    
    def add_device(self, device_id, name, ip, port=DEFAULT_PORT, timeout=DEFAULT_TIMEOUT):
        """Add a new device to the manager"""
        if device_id in self.devices:
            logger.warning(f"Device ID {device_id} already exists, updating")
        
        self.devices[device_id] = {
            'name': name,
            'ip': ip,
            'port': int(port),
            'timeout': int(timeout),
            'last_connected': None
        }
        self.save_devices()
        return device_id
    
    def remove_device(self, device_id):
        """Remove a device from the manager"""
        if device_id in self.devices:
            del self.devices[device_id]
            self.save_devices()
            logger.info(f"Removed device {device_id}")
            return True
        return False
    
    def get_device(self, device_id):
        """Get device details by ID"""
        return self.devices.get(device_id)
    
    def get_all_devices(self):
        """Get all registered devices"""
        return self.devices
    
    def set_active_device(self, device_id):
        """Set the active device for the current session and save to config"""
        if device_id in self.devices:
            self.active_device = device_id
            if has_request_context():
                session['active_device'] = device_id
            logger.info(f"Set active device to {device_id}")
            
            # Save the active device to config immediately
            try:
                self.save_devices()
                logger.info(f"Saved active device {device_id} to config")
            except Exception as e:
                logger.error(f"Error saving active device to config: {str(e)}")
                
            return True
        return False
    
    def get_active_device_id(self):
        """Get the active device ID from session, config, or default"""
        # First check request context (for current web session)
        if has_request_context():
            # Check headers first, then session
            device_id = request.headers.get('X-Device-ID') or session.get('active_device')
            if device_id and device_id in self.devices:
                # If found in session, make sure it's also saved to config
                if self.active_device != device_id:
                    self.set_active_device(device_id)
                return device_id
        
        # If not in session, use the active device from config
        if self.active_device and self.active_device in self.devices:
            logger.info(f"Using active device {self.active_device} from config")
            # Update session if in request context
            if has_request_context():
                session['active_device'] = self.active_device
            return self.active_device
        
        # If no devices, return None
        if not self.devices:
            return None
            
        # Otherwise, use the first device and set it as active
        first_device = next(iter(self.devices))
        self.set_active_device(first_device)
        return first_device
    
    def connect_to_device(self, device_id=None):
        """Connect to a specific device or the active device"""
        # If no device_id specified, use active device
        if not device_id:
            device_id = self.get_active_device_id()
            if not device_id:
                raise ValueError("No active device set and no device ID provided")
        
        # Get device details
        device = self.devices.get(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        # Connect to device
        ip = device['ip']
        port = device['port']
        timeout = device['timeout']
        
        logger.info(f"Connecting to device {device_id} at {ip}:{port}")
        zk = ZK(ip, port=port, timeout=timeout)
        conn = zk.connect()
        
        if not conn:
            raise ConnectionError(f"Failed to connect to device {device_id} at {ip}:{port}")
        
        # Update last connected timestamp
        self.devices[device_id]['last_connected'] = datetime.now().isoformat()
        self.save_devices()
        
        # Set as active device
        self.set_active_device(device_id)
        
        return conn
    
    def connect_to_all_devices(self):
        """Connect to all registered devices and return connections"""
        connections = {}
        for device_id in self.devices:
            try:
                connections[device_id] = self.connect_to_device(device_id)
            except Exception as e:
                logger.error(f"Error connecting to device {device_id}: {str(e)}")
        
        return connections
    
    def test_connection(self, device_id):
        """Test connection to a device"""
        try:
            conn = self.connect_to_device(device_id)
            conn.disconnect()
            return True
        except Exception as e:
            logger.error(f"Connection test failed for device {device_id}: {str(e)}")
            return False

# Create a global instance of the device manager
device_manager = DeviceManager()
