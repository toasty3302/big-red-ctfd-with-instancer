#!/usr/bin/env python3
"""
Challenge Instancer App
Integrates with CTFd for authentication and creates Azure Container Instances
"""

import os
import uuid
import secrets
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import Error
from passlib.hash import bcrypt_sha256

# Azure imports
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import (
    ContainerGroup, Container, ContainerGroupRestartPolicy,
    ResourceRequirements, ResourceRequests, ContainerPort,
    IpAddress, Port, OperatingSystemTypes, ImageRegistryCredential
)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# Azure Configuration
AZURE_CONFIG = {
    'subscription_id': os.getenv('AZURE_SUBSCRIPTION_ID'),
    'resource_group': os.getenv('AZURE_RESOURCE_GROUP'),
    'location': os.getenv('AZURE_LOCATION'),
    'acr_server': os.getenv('ACR_SERVER'),
    'acr_username': os.getenv('ACR_USERNAME'),
    'acr_password': os.getenv('ACR_PASSWORD')
}

# Validate that all required Azure config is present
for key, value in AZURE_CONFIG.items():
    if not value:
        raise ValueError(f"Missing required environment variable for Azure config: {key.upper()}")

# CTFd Database Configuration
CTFD_DB_CONFIG = {
    'host': os.getenv('CTFD_DB_HOST'),
    'port': int(os.getenv('CTFD_DB_PORT', '3306')),
    'user': os.getenv('CTFD_DB_USER'),
    'password': os.getenv('CTFD_DB_PASSWORD'),
    'database': os.getenv('CTFD_DB_NAME')
}

# Validate that all required database config is present
for key, value in CTFD_DB_CONFIG.items():
    if not value:
        raise ValueError(f"Missing required environment variable for database config: CTFD_DB_{key.upper()}")

# Challenge definitions with Azure Container Registry images
CHALLENGES = {
    'eaas': {
        'name': 'EaaS',
        'description': 'Echo as a Service',
        'image': f"{AZURE_CONFIG['acr_server']}/eaas:latest",
        'port': 1337,
        'category': 'Web'
    },
    'vuln-app': {
        'name': 'Vulnerable Web App',
        'description': 'A simple web application with vulnerabilities',
        'image': f"{AZURE_CONFIG['acr_server']}/vuln-app:latest",  # Using public image as fallback
        'port': 1337,
        'category': 'Web'
    }
}

