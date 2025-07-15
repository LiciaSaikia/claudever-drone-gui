#!/usr/bin/env python3
"""
Setup script for the Drone Controller Application
This script helps set up the development environment
"""

import os
import sys
import subprocess
import platform

def run_command(command, description):
    """Run a command and handle errors"""
    print(f">>> {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                               capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"  Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("✗ Python 3.7 or higher is required")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def check_node_version():
    """Check if Node.js is installed"""
    try:
        result = subprocess.run(['node', '--version'], 
                              capture_output=True, text=True)
        print(f"✓ Node.js {result.stdout.strip()} detected")
        return True
    except FileNotFoundError:
        print("✗ Node.js is not installed")
        return False

def setup_python_environment():
    """Set up Python virtual environment and install dependencies"""
    print("\n=== Setting up Python Environment ===")
    
    # Create virtual environment
    if not os.path.exists('venv'):
        if not run_command('python -m venv venv', 'Creating virtual environment'):
            return False
    
    # Determine activation command based on OS
    if platform.system() == 'Windows':
        activate_cmd = 'venv\\Scripts\\activate'
        pip_cmd = 'venv\\Scripts\\pip'
    else:
        activate_cmd = 'source venv/bin/activate'
        pip_cmd = 'venv/bin/pip'
    
    # Install Python dependencies
    install_cmd = f'{pip_cmd} install -r requirements.txt'
    if not run_command(install_cmd, 'Installing Python dependencies'):
        return False
    
    return True

def setup_node_environment():
    """Set up Node.js environment and install dependencies"""
    print("\n=== Setting up Node.js Environment ===")
    
    # Install Node.js dependencies
    if not run_command('npm install', 'Installing Node.js dependencies'):
        return False
    
    return True

def create_directory_structure():
    """Create necessary directories"""
    print("\n=== Creating Directory Structure ===")
    
    directories = [
        'src/python',
        'src/renderer',
        'src/assets',
        'logs',
        'config'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created directory: {directory}")
        else:
            print(f"✓ Directory exists: {directory}")
    
    return True

def create_launch_scripts():
    """Create launch scripts for different platforms"""
    print("\n=== Creating Launch Scripts ===")
    
    # Windows batch script
    windows_script = """@echo off
echo Starting Drone Controller Application...
call venv\\Scripts\\activate
start "" npm start
echo Application started. Check for the Electron window.
pause
"""
    
    # Unix shell script
    unix_script = """#!/bin/bash
echo "Starting Drone Controller Application..."
source venv/bin/activate
npm start &
echo "Application started. Check for the Electron window."
"""
    
    try:
        with open('start_app.bat', 'w') as f:
            f.write(windows_script)
        print("✓ Created Windows launch script: start_app.bat")
        
        with open('start_app.sh', 'w') as f:
            f.write(unix_script)
        os.chmod('start_app.sh', 0o755)
        print("✓ Created Unix launch script: start_app.sh")
        
        return True
    except Exception as e:
        print(f"✗ Error creating launch scripts: {e}")
        return False

def main():
    """Main setup function"""
    print("=== Drone Controller Application Setup ===")
    print("This script will set up the development environment")
    print("=" * 50)
    
    # Check prerequisites
    if not check_python_version():
        sys.exit(1)
    
    if not check_node_version():
        print("Please install Node.js from https://nodejs.org/")
        sys.exit(1)
    
    # Setup steps
    steps = [
        create_directory_structure,
        setup_python_environment,
        setup_node_environment,
        create_launch_scripts
    ]
    
    for step in steps:
        if not step():
            print(f"\n✗ Setup failed during: {step.__name__}")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✓ Setup completed successfully!")
    print("\nNext steps:")
    print("1. Connect your Herelink device to the same network")
    print("2. Run the application:")
    print("   - Windows: double-click start_app.bat")
    print("   - Unix/Linux/Mac: ./start_app.sh")
    print("3. Configure the UDP connection in the app")
    print("4. Set your target coordinates and start the mission")
    print("\nFor troubleshooting, check the console output in the app.")

if __name__ == "__main__":
    main()