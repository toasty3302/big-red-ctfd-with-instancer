#!/usr/bin/env python3
"""
Azure Authentication Helper
This script provides guidance for setting up Azure authentication
"""

import subprocess
import sys
import os

def check_azure_auth():
    """Check if Azure authentication is working"""
    print("🔍 Checking Azure authentication status...")
    
    # Check if Azure CLI is available
    try:
        result = subprocess.run(["az", "--version"], capture_output=True, text=True, check=True)
        print("✅ Azure CLI is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Azure CLI not found")
        print("📖 Please install Azure CLI:")
        print("   Method 1: Download from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        print("   Method 2: Run 'winget install Microsoft.AzureCLI'")
        return False
    
    # Check if logged in
    try:
        result = subprocess.run(["az", "account", "show"], capture_output=True, text=True, check=True)
        print("✅ Logged in to Azure")
        
        # Parse account info
        import json
        account_info = json.loads(result.stdout)
        print(f"   Account: {account_info.get('user', {}).get('name', 'N/A')}")
        print(f"   Subscription: {account_info.get('name', 'N/A')}")
        print(f"   Subscription ID: {account_info.get('id', 'N/A')}")
        
        return True
        
    except subprocess.CalledProcessError:
        print("❌ Not logged in to Azure")
        print("📖 Please login to Azure:")
        print("   Run: az login")
        return False

def provide_setup_instructions():
    """Provide setup instructions"""
    print("\n📋 Setup Instructions:")
    print("=" * 30)
    
    print("1. Install Azure CLI:")
    print("   winget install Microsoft.AzureCLI")
    print("   OR download from: https://aka.ms/installazurecliwindows")
    
    print("\n2. Login to Azure:")
    print("   az login")
    
    print("\n3. Set the correct subscription:")
    print("2. Set the subscription with:")
    print(f"   az account set --subscription {os.getenv('AZURE_SUBSCRIPTION_ID', 'YOUR_SUBSCRIPTION_ID')}")
    
    print("\n4. Verify access:")
    print("   az group list")
    
    print("\n5. Run the instancer app:")
    print("   python app.py")

if __name__ == "__main__":
    if not check_azure_auth():
        provide_setup_instructions()
        sys.exit(1)
    else:
        print("\n✅ Azure authentication is properly configured!")
        print("🚀 You can now run the Challenge Instancer app.")
        sys.exit(0)
