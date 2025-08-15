#!/usr/bin/env python3
"""
Test the correct password
"""

import os
import subprocess
from passlib.hash import bcrypt_sha256

# Get database password from environment
db_password = os.getenv('CTFD_DB_PASSWORD', 'ctfd')

# Get the stored hash
result = subprocess.run([
    'docker', 'exec', 'big-red-ctfd-db-1',
    'mysql', '-u', 'ctfd', f'-p{db_password}', 'ctfd',
    '-e', "SELECT password FROM users WHERE name = 'toasty';",
    '--batch', '--raw'
], capture_output=True, text=True, check=True)

stored_hash = result.stdout.strip().split('\n')[1]

print("Testing password verification...")
print("Password: Dcba!2345")
print(f"Hash: {stored_hash[:50]}...")

try:
    is_valid = bcrypt_sha256.verify('Dcba!2345', stored_hash)
    print(f"Verification result: {is_valid}")
    
    if is_valid:
        print("✅ SUCCESS! Password verification works correctly!")
    else:
        print("❌ FAILED! Password verification failed!")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
