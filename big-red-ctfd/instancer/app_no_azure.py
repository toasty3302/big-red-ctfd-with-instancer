#!/usr/bin/env python3
"""
Challenge Instancer App
Integrates with CTFd for authentication and manages challenge instances (without Azure)
"""

import os
import uuid
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import Error
from passlib.hash import bcrypt_sha256

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# CTFd Database Configuration
CTFD_DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'ctfd',
    'password': 'ctfd',
    'database': 'ctfd'
}

# Challenge definitions (without Azure images)
CHALLENGES = {
    'web-basic': {
        'name': 'Basic Web Challenge',
        'description': 'A simple web application with vulnerabilities',
        'port': 80,
        'category': 'Web'
    },
    'crypto-rsa': {
        'name': 'RSA Crypto Challenge',
        'description': 'Break the RSA encryption',
        'port': 1337,
        'category': 'Crypto'
    },
    'pwn-buffer': {
        'name': 'Buffer Overflow Challenge',
        'description': 'Exploit a buffer overflow vulnerability',
        'port': 9999,
        'category': 'Pwn'
    },
    'forensics-disk': {
        'name': 'Disk Forensics Challenge',
        'description': 'Analyze a disk image for hidden data',
        'port': 8080,
        'category': 'Forensics'
    },
    'eaas-demo': {
        'name': 'EaaS Demo Challenge',
        'description': 'Demo challenge using the EaaS container',
        'port': 1337,
        'category': 'Demo'
    }
}

class ChallengeInstancer:
    def __init__(self):
        # Initialize database (only instances table, users come from CTFd)
        self.init_db()
    
    def init_db(self):
        """Initialize database for tracking instances (users come from CTFd)"""
        try:
            import subprocess
            
            print("🗄️  Initializing challenge instances table...")
            
            # Create instances table in CTFd database
            create_table_sql = '''
            CREATE TABLE IF NOT EXISTS challenge_instances (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                challenge_id VARCHAR(255) NOT NULL,
                container_name VARCHAR(255) UNIQUE NOT NULL,
                fqdn TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'creating',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NULL,
                INDEX idx_user_challenge (user_id, challenge_id),
                INDEX idx_container_name (container_name)
            );
            '''
            
            # Execute via docker
            result = subprocess.run([
                'docker', 'exec', 'big-red-ctfd-db-1', 
                'mysql', '-u', 'ctfd', '-pctfd', 'ctfd', 
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
                'mysql', '-u', 'ctfd', '-pctfd', 'ctfd',
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
        """Create a new challenge instance for the user (MOCK - No Azure)"""
        if challenge_id not in CHALLENGES:
            return {'success': False, 'error': 'Invalid challenge ID'}
        
        challenge = CHALLENGES[challenge_id]
        hex_suffix = self.generate_hex_suffix()
        
        # Generate unique container name and DNS name
        container_name = f"cornell-{challenge_id}-{user_uuid}-{hex_suffix}"
        
        print(f"🚀 Creating mock instance for user {user_uuid}")
        print(f"   Challenge: {challenge['name']}")
        print(f"   Container: {container_name}")
        print("   ⚠️  Note: This is a mock instance - Azure functionality has been removed")
        
        expires_at = datetime.now() + timedelta(hours=4)  # Instance expires in 4 hours
        
        # Generate mock URL
        mock_url = f"http://mock-{container_name}.example.com:{challenge['port']}"
        
        # Store instance in database
        self.store_instance(user_id, challenge_id, container_name, mock_url, expires_at)
        
        print(f"✅ Mock instance created!")
        print(f"   URL: {mock_url}")
        
        return {
            'success': True,
            'url': mock_url,
            'container_name': container_name,
            'expires_at': expires_at.isoformat()
        }
    
    def store_instance(self, user_id: int, challenge_id: str, container_name: str, fqdn: str, expires_at):
        """Store instance in CTFd database"""
        try:
            import subprocess
            
            expires_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')
            
            insert_sql = f'''
            INSERT INTO challenge_instances (user_id, challenge_id, container_name, fqdn, status, expires_at)
            VALUES ({user_id}, '{challenge_id}', '{container_name}', '{fqdn}', 'running', '{expires_str}');
            '''
            
            subprocess.run([
                'docker', 'exec', 'big-red-ctfd-db-1',
                'mysql', '-u', 'ctfd', '-pctfd', 'ctfd',
                '-e', insert_sql
            ], check=True, capture_output=True)
            
        except Exception as e:
            print(f"Error storing instance: {e}")
    
    def get_user_instances(self, user_id: int) -> List[Dict]:
        """Get all instances for a user from CTFd database"""
        try:
            import subprocess
            
            query = f'''
            SELECT challenge_id, container_name, fqdn, status, created_at, expires_at
            FROM challenge_instances 
            WHERE user_id = {user_id} 
            ORDER BY created_at DESC;
            '''
            
            result = subprocess.run([
                'docker', 'exec', 'big-red-ctfd-db-1',
                'mysql', '-u', 'ctfd', '-pctfd', 'ctfd',
                '-e', query, '--batch', '--raw'
            ], capture_output=True, text=True, check=True)
            
            lines = result.stdout.strip().split('\n')
            instances = []
            
            if len(lines) > 1:  # Skip header
                for line in lines[1:]:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 6:
                            challenge_id, container_name, fqdn, status, created_at, expires_at = parts
                            instances.append({
                                'challenge_id': challenge_id,
                                'challenge_name': CHALLENGES.get(challenge_id, {}).get('name', 'Unknown'),
                                'container_name': container_name,
                                'url': fqdn,
                                'status': status,
                                'created_at': created_at,
                                'expires_at': expires_at
                            })
            
            return instances
            
        except Exception as e:
            print(f"Error getting user instances: {e}")
            return []
    
    def delete_instance(self, user_id: int, container_name: str) -> bool:
        """Delete a challenge instance (MOCK - No Azure)"""
        try:
            print(f"🗑️  Mock deleting instance: {container_name}")
            print("   ⚠️  Note: This is a mock deletion - Azure functionality has been removed")
            
            # Update database
            delete_sql = f'''
            UPDATE challenge_instances 
            SET status = 'deleted' 
            WHERE user_id = {user_id} AND container_name = '{container_name}';
            '''
            
            import subprocess
            subprocess.run([
                'docker', 'exec', 'big-red-ctfd-db-1',
                'mysql', '-u', 'ctfd', '-pctfd', 'ctfd',
                '-e', delete_sql
            ], check=True, capture_output=True)
            
            return True
        except Exception as e:
            print(f"Error deleting instance: {e}")
            return False

# Initialize the instancer
instancer = ChallengeInstancer()

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    instances = instancer.get_user_instances(user_id)
    
    return render_template('dashboard.html', 
                         challenges=CHALLENGES, 
                         instances=instances,
                         username=session.get('username'),
                         user_type=session.get('user_type'))

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
        flash(f'Mock instance created! URL: {result["url"]}', 'success')
    else:
        flash(f'Error creating instance: {result["error"]}', 'error')
    
    return redirect(url_for('index'))

@app.route('/delete_instance', methods=['POST'])
def delete_instance():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    container_name = request.form.get('container_name')
    user_id = session['user_id']
    
    if instancer.delete_instance(user_id, container_name):
        flash('Mock instance deleted successfully!', 'success')
    else:
        flash('Error deleting instance!', 'error')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("🚀 Starting Challenge Instancer (No Azure)")
    print("⚠️  Note: Azure functionality has been removed - all instances are mock")
    print("🔐 CTFd authentication is still active")
    print("🌐 Server starting at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
