#!/usr/bin/env python3
"""
Test CTFd Password Verification
This script tests if we can properly verify CTFd passwords using the same method as CTFd
"""

import os
import subprocess
from passlib.hash import bcrypt_sha256

def test_ctfd_password_verification():
    """Test password verification against the actual CTFd database"""
    try:
        # Get database password from environment
        db_password = os.getenv('CTFD_DB_PASSWORD', 'ctfd')
        
        # Get the actual user data from CTFd database
        query = "SELECT name, password FROM users WHERE name = 'toasty' LIMIT 1;"
        
        result = subprocess.run([
            'docker', 'exec', 'big-red-ctfd-db-1',
            'mysql', '-u', 'ctfd', f'-p{db_password}', 'ctfd',
            '-e', query, '--batch', '--raw'
        ], capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            print("❌ User 'toasty' not found")
            return False
        
        # Parse the result (skip header line)
        user_data = lines[1].split('\t')
        if len(user_data) < 2:
            print("❌ Invalid user data format")
            return False
        
        username, stored_hash = user_data
        print(f"👤 Testing user: {username}")
        print(f"🔑 Stored hash: {stored_hash[:50]}...")
        
        # Test with different passwords
        test_passwords = [
            "Dcba!2345",   # The actual password in the database
            "password123",  # Common password
            "toasty",       # Username as password
            "admin",        # Simple admin password
            "123456",       # Very simple password
            "cornell",      # CTF team name
            ""              # Empty password
        ]
        
        print("\n🧪 Testing password verification:")
        for test_password in test_passwords:
            try:
                is_valid = bcrypt_sha256.verify(test_password, stored_hash)
                status = "✅ MATCH" if is_valid else "❌ No match"
                print(f"   '{test_password}' -> {status}")
                
                if is_valid:
                    print(f"\n🎉 SUCCESS! Password for user '{username}' is: '{test_password}'")
                    return True
                    
            except Exception as e:
                print(f"   '{test_password}' -> ❌ Error: {e}")
        
        print(f"\n⚠️  None of the test passwords worked for user '{username}'")
        print("💡 Try manually setting a password for the 'toasty' user in CTFd")
        return False
        
    except Exception as e:
        print(f"❌ Error testing password verification: {e}")
        return False

if __name__ == "__main__":
    print("CTFd Password Verification Test")
    print("=" * 40)
    
    try:
        # First install passlib if not installed
        import passlib
        print("✅ passlib is available")
    except ImportError:
        print("❌ passlib not found. Installing...")
        subprocess.run(['pip', 'install', 'passlib'], check=True)
        print("✅ passlib installed")
    
    test_ctfd_password_verification()
