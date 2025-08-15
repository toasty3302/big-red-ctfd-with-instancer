#!/usr/bin/env python3
"""
Setup script for Challenge Instancer with Azure Container Instances and CTFd Integration
"""

import subprocess
import sys
import os

def run_command(command):
    """Run a command and return the result"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(f"Success: {result.stdout}")
    return True

def check_ctfd_database():
    """Check if CTFd database container is running"""
    try:
        result = subprocess.run([
            'docker', 'ps', '--filter', 'name=big-red-ctfd-db-1', '--format', '{{.Names}}'
        ], capture_output=True, text=True, timeout=10)
        
        if 'big-red-ctfd-db-1' in result.stdout:
            print("✅ CTFd database container is running")
            return True
        else:
            print("⚠️  CTFd database container not found")
            print("   Please start the CTFd stack first:")
            print("   cd c:\\Users\\billn\\Downloads\\big-red-ctfd")
            print("   docker-compose up -d")
            return False
    except:
        print("❌ Error checking CTFd database")
        return False

def main():
    print("🚀 Setting up Challenge Instancer with Azure Integration")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("❌ Please run this script from the instancer directory")
        sys.exit(1)
    
    # Install requirements
    print("\n📦 Installing Python requirements...")
    if not run_command(f'"{sys.executable}" -m pip install -r requirements.txt'):
        print("❌ Failed to install requirements")
        sys.exit(1)
    
    # Check Docker and CTFd database
    print("\n🐳 Checking CTFd database...")
    if not check_ctfd_database():
        print("❌ CTFd database not available")
        print("   Please make sure CTFd is running first")
    
    # Check Azure CLI
    print("\n🔍 Checking Azure CLI...")
    if not run_command('az --version'):
        print("❌ Azure CLI not found. Please install Azure CLI first.")
        print("   Run: winget install Microsoft.AzureCLI")
    else:
        # Check Azure login
        print("\n🔐 Checking Azure authentication...")
        if not run_command('az account show'):
            print("❌ Not logged into Azure. Use start_instancer.py for automatic login")
            print("   Or manually run: az login")
        else:
            print("✅ Azure authentication verified")
    
    print("\n" + "=" * 40)
    print("✅ Setup completed!")
    print("\n🚀 To start the application:")
    print("   Option 1 (Recommended): python start_instancer.py")
    print("   Option 2 (Manual): az login && python app.py")
    print("\n🌐 Then visit: http://localhost:5000")
    print("\n� Login with your CTFd credentials:")
    print("   Username: toasty")
    print("   Password: Dcba!2345")
    print("\n☁️  Azure Container Instances will be created for challenges")

if __name__ == '__main__':
    main()
