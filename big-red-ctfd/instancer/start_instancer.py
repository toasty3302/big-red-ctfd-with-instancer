#!/usr/bin/env python3
"""
Launcher script for the Challenge Instancer.
Automatically handles Azure authentication before starting the Flask app.
"""

import subprocess
import sys
import os
import time
import platform

# Determine the correct Azure CLI command based on platform
AZ_CMD = 'az.cmd' if platform.system() == 'Windows' else 'az'
USE_SHELL = platform.system() == 'Windows'

def check_azure_cli():
    """Check if Azure CLI is installed."""
    try:
        result = subprocess.run([AZ_CMD, '--version'], capture_output=True, text=True, timeout=10, shell=USE_SHELL)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def check_azure_auth():
    """Check if user is already logged into Azure."""
    try:
        result = subprocess.run([AZ_CMD, 'account', 'show'], capture_output=True, text=True, timeout=10, shell=USE_SHELL)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False

def azure_login():
    """Login to Azure interactively or via service principal."""
    if os.getenv('DOCKER_MODE'):
        print("🐳 Running in Docker mode...")
        # Check if service principal credentials are provided
        if all([os.getenv('AZURE_CLIENT_ID'), os.getenv('AZURE_CLIENT_SECRET'), os.getenv('AZURE_TENANT_ID')]):
            print("🔐 Using service principal authentication...")
            try:
                result = subprocess.run([
                    AZ_CMD, 'login', '--service-principal',
                    '--username', os.getenv('AZURE_CLIENT_ID'),
                    '--password', os.getenv('AZURE_CLIENT_SECRET'),
                    '--tenant', os.getenv('AZURE_TENANT_ID')
                ], capture_output=True, text=True, timeout=60, shell=USE_SHELL)
                
                if result.returncode == 0:
                    print("✅ Service principal login successful")
                    return True
                else:
                    print(f"❌ Service principal login failed: {result.stderr}")
                    return False
            except subprocess.TimeoutExpired:
                print("❌ Service principal login timed out")
                return False
        else:
            print("⚠️  No service principal credentials provided")
            print("💡 The app will try to use DefaultAzureCredential instead")
            print("   Make sure you have proper Azure authentication configured")
            return True  # Continue anyway, let DefaultAzureCredential handle it
    else:
        print("🔐 Logging into Azure interactively...")
        try:
            # Use interactive login
            result = subprocess.run([AZ_CMD, 'login'], timeout=300, shell=USE_SHELL)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("❌ Azure login timed out")
            return False

def set_azure_subscription():
    """Set the correct Azure subscription."""
    subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
    if not subscription_id:
        print("❌ AZURE_SUBSCRIPTION_ID environment variable not set")
        return False
        
    print(f"📋 Setting Azure subscription to {subscription_id}")
    try:
        result = subprocess.run([
            AZ_CMD, 'account', 'set', 
            '--subscription', subscription_id
        ], capture_output=True, text=True, timeout=30, shell=USE_SHELL)
        
        if result.returncode == 0:
            print("✅ Azure subscription set successfully")
            return True
        else:
            print(f"❌ Failed to set subscription: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Setting subscription timed out")
        return False

def verify_azure_access():
    """Verify Azure access by listing resource groups."""
    print("🔍 Verifying Azure access...")
    try:
        result = subprocess.run([
            AZ_CMD, 'group', 'list', '--query', '[0].name', '-o', 'tsv'
        ], capture_output=True, text=True, timeout=30, shell=USE_SHELL)
        
        if result.returncode == 0:
            print("✅ Azure access verified")
            return True
        else:
            print(f"❌ Azure access verification failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Azure verification timed out")
        return False

def start_flask_app():
    """Start the Flask application."""
    print("🚀 Starting Challenge Instancer...")
    try:
        # Import the app module
        import app
        
        # Print startup message
        print("🚀 Starting Challenge Instancer with Azure Container Instances")
        print("🔐 CTFd authentication enabled")
        print("☁️  Azure Container Instance integration enabled")
        print("🌐 Server starting at http://localhost:5000")
        
        # Run the app with use_reloader=False to prevent multiple instances
        app.app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
        
    except ImportError as e:
        print(f"❌ Failed to import app.py: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to start Flask app: {e}")
        sys.exit(1)

def main():
    """Main launcher function."""
    print("🎯 Challenge Instancer Launcher")
    print("=" * 40)
    
    # Check if running in Docker mode
    docker_mode = os.getenv('DOCKER_MODE')
    if docker_mode:
        print("🐳 Running in Docker container mode")
    
    # Check if Azure CLI is installed
    if not check_azure_cli():
        print("❌ Azure CLI not found. Please install it first:")
        if not docker_mode:
            print("   winget install Microsoft.AzureCLI")
        sys.exit(1)
    
    print("✅ Azure CLI found")
    
    # Check if already logged in
    if check_azure_auth():
        print("✅ Already logged into Azure")
    else:
        if docker_mode:
            print("🔐 Not logged into Azure, attempting authentication...")
        else:
            print("🔐 Not logged into Azure, starting login process...")
        
        if not azure_login():
            if docker_mode:
                print("⚠️  Azure CLI authentication failed, but continuing anyway...")
                print("   The app will use DefaultAzureCredential for Azure SDK calls")
            else:
                print("❌ Azure login failed")
                sys.exit(1)
        elif not docker_mode:
            print("✅ Azure login successful")
    
    # Set the correct subscription (skip if in Docker mode and login failed)
    if not docker_mode or check_azure_auth():
        if not set_azure_subscription():
            if docker_mode:
                print("⚠️  Failed to set Azure subscription, but continuing...")
            else:
                print("❌ Failed to set Azure subscription")
                sys.exit(1)
    
    # Verify access (skip if in Docker mode and not authenticated via CLI)
    if not docker_mode or check_azure_auth():
        if not verify_azure_access():
            if docker_mode:
                print("⚠️  Azure access verification failed, but continuing...")
            else:
                print("❌ Azure access verification failed")
                sys.exit(1)
    
    print("=" * 40)
    if docker_mode:
        print("🐳 Docker mode authentication complete!")
    else:
        print("🎉 Azure authentication complete!")
    print("📡 Starting Challenge Instancer on http://localhost:5000")
    print("=" * 40)
    
    # Small delay to let user see the messages
    time.sleep(2)
    
    # Start the Flask app
    start_flask_app()

if __name__ == "__main__":
    main()
