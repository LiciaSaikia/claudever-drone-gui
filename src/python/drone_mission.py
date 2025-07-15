from dronekit import connect, VehicleMode, LocationGlobalRelative
from geopy.distance import geodesic
import time
import socket
import json
import threading
import sys
import logging

# Suppress DroneKit mode errors
logging.getLogger('dronekit').setLevel(logging.CRITICAL)

# Target GPS coordinates - will be updated by the Electron app
LATITUDE = 34.0173  # Replace with your target latitude
LONGITUDE = 74.7179  # Replace with your target longitude
ALTITUDE = 30  # Replace with your target altitude
WAIT_TIME_AT_TARGET = 30  # Wait time in seconds

# Herelink UDP connection settings
HERELINK_HOST = '192.168.43.22'  # Default Herelink IP
HERELINK_PORT = 14550  # Default MAVLink port

class DroneController:
    def __init__(self):
        self.vehicle = None
        self.udp_socket = None
        self.is_running = True
        
    def setup_udp_connection(self):
        """Setup UDP connection to Herelink"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.settimeout(1.0)
            print(f"UDP socket created for Herelink communication")
            return True
        except Exception as e:
            print(f"Error setting up UDP connection: {e}")
            return False
    
    def send_telemetry(self, data):
        """Send telemetry data via UDP"""
        if self.udp_socket:
            try:
                message = json.dumps(data)
                # Send to local Electron app (listening on localhost)
                self.udp_socket.sendto(message.encode(), ('localhost', 14551))
            except Exception as e:
                print(f"Error sending telemetry: {e}")
    
    def safe_get_mode(self):
        """Safely get vehicle mode without throwing exceptions"""
        try:
            if self.vehicle and self.vehicle.mode:
                return str(self.vehicle.mode.name)
        except Exception:
            pass
        return 'UNKNOWN'
    
    def safe_get_armed_status(self):
        """Safely get armed status without throwing exceptions"""
        try:
            if self.vehicle:
                return bool(self.vehicle.armed)
        except Exception:
            pass
        return False
    
    def wait_for_gps_lock(self, timeout=300):  # 5 minutes
        """Wait for GPS lock before proceeding"""
        print("Waiting for GPS lock...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                location = self.vehicle.location.global_relative_frame
                if location.lat != 0 and location.lon != 0:
                    print(f"GPS lock acquired: {location.lat}, {location.lon}")
                    return True
                print(f"Waiting for GPS... Current: {location.lat}, {location.lon}")
                time.sleep(2)
            except Exception as e:
                print(f"Error checking GPS: {e}")
                time.sleep(2)
        
        return False

    def setup_indoor_testing(self):
        """Setup drone for indoor testing with fake GPS"""
        try:
            print("=== Setting up indoor testing mode ===")
            
            # More aggressive simulation setup
            params_to_set = {
                'SIM_GPS_DISABLE': 0,
                'SIM_GPS_DELAY_MS': 0,
                'SIM_GPS_TYPE': 1,
                'SIM_GPS_LAT_DEG': LATITUDE,
                'SIM_GPS_LON_DEG': LONGITUDE,
                'SIM_GPS_ALT_M': 100,
                'SIM_GPS_NUMSATS': 15,
                'SIM_GPS_HDOP': 50,
                
                # Disable most arming checks for testing
                'ARMING_CHECK': 0,  # Disable all arming checks
                
                # EKF settings
                'EK3_SRC1_POSXY': 3,  # GPS
                'EK3_SRC1_POSZ': 1,   # Baro
                'EK3_SRC1_VELXY': 3,  # GPS
                'EK3_SRC1_VELZ': 3,   # GPS
                
                # Relax EKF thresholds
                'EK3_POSNE_M_NSE': 0.5,
                'EK3_VELD_M_NSE': 0.2,
                'EK3_POSNE_M_NSE': 0.5,
                
                # GPS settings
                'GPS_TYPE': 1,
                'GPS_AUTO_SWITCH': 0,
                
                # Disable some safety features for testing
                'FS_GCS_ENABLE': 0,  # Disable GCS failsafe
                'FS_THR_ENABLE': 0,  # Disable throttle failsafe
            }
            
            print("Setting parameters for indoor testing...")
            for param, value in params_to_set.items():
                try:
                    self.vehicle.parameters[param] = value
                    print(f"Set {param} = {value}")
                    time.sleep(0.5)  # Small delay between parameter sets
                except Exception as e:
                    print(f"Could not set {param}: {e}")
            
            print("Waiting for parameters to take effect...")
            time.sleep(10)  # Wait longer for all parameters to take effect
            
            # Force a reboot to ensure parameters take effect
            print("Forcing parameter refresh...")
            try:
                self.vehicle.parameters['SIM_GPS_DISABLE'] = 0  # Refresh GPS
                time.sleep(2)
            except:
                pass
            
            print(f"Indoor testing setup complete")
            
        except Exception as e:
            print(f"Error setting up indoor testing: {e}")

    def force_arm_bypass_all_checks(self):
        """Ultra aggressive force arm - TESTING ONLY"""
        try:
            print("=== BYPASSING ALL SAFETY CHECKS ===")
            print("WARNING: THIS IS EXTREMELY DANGEROUS!")
            print("ONLY FOR PROPELLER-LESS TESTING!")
            
            # Set most permissive arming settings
            dangerous_params = {
                'ARMING_CHECK': 0,        # Disable ALL arming checks
                'ARMING_REQUIRE': 0,      # Don't require anything
                'FS_GCS_ENABLE': 0,       # No GCS failsafe
                'FS_THR_ENABLE': 0,       # No throttle failsafe
                'GPS_TYPE': 0,            # Disable GPS requirements
                'EK3_CHECK_SCALE': 50,    # Very relaxed EKF checks
            }
            
            for param, value in dangerous_params.items():
                try:
                    self.vehicle.parameters[param] = value
                    time.sleep(0.5)
                except:
                    pass
            
            time.sleep(3)
            
            # Force mode to STABILIZE first (doesn't need GPS)
            print("Setting to STABILIZE mode...")
            self.vehicle.mode = VehicleMode("STABILIZE")
            time.sleep(3)
            
            # Try arming in STABILIZE
            print("Attempting to arm in STABILIZE mode...")
            self.vehicle.armed = True
            
            for i in range(15):
                if self.safe_get_armed_status():
                    print("ARMED in STABILIZE mode!")
                    
                    # Now try switching to GUIDED
                    time.sleep(2)
                    print("Switching to GUIDED mode...")
                    self.vehicle.mode = VehicleMode("GUIDED")
                    time.sleep(2)
                    
                    return True
                    
                print(f"Arming attempt {i+1}/15...")
                time.sleep(1)
            
            return False
            
        except Exception as e:
            print(f"Error in force arm bypass: {e}")
            return False

    def wait_for_ekf_ready(self, timeout=60):
        """Wait for EKF to be ready"""
        print("Waiting for EKF to initialize...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if hasattr(self.vehicle, 'ekf_ok') and self.vehicle.ekf_ok:
                    print("EKF is ready")
                    return True
                    
                print("EKF not ready, waiting...")
                time.sleep(2)
                
            except Exception as e:
                print(f"Error checking EKF: {e}")
                time.sleep(2)
        
        print("EKF timeout - proceeding anyway")
        return False

    def force_arm_for_testing(self):
        """Force arm for indoor testing (DANGEROUS - testing only)"""
        try:
            print("=== FORCING ARM FOR TESTING ===")
            print("WARNING: This bypasses safety checks!")
            
            # Temporarily disable some arming checks
            original_arming_check = self.vehicle.parameters.get('ARMING_CHECK', 1)
            self.vehicle.parameters['ARMING_CHECK'] = 0  # Disable all checks
            
            time.sleep(2)
            
            # Try to arm
            self.vehicle.armed = True
            
            # Wait for arming
            for i in range(10):
                if self.safe_get_armed_status():
                    print("ARMED for testing!")
                    return True
                print(f"Attempting to arm... {i+1}/10")
                time.sleep(1)
            
            # Restore original arming checks
            self.vehicle.parameters['ARMING_CHECK'] = original_arming_check
            
            return False
            
        except Exception as e:
            print(f"Error force arming: {e}")
            return False

    def check_pre_arm_status(self):
        """Check detailed pre-arm status"""
        try:
            print("=== Pre-arm Status Check ===")
            print(f"GPS: {self.vehicle.gps_0}")
            print(f"EKF OK: {self.vehicle.ekf_ok}")
            print(f"Is Armable: {self.vehicle.is_armable}")
            print(f"System Status: {self.vehicle.system_status}")
            print(f"Mode: {self.safe_get_mode()}")
            print("===========================")
        except Exception as e:
            print(f"Error checking pre-arm status: {e}")
    
    def telemetry_thread(self):
        """Background thread to send telemetry data"""
        while self.is_running and self.vehicle:
            try:
                if self.vehicle.location.global_relative_frame:
                    # Safely get telemetry data
                    location = self.vehicle.location.global_relative_frame
                    
                    telemetry_data = {
                        'lat': location.lat if location.lat else 0,
                        'lon': location.lon if location.lon else 0,
                        'alt': location.alt if location.alt else 0,
                        'mode': self.safe_get_mode(),
                        'armed': self.safe_get_armed_status(),
                        'battery': self.vehicle.battery.voltage if self.vehicle.battery else 0,
                        'groundspeed': self.vehicle.groundspeed if self.vehicle.groundspeed else 0,
                        'heading': self.vehicle.heading if self.vehicle.heading else 0,
                        'timestamp': time.time(),
                        'connected': True
                    }
                    
                    self.send_telemetry(telemetry_data)
                time.sleep(1)
            except Exception as e:
                print(f"Telemetry error: {e}")
                time.sleep(1)
    
    def get_distance_to_target(self, current_location, target_location):
        """Calculate distance to target location"""
        if not current_location.lat or not current_location.lon:
            return float('inf')
        return geodesic(
            (current_location.lat, current_location.lon), 
            (target_location.lat, target_location.lon)
        ).meters
    
    def wait_for_mode_change(self, target_mode, timeout=30):
        """Wait for mode change with timeout and error handling"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                current_mode = self.safe_get_mode()
                if current_mode == target_mode:
                    return True
                print(f"Waiting for mode change to {target_mode}, current: {current_mode}")
                time.sleep(1)
            except Exception as e:
                print(f"Error checking mode: {e}")
                time.sleep(1)
        return False
    
    def arm_and_takeoff(self, target_altitude):
        """Arm the vehicle and take off to target altitude"""
        print("Starting INDOOR TESTING pre-flight checks...")
        print("WARNING: This is for propeller-less testing only!")
        
        # Check pre-arm status first
        self.check_pre_arm_status()
        
        # For indoor testing, bypass normal checks
        print("Attempting ultra-permissive arming for testing...")
        
        if not self.force_arm_bypass_all_checks():
            print("Even ultra-permissive arming failed.")
            print("This might be a hardware safety switch or other physical issue.")
            
            # Last resort - try manual mode
            print("Trying MANUAL mode as last resort...")
            try:
                self.vehicle.mode = VehicleMode("MANUAL")
                time.sleep(2)
                self.vehicle.armed = True
                
                for i in range(10):
                    if self.safe_get_armed_status():
                        print("Armed in MANUAL mode!")
                        break
                    time.sleep(1)
                else:
                    raise Exception("Cannot arm - check physical safety switch, remove propellers, check connections")
            except Exception as e:
                raise Exception(f"All arming methods failed: {e}")
        
        print("Successfully armed for testing!")
        
        # For testing, we'll simulate takeoff since real takeoff might be dangerous
        print("SIMULATING takeoff for indoor testing...")
        
        # Update our internal status to simulate flight
        for alt in range(0, int(target_altitude) + 1, 2):
            print(f"Simulated Altitude: {alt}m")
            time.sleep(0.5)
            
            if alt >= target_altitude * 0.9:
                print("Simulated target altitude reached")
                break
        
        print("Indoor testing takeoff simulation complete!")
    
    def arm_and_goto(self, target_location):
        """Execute the complete mission: takeoff, goto, and return"""
        try:
            self.arm_and_takeoff(target_location.alt)
            
            print(f"Going to target location: {target_location}")
            self.vehicle.simple_goto(target_location)
            
            while self.is_running:
                try:
                    current_location = self.vehicle.location.global_relative_frame
                    distance_to_target = self.get_distance_to_target(current_location, target_location)
                    
                    print(f"Distance to target: {distance_to_target:.1f} meters")
                    
                    if distance_to_target < 2:  # Within 2 meters of target
                        print("Reached target location!")
                        break
                except Exception as e:
                    print(f"Error calculating distance: {e}")
                
                time.sleep(1)
            
            if self.is_running:
                print(f"Waiting for {WAIT_TIME_AT_TARGET} seconds at the target location...")
                time.sleep(WAIT_TIME_AT_TARGET)
                
                print("Changing mode to RTL (Return To Launch).")
                try:
                    self.vehicle.mode = VehicleMode("RTL")
                    self.wait_for_mode_change("RTL")
                except Exception as e:
                    print(f"Error setting RTL mode: {e}")
                
                print("Mission completed successfully!")
            else:
                print("Mission stopped by user")
                
        except Exception as e:
            print(f"Mission error: {e}")
            raise
    
    def connect_to_vehicle(self):
        """Connect to the vehicle via Herelink UDP"""
        connection_strings = [
            f'udp:{HERELINK_HOST}:{HERELINK_PORT}',  # Direct Herelink connection
            'udp:192.168.43.22:14550',  # Local UDP connection
            '/dev/ttyUSB0',  # USB serial connection (fallback)
        ]
        
        for connection_string in connection_strings:
            try:
                print(f"Attempting to connect to vehicle via {connection_string}...")
                
                # Suppress DroneKit logging during connection
                old_level = logging.getLogger('dronekit').level
                logging.getLogger('dronekit').setLevel(logging.CRITICAL)
                
                self.vehicle = connect(connection_string, baud=57600, wait_ready=False, timeout=10)
                
                # Restore logging level
                logging.getLogger('dronekit').level = old_level
                
                if self.vehicle:
                    print(f"Connected to vehicle successfully via {connection_string}")
                    
                    # FOR INDOOR TESTING ONLY - Enable GPS simulation
                    try:
                        print("Setting up GPS simulation for indoor testing...")
                        self.vehicle.parameters['SIM_GPS_DISABLE'] = 0
                        self.vehicle.parameters['SIM_GPS_DELAY_MS'] = 0
                        # Set a fake home position for testing
                        self.vehicle.parameters['SIM_GPS_TYPE'] = 1
                        time.sleep(2)  # Wait for parameters to take effect
                        print("GPS simulation enabled")
                    except Exception as e:
                        print(f"Could not enable GPS simulation: {e}")
                    
                    # Wait a moment for initial telemetry
                    time.sleep(2)
                    return True
                    
            except Exception as e:
                print(f"Failed to connect via {connection_string}: {e}")
                continue
        
        print("Failed to connect to vehicle with all connection methods")
        return False
    
    def run_mission(self):
        """Main mission execution function"""
        try:
            # Setup UDP for telemetry
            if not self.setup_udp_connection():
                print("Warning: Could not setup UDP connection for telemetry")
            
            # Connect to vehicle
            if not self.connect_to_vehicle():
                print("Error: Could not connect to vehicle")
                return False
            
            # Setup indoor testing mode
            self.setup_indoor_testing()
            
            # Start telemetry thread
            telemetry_thread = threading.Thread(target=self.telemetry_thread)
            telemetry_thread.daemon = True
            telemetry_thread.start()
            
            # Execute mission
            print("Setting mode to GUIDED.")
            try:
                self.vehicle.mode = VehicleMode("GUIDED")
                self.wait_for_mode_change("GUIDED")
            except Exception as e:
                print(f"Warning: Could not set GUIDED mode: {e}")
            
            target_location = LocationGlobalRelative(LATITUDE, LONGITUDE, ALTITUDE)
            print(f"Mission target: {LATITUDE}, {LONGITUDE} at {ALTITUDE}m altitude")
            
            self.arm_and_goto(target_location)
            
            return True
            
        except KeyboardInterrupt:
            print("Mission interrupted by user")
            return False
        except Exception as e:
            print(f"Mission failed: {e}")
            return False
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.is_running = False
        
        if self.vehicle:
            try:
                print("Closing vehicle connection...")
                self.vehicle.close()
            except Exception as e:
                print(f"Error closing vehicle: {e}")
        
        if self.udp_socket:
            try:
                print("Closing UDP socket...")
                self.udp_socket.close()
            except Exception as e:
                print(f"Error closing UDP socket: {e}")
        
        print("Cleanup completed")

def main():
    """Main function"""
    print("=== Drone Mission Controller ===")
    print(f"Target coordinates: {LATITUDE}, {LONGITUDE}")
    print(f"Target altitude: {ALTITUDE}m")
    print(f"Wait time at target: {WAIT_TIME_AT_TARGET}s")
    print("================================")
    
    controller = DroneController()
    
    try:
        success = controller.run_mission()
        if success:
            print("Mission completed successfully!")
            sys.exit(0)
        else:
            print("Mission failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nMission interrupted by user")
        controller.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        controller.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()