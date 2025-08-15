#!/usr/bin/env python3
"""
Simple Azure Container Instance test
This directly uses Azure SDK without CTFd dependencies
"""

import os
import time
from datetime import datetime

# Direct Azure imports
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import *
from azure.mgmt.containerinstance.models import ImageRegistryCredential

class SimpleAzureTest:
    def __init__(self):
        # Load from environment variables
        self.subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
        self.resource_group = os.getenv('AZURE_RESOURCE_GROUP')
        self.location = os.getenv('AZURE_LOCATION')
        
        # Validate required environment variables
        if not all([self.subscription_id, self.resource_group, self.location]):
            raise ValueError("Missing required environment variables: AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, AZURE_LOCATION")
        
        # Initialize Azure client
        credential = DefaultAzureCredential()
        self.client = ContainerInstanceManagementClient(credential, self.subscription_id)
    
    def create_test_container(self, image_choice="hello", user_id="user"):
        # Generate unique name with microseconds and user ID to avoid collisions
        import random
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")  # includes microseconds
        random_suffix = random.randint(1000, 9999)
        unique_id = f"{user_id}-{timestamp}-{random_suffix}"
        
        # Different image options to avoid Docker Hub issues
        images = {
            "hello": {
                "image": "mcr.microsoft.com/hello-world",
                "port": 80,
                "name": f"test-hello-{unique_id}"
            },
            "nginx": {
                "image": "nginx:alpine", 
                "port": 1337,
                "name": f"test-nginx-{unique_id}"
            },
            "httpd": {
                "image": "mcr.microsoft.com/oss/httpd/httpd:2.4",
                "port": 80,
                "name": f"test-httpd-{unique_id}"
            },
            "ssh": {
                "image": "lscr.io/linuxserver/openssh-server:latest",
                "port": 2222,
                "name": f"test-ssh-{unique_id}",
                "env": [
                    EnvironmentVariable(name="PUID", value="1000"),
                    EnvironmentVariable(name="PGID", value="1000"),
                    EnvironmentVariable(name="TZ", value="Etc/UTC"),
                    EnvironmentVariable(name="PUBLIC_KEY_URL", value="https://github.com/Cornell-Cybersecurity-Club.keys"),
                    EnvironmentVariable(name="SUDO_ACCESS", value="true"),
                    EnvironmentVariable(name="PASSWORD_ACCESS", value="true"),
                    EnvironmentVariable(name="USER_PASSWORD", value="ctfd123"),
                    EnvironmentVariable(name="USER_NAME", value="ctfuser")
                ]
            },
            "ubuntu": {
                "image": "ubuntu:22.04",
                "port": 22,
                "name": f"test-ubuntu-{unique_id}",
                "command": ["/bin/bash", "-c", "apt-get update && apt-get install -y openssh-server nginx && echo 'ctfuser:ctfd123' | chpasswd && useradd -m -s /bin/bash ctfuser && echo 'ctfuser:ctfd123' | chpasswd && service ssh start && nginx -g 'daemon off;'"]
            },
            "eaas": {
                "image": "cornellctfregistry2.azurecr.io/eaas:latest",
                "port": 1337,
                "name": f"test-eaas-{unique_id}"
            },
            "eaas-dockerhub": {
                "image": "toasty3302/eaas",
                "port": 1337,
                "name": f"test-eaas-dh-{unique_id}"
            }
        }
        
        config = images[image_choice]
        name = config["name"]
        image = config["image"]
        port = config["port"]
        
        print(f"🚀 Creating container: {name}")
        print(f"   Image: {image}")
        print(f"   Port: {port}")
        
        # Build container configuration (optimized for cost)
        container_config = {
            "name": name,
            "image": image,
            "resources": ResourceRequirements(
                requests=ResourceRequests(memory_in_gb=0.5, cpu=0.25)  # Reduced from 1GB/0.5CPU
            ),
            "ports": [ContainerPort(port=port, protocol=ContainerNetworkProtocol.TCP)]
        }
        
        # Add environment variables if specified
        if "env" in config:
            container_config["environment_variables"] = config["env"]
            print(f"   Environment variables: {len(config['env'])} vars")
        
        # Add command if specified
        if "command" in config:
            container_config["command"] = config["command"]
            print(f"   Custom command: {' '.join(config['command'][:3])}...")
        
        # Container configuration
        container = Container(**container_config)
        
        # Registry credentials - support both Docker Hub and ACR
        image_registry_credentials = []
        
        print(f"🔍 Checking image registry for: {image}")
        
        # Determine which registry is being used
        if "cornellctfregistry2.azurecr.io" in image:
            print("   🏢 Registry Type: Azure Container Registry (ACR)")
            print("   ✅ No Docker Hub rate limits apply!")
        elif "index.docker.io" in image or "docker.io" in image or ("/" in image and not "." in image.split("/")[0]):
            print("   🐳 Registry Type: Docker Hub")
            print("   ⚠️  Docker Hub rate limits may apply")
        elif "mcr.microsoft.com" in image:
            print("   🏢 Registry Type: Microsoft Container Registry")
            print("   ✅ No Docker Hub rate limits apply!")
        elif "lscr.io" in image:
            print("   🏢 Registry Type: LinuxServer.io Registry")
            print("   ✅ No Docker Hub rate limits apply!")
        else:
            print("   ❓ Registry Type: Unknown/Other")
        
        # Add Docker Hub credentials for Docker Hub images
        if "index.docker.io" in image or "docker.io" in image or "/" in image and not "." in image.split("/")[0]:
            image_registry_credentials.append(
                ImageRegistryCredential(
                    server="index.docker.io",
                    username="toasty3302",
                    password="Dcba!2345"
                )
            )
            print("   🔑 Added Docker Hub credentials")
        
        # Add ACR credentials for ACR images
        if "cornellctfregistry2.azurecr.io" in image:
            image_registry_credentials.append(
                ImageRegistryCredential(
                    server="cornellctfregistry2.azurecr.io",
                    username="cornellctfregistry2",
                    password="ej+DIEuslL1v0XEmNv+aDecnkYyQ2Ct+Qeo78bjY/F+ACRCaTOJg"
                )
            )
            print("   🔑 Added ACR credentials for cornellctfregistry2.azurecr.io")
        
        if not image_registry_credentials:
            print("   ℹ️  No registry credentials needed (using public registry)")
        
        print(f"   📊 Total credentials configured: {len(image_registry_credentials)}")
        
        # Public IP configuration with custom DNS name
        dns_name = f"cornell-{image_choice}-{unique_id}".replace("_", "-")[:63]  # DNS name limit
        ip_config = IpAddress(
            type=ContainerGroupIpAddressType.PUBLIC,
            dns_name_label=dns_name,
            ports=[Port(port=port, protocol=ContainerNetworkProtocol.TCP)]
        )
        
        # Container group
        container_group = ContainerGroup(
            location=self.location,
            containers=[container],
            os_type=OperatingSystemTypes.LINUX,
            ip_address=ip_config,
            restart_policy=ContainerGroupRestartPolicy.NEVER,
            image_registry_credentials=image_registry_credentials,
            tags={"test": "cornell"}
        )
        
        # Create the container
        operation = self.client.container_groups.begin_create_or_update(
            self.resource_group, name, container_group
        )
        
        print("⏳ Waiting for container creation...")
        result = operation.result()
        
        print("✅ Container created successfully!")
        print(f"   Name: {result.name}")
        print(f"   DNS Name: {dns_name}")
        print(f"   FQDN: {result.ip_address.fqdn}")
        print(f"   IP: {result.ip_address.ip}")
        print(f"   URL: http://{result.ip_address.fqdn}:{port}")
        
        return name, result, port
    
    def check_status(self, name):
        print(f"🔍 Checking status of {name}...")
        container_group = self.client.container_groups.get(self.resource_group, name)
        
        if container_group.instance_view:
            state = container_group.instance_view.state
            print(f"   State: {state}")
            
            if container_group.instance_view.events:
                print("   Recent events:")
                for event in container_group.instance_view.events[-3:]:
                    print(f"     - {event.type}: {event.message}")
        else:
            print("   No instance view available")
    
    def delete_container(self, name):
        print(f"🗑️  Deleting container: {name}")
        operation = self.client.container_groups.begin_delete(self.resource_group, name)
        operation.result()
        print("✅ Container deleted!")