class ChallengeInstancer:
    def __init__(self):
        # Initialize database (only instances table, users come from CTFd)
        self.init_db()
        
        # Initialize Azure client
        self.setup_azure_auth()
        
        # Start cleanup thread
        self.start_cleanup_thread()
    
    def get_db_password(self):
        """Get database password from environment variable"""
        return os.getenv('CTFD_DB_PASSWORD', 'ctfd')
    
    def setup_azure_auth(self):
        """Setup Azure authentication and container client"""
        try:
            print("🔐 Setting up Azure authentication...")
            self.credential = DefaultAzureCredential()
            self.container_client = ContainerInstanceManagementClient(
                credential=self.credential,
                subscription_id=AZURE_CONFIG['subscription_id']
            )
            print("✅ Azure authentication setup complete")
        except Exception as e:
            print(f"❌ Azure authentication failed: {e}")
            print("💡 Make sure you're logged into Azure CLI: az login")
            self.container_client = None
    
    def init_db(self):
        """Initialize database for tracking instances (users come from CTFd)"""
        try:
            import subprocess
            
            print("🗄️  Initializing instancer_instances table...")
            
            # Create instances table in CTFd database with a unique name
            create_table_sql = '''
            CREATE TABLE IF NOT EXISTS instancer_instances (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                challenge_id VARCHAR(255) NOT NULL,
                container_name VARCHAR(255) UNIQUE NOT NULL,
                fqdn TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'creating',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NULL,
                INDEX idx_user_challenge (user_id, challenge_id),
                INDEX idx_container_name (container_name),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            '''
            
            # Execute via docker
            result = subprocess.run([
                'docker', 'exec', 'big-red-ctfd-db-1', 
                'mysql', '-u', 'ctfd', f'-p{self.get_db_password()}', 'ctfd', 
                '-e', create_table_sql
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Database table created successfully")
            else:
                print(f"⚠️  Database table creation warning: {result.stderr}")
                print("💡 Table might already exist, continuing...")
            
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
            print("💡 Continuing without database table creation...")
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user against CTFd database and return user info if successful"""
        try:
            import subprocess
            import json
            
            # Query CTFd users table via docker exec
            query = f"SELECT id, name, email, password, type FROM users WHERE name = '{username}' LIMIT 1;"
            
            result = subprocess.run([
                'docker', 'exec', 'big-red-ctfd-db-1',
                'mysql', '-u', 'ctfd', f'-p{self.get_db_password()}', 'ctfd',
                '-e', query, '--batch', '--raw'
            ], capture_output=True, text=True, check=True)
            
            lines = result.stdout.strip().split('\n')
            if len(lines) < 2:  # No user found (only header)
                return None
            
            # Parse the result (skip header line)
            user_data = lines[1].split('\t')
            if len(user_data) < 5:
                return None
            
            user_id, name, email, password_hash, user_type = user_data
            
            # Verify password using bcrypt (CTFd uses bcrypt-sha256)
            if self.verify_ctfd_password(password, password_hash):
                return {
                    'id': int(user_id),
                    'username': name,
                    'email': email,
                    'type': user_type
                }
            
            return None
            
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None
    
    def verify_ctfd_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against CTFd's bcrypt-sha256 hash using the same method as CTFd"""
        try:
            # Use the same verification method as CTFd
            return bcrypt_sha256.verify(password, stored_hash)
        except Exception as e:
            print(f"Error verifying password: {e}")
            return False
    
    def generate_hex_suffix(self) -> str:
        """Generate a random 16-character hex string"""
        return secrets.token_hex(8)  # 8 bytes = 16 hex characters
    
    def create_challenge_instance(self, user_id: int, user_uuid: str, challenge_id: str) -> Dict:
        """Create a new challenge instance for the user using Azure Container Instances"""
        if challenge_id not in CHALLENGES:
            return {'success': False, 'error': 'Invalid challenge ID'}
        
        if not self.container_client:
            return {'success': False, 'error': 'Azure authentication not available'}
        
        # Check if user already has an active instance of this challenge
        if self.user_has_active_instance(user_id, challenge_id):
            return {'success': False, 'error': f'You already have an active instance of this challenge. Please delete it first.'}
        
        challenge = CHALLENGES[challenge_id]
        hex_suffix = self.generate_hex_suffix()
        
        # Generate unique container name and DNS name
        container_name = f"cornell-{challenge_id}-{user_uuid}-{hex_suffix}"
        dns_name = container_name  # Azure will create the FQDN
        
        print(f"🚀 Creating Azure container instance for user {user_uuid}")
        print(f"   Challenge: {challenge['name']}")
        print(f"   Container: {container_name}")
        print(f"   Image: {challenge['image']}")
        
        try:
            # Create container group
            container_group = self._create_container_group(
                container_name, 
                challenge['image'], 
                challenge['port'],
                dns_name
            )
            
            # Start the container creation (async)
            print(f"⏳ Starting container creation...")
            operation = self.container_client.container_groups.begin_create_or_update(
                resource_group_name=AZURE_CONFIG['resource_group'],
                container_group_name=container_name,
                container_group=container_group
            )
            
            # Wait for initial creation to start
            time.sleep(2)
            
            # Generate the FQDN
            fqdn = f"{dns_name}.{AZURE_CONFIG['location'].lower().replace(' ', '')}.azurecontainer.io"
            challenge_url = f"http://{fqdn}:{challenge['port']}"
            
            # Use UTC time to avoid timezone issues
            from datetime import timezone
            current_time = datetime.now(timezone.utc).replace(tzinfo=None)  # Remove timezone info for MySQL
            expires_at = current_time + timedelta(minutes=15)  # Instance expires in 15 minutes
            
            print(f"🕐 Current time (UTC): {current_time}")
            print(f"⏰ Expires at (UTC): {expires_at}")
            
            # Store instance in database
            self.store_instance(user_id, challenge_id, container_name, challenge_url, expires_at)
            
            print(f"✅ Container creation initiated!")
            print(f"   URL: {challenge_url}")
            print(f"   Note: Container may take 1-2 minutes to be fully accessible")
            
            return {
                'success': True,
                'url': challenge_url,
                'container_name': container_name,
                'expires_at': expires_at.isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error creating container: {e}")
            return {'success': False, 'error': f'Container creation failed: {str(e)}'}

    def _create_container_group(self, container_name: str, image: str, port: int, dns_name: str):
        """Create Azure Container Group configuration"""
        
        # Container configuration
        container = Container(
            name=container_name,
            image=image,
            resources=ResourceRequirements(
                requests=ResourceRequests(
                    memory_in_gb=0.5,
                    cpu=0.25
                )
            ),
            ports=[ContainerPort(port=port)]
        )
        
        # Only add registry credentials for ACR images
        registry_credentials = []
        if AZURE_CONFIG['acr_server'] in image:
            registry_credentials = [
                ImageRegistryCredential(
                    server=AZURE_CONFIG['acr_server'],
                    username=AZURE_CONFIG['acr_username'],
                    password=AZURE_CONFIG['acr_password']
                )
            ]
        
        # Container group with public IP and DNS
        container_group = ContainerGroup(
            location=AZURE_CONFIG['location'],
            containers=[container],
            os_type=OperatingSystemTypes.linux,
            restart_policy=ContainerGroupRestartPolicy.never,
            ip_address=IpAddress(
                type="Public",
                ports=[Port(protocol="TCP", port=port)],
                dns_name_label=dns_name
            ),
            tags={
                'environment': 'ctf',
                'challenge': container_name.split('-')[1],
                'created_by': 'challenge_instancer'
            }
        )
        
        # Add registry credentials only if we have them
        if registry_credentials:
            container_group.image_registry_credentials = registry_credentials
        
        return container_group
    
    def store_instance(self, user_id: int, challenge_id: str, container_name: str, fqdn: str, expires_at):
        """Store instance in CTFd database"""
        try:
            import subprocess
            
            expires_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')
            
            insert_sql = f'''
            INSERT INTO instancer_instances (user_id, challenge_id, container_name, fqdn, status, expires_at)
            VALUES ({user_id}, '{challenge_id}', '{container_name}', '{fqdn}', 'running', '{expires_str}');
            '''
            
            subprocess.run([
                'docker', 'exec', 'big-red-ctfd-db-1',
                'mysql', '-u', 'ctfd', f'-p{self.get_db_password()}', 'ctfd',
                '-e', insert_sql
            ], check=True, capture_output=True)
            
        except Exception as e:
            print(f"Error storing instance: {e}")
    
    def user_has_active_instance(self, user_id: int, challenge_id: str) -> bool:
        """Check if user already has an active instance of this challenge"""
        try:
            import subprocess
            
            query = f'''
            SELECT COUNT(*) as count
            FROM instancer_instances 
            WHERE user_id = {user_id} 
            AND challenge_id = '{challenge_id}' 
            AND status IN ('creating', 'running');
            '''
            
            result = subprocess.run([
                'docker', 'exec', 'big-red-ctfd-db-1',
                'mysql', '-u', 'ctfd', f'-p{self.get_db_password()}', 'ctfd',
                '-e', query, '--batch', '--raw'
            ], capture_output=True, text=True, check=True)
            
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # Skip header
                count = int(lines[1])
                return count > 0
            
            return False
            
        except Exception as e:
            print(f"Error checking active instances: {e}")
            return False

    def get_user_instances(self, user_id: int) -> List[Dict]:
        """Get all active instances for a user from CTFd database"""
        try:
            import subprocess
            
            query = f'''
            SELECT challenge_id, container_name, fqdn, status, created_at, expires_at
            FROM instancer_instances 
            WHERE user_id = {user_id} 
            AND status != 'deleted'
            ORDER BY created_at DESC;
            '''
            
            print(f"🔍 Querying instances for user_id: {user_id}")
            
            result = subprocess.run([
                'docker', 'exec', 'big-red-ctfd-db-1',
                'mysql', '-u', 'ctfd', f'-p{self.get_db_password()}', 'ctfd',
                '-e', query, '--batch', '--raw'
            ], capture_output=True, text=True, check=True)
            
            print(f"📊 Query result stdout: {repr(result.stdout)}")
            print(f"📊 Query result stderr: {repr(result.stderr)}")
            
            lines = result.stdout.strip().split('\n')
            instances = []
            
            print(f"📝 Number of lines returned: {len(lines)}")
            
            if len(lines) > 1:  # Skip header
                for i, line in enumerate(lines[1:], 1):
                    print(f"📄 Processing line {i}: {repr(line)}")
                    if line.strip():
                        parts = line.split('\t')
                        print(f"🔧 Parts split: {parts}")
                        if len(parts) >= 6:
                            challenge_id, container_name, fqdn, status, created_at, expires_at = parts
                            instance = {
                                'challenge_id': challenge_id,
                                'challenge_name': CHALLENGES.get(challenge_id, {}).get('name', 'Unknown'),
                                'container_name': container_name,
                                'url': fqdn,
                                'status': status,
                                'created_at': created_at,
                                'expires_at': expires_at if expires_at != 'NULL' else None
                            }
                            instances.append(instance)
                            print(f"✅ Added instance: {instance}")
                        else:
                            print(f"⚠️  Line has {len(parts)} parts, expected 6")
            else:
                print("📭 No data rows found (only header or empty result)")
            
            print(f"🎯 Final instances count: {len(instances)}")
            return instances
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Database command failed with return code {e.returncode}")
            print(f"   stdout: {e.stdout}")
            print(f"   stderr: {e.stderr}")
            return []
        except Exception as e:
            print(f"❌ Error getting user instances: {e}")
            return []
    
    def delete_instance(self, user_id: int, container_name: str) -> bool:
        """Delete a challenge instance from Azure and update database"""
        try:
            print(f"🗑️  Deleting Azure container instance: {container_name}")
            
            if self.container_client:
                # Delete from Azure
                try:
                    operation = self.container_client.container_groups.begin_delete(
                        resource_group_name=AZURE_CONFIG['resource_group'],
                        container_group_name=container_name
                    )
                    print(f"✅ Azure container deletion initiated")
                except Exception as azure_error:
                    print(f"⚠️  Azure deletion warning: {azure_error}")
                    print("💡 Container might already be deleted or not exist")
            else:
                print("⚠️  Azure client not available, skipping Azure deletion")
            
            # Update database
            delete_sql = f'''
            UPDATE instancer_instances 
            SET status = 'deleted' 
            WHERE user_id = {user_id} AND container_name = '{container_name}';
            '''
            
            import subprocess
            subprocess.run([
                'docker', 'exec', 'big-red-ctfd-db-1',
                'mysql', '-u', 'ctfd', f'-p{self.get_db_password()}', 'ctfd',
                '-e', delete_sql
            ], check=True, capture_output=True)
            
            print(f"✅ Instance {container_name} deleted successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting instance: {e}")
            return False
    
    def cleanup_expired_instances(self):
        """Delete expired instances from Azure and mark as deleted in database"""
        try:
            import subprocess
            
            print("🧹 Starting cleanup of expired instances...")
            
            # Find expired instances
            query = '''
            SELECT user_id, challenge_id, container_name, fqdn, expires_at
            FROM instancer_instances 
            WHERE status IN ('creating', 'running')
            AND expires_at <= NOW();
            '''
            
            result = subprocess.run([
                'docker', 'exec', 'big-red-ctfd-db-1',
                'mysql', '-u', 'ctfd', f'-p{self.get_db_password()}', 'ctfd',
                '-e', query, '--batch', '--raw'
            ], capture_output=True, text=True, check=True)
            
            lines = result.stdout.strip().split('\n')
            expired_count = 0
            
            if len(lines) > 1:  # Skip header
                for line in lines[1:]:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 5:
                            user_id, challenge_id, container_name, fqdn, expires_at = parts
                            print(f"🗑️  Deleting expired instance: {container_name}")
                            
                            # Delete from Azure
                            if self.container_client:
                                try:
                                    self.container_client.container_groups.begin_delete(
                                        resource_group_name=AZURE_CONFIG['resource_group'],
                                        container_group_name=container_name
                                    )
                                    print(f"   ✅ Deleted from Azure: {container_name}")
                                except Exception as e:
                                    print(f"   ⚠️  Azure deletion warning for {container_name}: {e}")
                            
                            # Update database
                            delete_sql = f'''
                            UPDATE instancer_instances 
                            SET status = 'deleted' 
                            WHERE container_name = '{container_name}';
                            '''
                            
                            subprocess.run([
                                'docker', 'exec', 'big-red-ctfd-db-1',
                                'mysql', '-u', 'ctfd', f'-p{self.get_db_password()}', 'ctfd',
                                '-e', delete_sql
                            ], check=True, capture_output=True)
                            
                            expired_count += 1
            
            if expired_count > 0:
                print(f"🧹 Cleanup completed: {expired_count} expired instances deleted")
            else:
                print("🧹 No expired instances found")
                
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
    
    def start_cleanup_thread(self):
        """Start background thread to cleanup expired instances every 10 minutes"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(30)  # Wait 30 seconds
                    self.cleanup_expired_instances()
                except Exception as e:
                    print(f"❌ Cleanup thread error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        print("🧹 Started automatic cleanup thread (every 30 seconds)")

# Initialize the instancer
instancer = ChallengeInstancer()

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    print(f"🔍 Index requested by user_id: {user_id}, username: {session.get('username')}")
    
    instances = instancer.get_user_instances(user_id)
    print(f"🎯 Retrieved {len(instances)} instances for index")
    for i, instance in enumerate(instances):
        print(f"   Instance {i+1}: {instance}")
    
    # Create a set of challenge IDs that already have active instances
    active_challenge_ids = set()
    for instance in instances:
        if instance['status'] in ['creating', 'running']:
            active_challenge_ids.add(instance['challenge_id'])
    
    print(f"🔒 Active challenge IDs: {active_challenge_ids}")
    
    # Generate a simple user UUID for display (not for security)
    import hashlib
    user_uuid_display = hashlib.md5(session['username'].encode()).hexdigest()[:8]
    
    return render_template('dashboard.html', 
                         challenges=CHALLENGES, 
                         instances=instances,
                         active_challenge_ids=active_challenge_ids,
                         username=session.get('username'),
                         user_type=session.get('user_type'),
                         user_uuid=user_uuid_display)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user_data = instancer.authenticate_user(username, password)
        if user_data:
            session['user_id'] = user_data['id']
            session['username'] = user_data['username']
            session['email'] = user_data['email']
            session['user_type'] = user_data['type']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials! Please use your CTFd login.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Registration is disabled - users must be created in CTFd
    flash('Registration is disabled. Please register on the main CTFd platform first.', 'info')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/delete_instance', methods=['POST'])
def delete_instance():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    container_name = request.form.get('container_name')
    user_id = session['user_id']
    
    if not container_name:
        return jsonify({'success': False, 'error': 'Container name required'})
    
    result = instancer.delete_instance(user_id, container_name)
    
    if result:
        return jsonify({'success': True, 'message': 'Instance deleted successfully'})
    else:
        return jsonify({'success': False, 'error': 'Failed to delete instance'})

@app.route('/cleanup', methods=['POST'])
def manual_cleanup():
    """Manual cleanup endpoint for testing/admin purposes"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    try:
        instancer.cleanup_expired_instances()
        return jsonify({'success': True, 'message': 'Cleanup completed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Cleanup failed: {str(e)}'})

@app.route('/create_instance', methods=['POST'])
def create_instance():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    challenge_id = request.form.get('challenge_id')
    user_id = session['user_id']
    username = session['username']
    
    # Generate user UUID for container naming
    user_uuid = str(uuid.uuid4())[:8]  # Short UUID for container names
    
    result = instancer.create_challenge_instance(user_id, user_uuid, challenge_id)
    
    if result['success']:
        flash(f'Container instance created! URL: {result["url"]} (may take 1-2 minutes to be accessible)', 'success')
    else:
        flash(f'Error creating instance: {result["error"]}', 'error')
    
    return redirect(url_for('index'))

def start_app():
    """Start the Flask application"""
    print("🚀 Starting Challenge Instancer with Azure Container Instances")
    print("🔐 CTFd authentication enabled")
    print("☁️  Azure Container Instance integration enabled")
    print("🌐 Server starting at http://localhost:5000")
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)

if __name__ == '__main__':
    start_app()
