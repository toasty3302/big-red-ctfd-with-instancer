#!/usr/bin/env python3
"""
Setup script for Challenge Instancer
This script sets up Azure authentication and dependencies
"""

import subprocess
import sys
import os
import shutil

def install_azure_cli():
    """Install Azure CLI if not present"""
    print("🔧 Checking Azure CLI installation...")
    
    if shutil.which("az"):
        print("✅ Azure CLI already installed")
        return True
    
    print("📦 Installing Azure CLI...")
    try:
        # Use winget to install Azure CLI
        result = subprocess.run([
            "winget", "install", "Microsoft.AzureCLI", "--silent"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Azure CLI installed successfully")
            # Refresh PATH
            os.environ["PATH"] = os.environ["PATH"] + ";C:\\Program Files (x86)\\Microsoft SDKs\\Azure\\CLI2\\wbin"
            return True
        else:
            print(f"❌ Failed to install Azure CLI: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Installation timeout")
        return False
    except Exception as e:
        print(f"❌ Installation error: {e}")
        return False

def setup_azure_login():
    """Setup Azure login"""
    print("🔐 Setting up Azure authentication...")
    
    # Check if already logged in
    try:
        result = subprocess.run([
            "az", "account", "show"
        ], capture_output=True, text=True, check=True)
        
        print("✅ Already logged in to Azure")
        return True
        
    except subprocess.CalledProcessError:
        print("⚠️  Not logged in to Azure")
    
    # Attempt login
    print("🔑 Please complete Azure login...")
    print("💡 This will open a browser window for authentication")
    
    try:
        result = subprocess.run([
            "az", "login"
        ], check=True)
        
        print("✅ Azure login successful")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Azure login failed: {e}")
        return False

def set_azure_subscription():
    """Set the correct Azure subscription"""
    # Azure Configuration
    subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
    if not subscription_id:
        print("❌ AZURE_SUBSCRIPTION_ID environment variable not set")
        print("Please set it in your .env file or environment")
        return False
    
    print(f"🎯 Setting Azure subscription to: {subscription_id}")
    
    try:
        result = subprocess.run([
            "az", "account", "set", "--subscription", subscription_id
        ], check=True)
        
        print("✅ Azure subscription set successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to set subscription: {e}")
        return False

def verify_azure_access():
    """Verify Azure access by listing resource groups"""
    print("🧪 Verifying Azure access...")
    
    try:
        result = subprocess.run([
            "az", "group", "list", "--query", "[].name", "-o", "tsv"
        ], capture_output=True, text=True, check=True)
        
        resource_groups = result.stdout.strip().split('\n')
        print(f"✅ Azure access verified. Found {len(resource_groups)} resource groups:")
        for rg in resource_groups[:5]:  # Show first 5
            print(f"   - {rg}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Azure access verification failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Challenge Instancer Setup")
    print("=" * 40)
    
    # Step 1: Install Azure CLI
    if not install_azure_cli():
        print("❌ Setup failed: Could not install Azure CLI")
        print("💡 Please install Azure CLI manually from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        return False
    
    # Step 2: Setup Azure login
    if not setup_azure_login():
        print("❌ Setup failed: Could not login to Azure")
        return False
    
    # Step 3: Set subscription
    if not set_azure_subscription():
        print("❌ Setup failed: Could not set Azure subscription")
        return False
    
    # Step 4: Verify access
    if not verify_azure_access():
        print("❌ Setup failed: Could not verify Azure access")
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("✅ Azure CLI installed and configured")
    print("✅ Authentication completed")
    print("✅ Subscription set")
    print("✅ Access verified")
    print("\n🚀 You can now run the Challenge Instancer app:")
    print("   python app.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
