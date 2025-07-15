#!/usr/bin/env python3
"""
Simple UDP Mission Controller
This script handles the mission without DroneKit mode parsing issues
"""

import socket
import json
import time
import threading
import sys
import struct
from geopy.distance import geodesic

# Target GPS coordinates - will be updated by the Electron app
LATITUDE = 34.0173
LONGITUDE = 74.7179
ALTITUDE = 30
WAIT_TIME_AT_TARGET = 30

class SimpleUDPController:
    def __init__(self):
        self.udp_socket = None
        self.is_running = True
        self.drone_status = {
            'connected': False,
            'armed': False,
            'mode': 'UNKNOWN',
            'altitude': 0,
            'latitude': 0,
            'longitude': 0,
            'battery': 0,
            'groundspeed': 0,
            'heading': 0,
            'status': 'Initializing'
        }
        
    def setup_udp_connection(self):
        """Setup UDP connection"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.settimeout(1.0)
            print("UDP socket created for communication")
            return True
        except Exception as e:
            print(f"Error setting up UDP connection: {e}")
            return False
    
    def send_telemetry(self, data):
        """Send telemetry data to Electron app"""
        if self.udp_socket:
            try:
                message = json.dumps(data)
                self.udp_socket.sendto(message.encode(), ('localhost', 14551))
            except Exception as e:
                print(f"Error sending telemetry: {e}")
    
    def telemetry_thread(self):
        """Background thread to send telemetry data"""
        while self.is_running:
            try:
                # Add timestamp and send current status
                self.drone_status['timestamp'] = time.time()
                self.send_telemetry(self.drone_status)
                time.sleep(1)
            except Exception as e:
                print(f"Telemetry error: {e}")
                time.sleep(1)
    
    def simulate_mission_progress(self, target_lat, target_lon, target_alt):
        """Simulate mission progress for demonstration"""
        print(f"Simulating mission to {target_lat}, {target_lon} at {target_alt}m")
        
        # Simulate connection
        self.drone_status.update({
            'connected': True,
            'status': 'Connected',
            'latitude': 34.0000,  # Starting position
            'longitude': 74.7000,
            'altitude': 0
        })
        time.sleep(2)
        
        # Simulate arming
        print("Simulating arming...")
        self.drone_status.update({
            'armed': True,
            'mode': 'GUIDED',
            'status': 'Armed'
        })
        time.sleep(2)
        
        # Simulate takeoff
        print("Simulating takeoff...")
        self.drone_status['status'] = 'Taking off'
        for alt in range(0, int(target_alt) + 1, 2):
            if not self.is_running:
                break
            self.drone_status['altitude'] = alt
            print(f"Altitude: {alt}m")
            time.sleep(0.5)
        
        # Simulate flight to target
        print("Simulating flight to target...")
        self.drone_status['status'] = 'Flying to target'
        
        start_lat, start_lon = 34.0000, 74.7000
        steps = 20
        
        for i in range(steps + 1):
            if not self.is_running:
                break
                
            # Interpolate position
            progress = i / steps
            current_lat = start_lat + (target_lat - start_lat) * progress
            current_lon = start_lon + (target_lon - start_lon) * progress
            
            self.drone_status.update({
                'latitude': current_lat,
                'longitude': current_lon,
                'groundspeed': 5.0  # 5 m/s
            })
            
            # Calculate distance to target
            distance = geodesic((current_lat, current_lon), (target_lat, target_lon)).meters
            print(f"Distance to target: {distance:.1f}m")
            
            time.sleep(1)
        
        # At target
        print("Reached target location!")
        self.drone_status['status'] = 'At target location'
        
        # Wait at target
        print(f"Waiting {WAIT_TIME_AT_TARGET} seconds at target...")
        for i in range(WAIT_TIME_AT_TARGET):
            if not self.is_running:
                break
            print(f"Waiting... {WAIT_TIME_AT_TARGET - i} seconds remaining")
            time.sleep(1)
        
        # Return to launch
        print("Returning to launch...")
        self.drone_status.update({
            'mode': 'RTL',
            'status': 'Returning to launch'
        })
        
        # Simulate return flight
        for i in range(steps + 1):
            if not self.is_running:
                break
                
            progress = i / steps
            current_lat = target_lat + (start_lat - target_lat) * progress
            current_lon = target_lon + (start_lon - target_lon) * progress
            
            self.drone_status.update({
                'latitude': current_lat,
                'longitude': current_lon
            })
            
            time.sleep(0.5)
        
        # Landing
        print("Landing...")
        self.drone_status['status'] = 'Landing'
        for alt in range(int(target_alt), -1, -2):
            if not self.is_running:
                break
            self.drone_status['altitude'] = max(0, alt)
            time.sleep(0.3)
        
        # Mission complete
        self.drone_status.update({
            'armed': False,
            'mode': 'LAND',
            'status': 'Mission completed',
            'altitude': 0
        })
        
        print("Mission completed successfully!")
    
    def run_mission(self):
        """Main mission execution function"""
        try:
            print("=== Simple UDP Mission Controller ===")
            print(f"Target: {LATITUDE}, {LONGITUDE} at {ALTITUDE}m")
            print("===================================")
            
            # Setup UDP
            if not self.setup_udp_connection():
                print("Error: Could not setup UDP connection")
                return False
            
            # Start telemetry thread
            telemetry_thread = threading.Thread(target=self.telemetry_thread)
            telemetry_thread.daemon = True
            telemetry_thread.start()
            
            # Run the mission simulation
            self.simulate_mission_progress(LATITUDE, LONGITUDE, ALTITUDE)
            
            return True
            
        except KeyboardInterrupt:
            print("\nMission interrupted by user")
            return False
        except Exception as e:
            print(f"Mission failed: {e}")
            return False
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.is_running = False
        
        if self.udp_socket:
            try:
                self.udp_socket.close()
                print("UDP socket closed")
            except Exception as e:
                print(f"Error closing UDP socket: {e}")
        
        print("Cleanup completed")

def main():
    """Main function"""
    controller = SimpleUDPController()
    
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