def main():
    print("Simple Azure Container Instance Test")
    print("===================================")
    
    # Ask user which image to try
    print("\nWhich container image would you like to test?")
    print("1. Microsoft Hello World (mcr.microsoft.com/hello-world)")
    print("2. Microsoft HTTP Server (mcr.microsoft.com/oss/httpd/httpd:2.4)")
    print("3. Docker Hub Nginx (nginx:alpine) - might fail due to registry issues")
    print("4. SSH Server (LinuxServer OpenSSH) - user: ctfuser, pass: ctfd123")
    print("5. Ubuntu with SSH & Nginx - user: ctfuser, pass: ctfd123")
    print("6. EaaS Web Server from ACR (cornellctfregistry2.azurecr.io/eaas) - port 1337")
    print("7. EaaS Web Server from Docker Hub (toasty3302/eaas) - port 1337")
    
    choice = input("\nEnter choice (1-7) or press Enter for option 1: ").strip()
    
    image_map = {"1": "hello", "2": "httpd", "3": "nginx", "4": "ssh", "5": "ubuntu", "6": "eaas", "7": "eaas-dockerhub", "": "hello"}
    image_choice = image_map.get(choice, "hello")
    
    try:
        azure = SimpleAzureTest()
        print(f"✅ Connected to Azure subscription: {azure.subscription_id}")
        
        # Create container
        user_id = input("Enter user ID (or press Enter for 'testuser'): ").strip() or "testuser"
        name, result, port = azure.create_test_container(image_choice, user_id)
        
        # Show connection info
        if image_choice in ["ssh", "ubuntu"]:
            print(f"\n🔐 SSH Connection Info:")
            print(f"   Host: {result.ip_address.fqdn}")
            print(f"   Port: {port}")
            print(f"   Username: ctfuser")
            print(f"   Password: ctfd123")
            print(f"   Command: ssh -p {port} ctfuser@{result.ip_address.fqdn}")
        
        # Wait a bit
        print("\n⏳ Waiting 30 seconds for startup...")
        time.sleep(30)
        
        # Check status
        azure.check_status(name)
        
        # Ask about cleanup
        choice = input("\nDelete the test container? (y/n): ").lower().strip()
        if choice in ['y', 'yes']:
            azure.delete_container(name)
        else:
            print(f"⚠️  Container '{name}' left running - remember to clean up!")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        
        if "RegistryErrorResponse" in str(e):
            print("\n🔧 Docker Hub is experiencing issues. Try:")
            print("   1. Wait a few minutes and retry")
            print("   2. Use option 1 or 2 (Microsoft Container Registry)")
            print("   3. Check Docker Hub status: https://status.docker.com/")
        else:
            print("\nTroubleshooting:")
            print("- Make sure you're logged in: az login")
            print("- Check your subscription ID is correct")
            print("- Verify the resource group exists")

if __name__ == "__main__":
    main()
