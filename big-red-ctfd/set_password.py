#!/usr/bin/env python3
"""
Set CTFd User Password
This script sets a known password for testing the instancer app authentication
"""

import subprocess
from passlib.hash import bcrypt_sha256

def set_ctfd_user_password(username: str, new_password: str):
    """Set a new password for a CTFd user"""
    try:
        # Generate hash using the same method as CTFd
        password_hash = bcrypt_sha256.hash(new_password)
        print(f"Generated password hash: {password_hash}")
        
        # Update the password in the database
        update_sql = f"UPDATE users SET password = '{password_hash}' WHERE name = '{username}';"
        
        result = subprocess.run([
            'docker', 'exec', 'big-red-ctfd-db-1',
            'mysql', '-u', 'ctfd', '-pctfd', 'ctfd',
            '-e', update_sql
        ], capture_output=True, text=True, check=True)
        
        print(f"✅ Password updated successfully for user '{username}'")
        
        # Verify the update
        verify_sql = f"SELECT name, password FROM users WHERE name = '{username}';"
        result = subprocess.run([
            'docker', 'exec', 'big-red-ctfd-db-1',
            'mysql', '-u', 'ctfd', '-pctfd', 'ctfd',
            '-e', verify_sql, '--batch', '--raw'
        ], capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            user_data = lines[1].split('\t')
            stored_hash = user_data[1]
            
            # Test the verification
            is_valid = bcrypt_sha256.verify(new_password, stored_hash)
            if is_valid:
                print(f"✅ Password verification successful!")
                print(f"👤 Username: {username}")
                print(f"🔑 Password: {new_password}")
                return True
            else:
                print(f"❌ Password verification failed!")
                return False
        
        return False
        
    except Exception as e:
        print(f"❌ Error setting password: {e}")
        return False

if __name__ == "__main__":
    print("CTFd User Password Setter")
    print("=" * 30)
    
    username = "toasty"
    new_password = "toasty123"  # Simple password for testing
    
    print(f"Setting password for user '{username}' to '{new_password}'")
    
    if set_ctfd_user_password(username, new_password):
        print(f"\n🎉 SUCCESS!")
        print(f"You can now login to the instancer app with:")
        print(f"   Username: {username}")
        print(f"   Password: {new_password}")
    else:
        print(f"\n❌ FAILED to set password")
