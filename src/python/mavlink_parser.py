#!/usr/bin/env python3
"""
MAVLink Parser for Herelink UDP Data
This script properly parses MAVLink messages from Herelink and converts them to readable format
"""

import socket
import json
import time
import threading
import sys
from datetime import datetime

try:
    from pymavlink import mavutil
    MAVLINK_AVAILABLE = True
except ImportError:
    print("PyMAVLink not available. Install with: pip install pymavlink")
    MAVLINK_AVAILABLE = False

class MAVLinkParser:
    def __init__(self, listen_port=14550, forward_port=14551):
        self.listen_port = listen_port
        self.forward_port = forward_port
        self.listen_socket = None
        self.forward_socket = None
        self.is_running = False
        self.message_count = 0
        self.mav_connection = None
        
        # Drone status data
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
            'system_status': 'UNKNOWN',
            'last_heartbeat': 0
        }
        
    def setup_sockets(self):
        """Setup UDP sockets for listening and forwarding"""
        try:
            # Setup listening socket
            self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.listen_socket.bind(('0.0.0.0', self.listen_port))
            self.listen_socket.settimeout(1.0)
            
            # Setup forwarding socket
            self.forward_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            print(f"MAVLink Parser setup complete:")
            print(f"  Listening on: 0.0.0.0:{self.listen_port}")
            print(f"  Forwarding to: localhost:{self.forward_port}")
            
            return True
            
        except Exception as e:
            print(f"Error setting up sockets: {e}")
            return False
    
    def parse_mavlink_message(self, data, addr):
        """Parse MAVLink message and update drone status"""
        if not MAVLINK_AVAILABLE:
            return self.create_basic_telemetry(data, addr)
        
        try:
            # Create MAVLink connection if not exists
            if not self.mav_connection:
                # Create a virtual connection for parsing
                self.mav_connection = mavutil.mavlink_connection('udp:localhost:0', source_system=255)
            
            # Parse the message
            msg = self.mav_connection.mav.parse_char(data)
            
            if msg:
                return self.process_mavlink_message(msg, addr)
            else:
                return self.create_basic_telemetry(data, addr)
                
        except Exception as e:
            print(f"Error parsing MAVLink: {e}")
            return self.create_basic_telemetry(data, addr)
    
    def process_mavlink_message(self, msg, addr):
        """Process parsed MAVLink message and extract telemetry"""
        timestamp = datetime.now().isoformat()
        
        # Update drone status based on message type
        if msg.get_type() == 'HEARTBEAT':
            self.drone_status['connected'] = True
            self.drone_status['armed'] = (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
            self.drone_status['mode'] = mavutil.mode_string_v10(msg)
            self.drone_status['system_status'] = mavutil.mavlink.enums['MAV_STATE'][msg.system_status].name
            self.drone_status['last_heartbeat'] = time.time()
            
        elif msg.get_type() == 'GLOBAL_POSITION_INT':
            self.drone_status['latitude'] = msg.lat / 1e7
            self.drone_status['longitude'] = msg.lon / 1e7
            self.drone_status['altitude'] = msg.alt / 1000.0  # Convert mm to m
            self.drone_status['heading'] = msg.hdg / 100.0
            
        elif msg.get_type() == 'VFR_HUD':
            self.drone_status['groundspeed'] = msg.groundspeed
            self.drone_status['altitude'] = msg.alt
            
        elif msg.get_type() == 'SYS_STATUS':
            self.drone_status['battery'] = msg.battery_remaining
            
        # Create telemetry object
        telemetry = {
            'message_type': 'mavlink_parsed',
            'mavlink_type': msg.get_type(),
            'timestamp': timestamp,
            'source_ip': addr[0],
            'source_port': addr[1],
            'message_id': self.message_count,
            'drone_status': self.drone_status.copy()
        }
        
        return telemetry
    
    def create_basic_telemetry(self, data, addr):
        """Create basic telemetry when MAVLink parsing is not available"""
        timestamp = datetime.now().isoformat()
        
        # Basic telemetry without MAVLink parsing
        telemetry = {
            'message_type': 'mavlink_raw',
            'timestamp': timestamp,
            'source_ip': addr[0],
            'source_port': addr[1],
            'message_id': self.message_count,
            'data_length': len(data),
            'raw_data_preview': data[:20].hex() if len(data) >= 20 else data.hex(),
            'drone_status': {
                'connected': True,  # We're receiving data
                'armed': False,
                'mode': 'UNKNOWN',
                'altitude': 0,
                'latitude': 0,
                'longitude': 0,
                'battery': 0,
                'groundspeed': 0,
                'heading': 0,
                'system_status': 'RECEIVING_DATA',
                'last_heartbeat': time.time()
            }
        }
        
        return telemetry
    
    def forward_message(self, telemetry_data):
        """Forward processed telemetry to Electron app"""
        if self.forward_socket:
            try:
                json_message = json.dumps(telemetry_data, indent=2)
                self.forward_socket.sendto(
                    json_message.encode('utf-8'), 
                    ('localhost', self.forward_port)
                )
                
            except Exception as e:
                print(f"Error forwarding message: {e}")
    
    def listen_for_messages(self):
        """Main listening loop"""
        print(f"Starting MAVLink parser on port {self.listen_port}...")
        print("Press Ctrl+C to stop")
        
        last_status_print = 0
        
        while self.is_running:
            try:
                # Receive data
                data, addr = self.listen_socket.recvfrom(1024)
                self.message_count += 1
                
                # Parse the MAVLink message
                telemetry = self.parse_mavlink_message(data, addr)
                
                if telemetry:
                    # Forward to Electron app
                    self.forward_message(telemetry)
                    
                    # Print status occasionally
                    current_time = time.time()
                    if current_time - last_status_print > 5:  # Every 5 seconds
                        print(f"Messages received: {self.message_count} | "
                              f"Status: {telemetry['drone_status']['system_status']} | "
                              f"Mode: {telemetry['drone_status']['mode']}")
                        last_status_print = current_time
                    
            except socket.timeout:
                # Check for connection timeout
                if time.time() - self.drone_status.get('last_heartbeat', 0) > 10:
                    self.drone_status['connected'] = False
                continue
            except Exception as e:
                if self.is_running:
                    print(f"Error receiving message: {e}")
                    time.sleep(1)
    
    def start(self):
        """Start the MAVLink parser"""
        if not self.setup_sockets():
            return False
        
        self.is_running = True
        
        try:
            self.listen_for_messages()
        except KeyboardInterrupt:
            print("\nStopping MAVLink parser...")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the parser and cleanup"""
        self.is_running = False
        
        if self.listen_socket:
            self.listen_socket.close()
            print("Listen socket closed")
        
        if self.forward_socket:
            self.forward_socket.close()
            print("Forward socket closed")
        
        print(f"Total messages processed: {self.message_count}")

def main():
    """Main function"""
    print("=== MAVLink Parser for Herelink ===")
    
    # Default ports
    listen_port = 14550  # Listen for Herelink data
    forward_port = 14551  # Forward to Electron app
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        try:
            listen_port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid listen port: {sys.argv[1]}")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        try:
            forward_port = int(sys.argv[2])
        except ValueError:
            print(f"Invalid forward port: {sys.argv[2]}")
            sys.exit(1)
    
    # Create and start parser
    parser = MAVLinkParser(listen_port, forward_port)
    
    try:
        parser.start()
    except Exception as e:
        print(f"Error starting parser: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()