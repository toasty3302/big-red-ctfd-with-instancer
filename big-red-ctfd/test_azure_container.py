#!/usr/bin/env python3
"""
Sample script to test Azure Container Instance creation
Run this to test if your Azure configuration is working
"""

import sys
import os
import time
from datetime import datetime

# Add the current directory to Python path so we can import the azure_client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock CTFd's get_config function since we're running outside CTFd
class MockCTFdUtils:
    @staticmethod
    def get_config(key):
        # Return None for all config calls since we hardcoded the subscription ID
        return None

# Replace CTFd.utils with our mock
sys.modules['CTFd.utils'] = MockCTFdUtils()

# Now import our Azure client
from CTFd.plugins.challenge_instancer.azure_client import AzureContainerClient

def test_azure_container():
    """Test creating and managing an Azure Container Instance"""
    
    print("🚀 Testing Azure Container Instance Creation")
    print("=" * 60)
    
    # Generate a unique container name
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    container_name = f"test-nginx-{timestamp}"
    
    print(f"Container Name: {container_name}")
    print(f"Docker Image: nginx:alpine")
    print(f"CPU: 0.5 cores")
    print(f"Memory: 0.5 GB")
    print(f"Port: 1337")
    print("=" * 60)
    
    try:
        # Initialize the Azure client
        print("🔧 Initializing Azure client...")
        azure_client = AzureContainerClient()
        print("✅ Azure client initialized successfully!")
        print(f"   Subscription ID: {azure_client.subscription_id}")
        print(f"   Resource Group: {azure_client.resource_group}")
        
        # Create the container instance
        print("\n⏳ Creating container instance...")
        result = azure_client.create_container_instance(
            name=container_name,
            image="nginx:alpine",
            cpu=0.5,
            memory=0.5,
            port=1337
        )
        
        print("🎉 Container instance created successfully!")
        print("\n📋 Container Details:")
        print(f"   Name: {result['name']}")
        print(f"   FQDN: {result['fqdn']}")
        print(f"   IP Address: {result['ip']}")
        print(f"   State: {result['state']}")
        print(f"   Access URL: http://{result['fqdn']}:1337")
        
        # Wait for container to start
        print("\n⏳ Waiting 30 seconds for container to start...")
        time.sleep(30)
        
        # Check the status
        print("🔍 Checking container status...")
        status = azure_client.get_container_status(container_name)
        print(f"   Current State: {status['state']}")
        
        if status.get('events'):
            print("   Recent Events:")
            for event in status['events'][-3:]:  # Show last 3 events
                timestamp = event.get('timestamp', 'Unknown time')
                print(f"     - [{timestamp}] {event['type']}: {event['message']}")
        
        # Ask if user wants to delete the container
        print(f"\n❓ Test complete! Container '{container_name}' is running.")
        choice = input("Do you want to delete the test container now? (y/n): ").lower().strip()
        
        if choice == 'y' or choice == 'yes':
            print(f"\n🗑️  Deleting container '{container_name}'...")
            azure_client.delete_container_instance(container_name)
            print("✅ Container deleted successfully!")
        else:
            print(f"\n⚠️  Container '{container_name}' left running.")
            print(f"   Remember to delete it manually to avoid charges!")
            print(f"   Command: az container delete --resource-group {azure_client.resource_group} --name {container_name}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Make sure you're logged into Azure CLI: az login")
        print("2. Verify your subscription ID is correct")
        print("3. Check that the resource group 'ctfd-instances' exists")
        print("4. Ensure you have Contributor permissions on the subscription")
        return False

def list_existing_containers():
    """List any existing test containers"""
    print("\n📋 Checking for existing test containers...")
    
    try:
        azure_client = AzureContainerClient()
        containers = azure_client.list_user_instances("test-")
        
        if containers:
            print(f"Found {len(containers)} test containers:")
            for container in containers:
                print(f"   - {container['name']}: {container['state']}")
                if container['fqdn']:
                    print(f"     URL: http://{container['fqdn']}:1337")
        else:
            print("No test containers found.")
            
        return containers
        
    except Exception as e:
        print(f"❌ Error listing containers: {str(e)}")
        return []

if __name__ == "__main__":
    print("Azure Container Instance Test Script")
    print("====================================")
    
    # Check if running in the correct directory
    if not os.path.exists("CTFd/plugins/challenge_instancer/azure_client.py"):
        print("❌ Error: This script must be run from the big-red-ctfd directory")
        print("   Please cd to the directory containing the CTFd folder")
        sys.exit(1)
    
    print("\nWhat would you like to do?")
    print("1. Create and test a new container")
    print("2. List existing test containers")
    print("3. Both")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        test_azure_container()
    elif choice == "2":
        list_existing_containers()
    elif choice == "3":
        list_existing_containers()
        print("\n" + "="*60)
        test_azure_container()
    else:
        print("Invalid choice. Exiting.")
