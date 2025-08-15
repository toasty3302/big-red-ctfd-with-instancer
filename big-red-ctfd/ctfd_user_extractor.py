#!/usr/bin/env python3
"""
CTFd User Database Extractor
This script connects to the CTFd database and extracts usernames and passwords.
"""

import os
import sys
import configparser
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL
from tabulate import tabulate

def process_string_var(value):
    """Process string variables from config (copied from CTFd config.py)"""
    if value == "":
        return None

    if value.isdigit():
        return int(value)
    elif value.replace(".", "", 1).isdigit():
        return float(value)

    try:
        from distutils.util import strtobool
        return bool(strtobool(value))
    except ValueError:
        return value

def empty_str_cast(value, default=None):
    """Cast empty strings (copied from CTFd config.py)"""
    if value == "":
        return default
    return value

def get_ctfd_database_url():
    """Get the CTFd database URL from config or Docker environment"""
    # First, try to connect to the Docker MariaDB service
    # This matches the docker-compose.yml configuration
    docker_database_url = "mysql+pymysql://ctfd:ctfd@localhost:3306/ctfd"
    
    # Get the CTFd directory
    ctfd_dir = os.path.dirname(os.path.abspath(__file__))
    ctfd_path = os.path.join(ctfd_dir, "CTFd")
    
    # Read config.ini
    config_path = os.path.join(ctfd_path, "config.ini")
    config_ini = configparser.ConfigParser()
    config_ini.read(config_path)
    
    # Get DATABASE_URL
    database_url = empty_str_cast(config_ini.get("server", "DATABASE_URL", fallback=""))
    
    if not database_url:
        # Check if we have individual database settings
        database_host = empty_str_cast(config_ini.get("server", "DATABASE_HOST", fallback=""))
        if database_host:
            # Construct URL from individual variables
            database_url = str(URL(
                drivername=empty_str_cast(config_ini.get("server", "DATABASE_PROTOCOL", fallback="")) or "mysql+pymysql",
                username=empty_str_cast(config_ini.get("server", "DATABASE_USER", fallback="")) or "ctfd",
                password=empty_str_cast(config_ini.get("server", "DATABASE_PASSWORD", fallback="")),
                host=database_host,
                port=empty_str_cast(config_ini.get("server", "DATABASE_PORT", fallback="")),
                database=empty_str_cast(config_ini.get("server", "DATABASE_NAME", fallback="")) or "ctfd",
            ))
        else:
            # Try Docker database first, fallback to SQLite
            print("No database config found, trying Docker MariaDB first...")
            return docker_database_url
    
    return database_url

def extract_ctfd_users():
    """Extract users from CTFd database"""
    try:
        # Get database URL
        database_url = get_ctfd_database_url()
        print(f"Connecting to database: {database_url}")
        
        # Create engine
        engine = create_engine(database_url)
        
        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Query users table
        print("\\nQuerying users table...")
        result = session.execute(text("""
            SELECT id, name, email, password, type, created, verified, banned, hidden
            FROM users 
            ORDER BY id
        """))
        
        users = result.fetchall()
        
        if not users:
            print("No users found in the database.")
            return []
        
        # Format data for display
        headers = ["ID", "Username", "Email", "Password Hash", "Type", "Created", "Verified", "Banned", "Hidden"]
        user_data = []
        
        for user in users:
            user_data.append([
                user[0],  # id
                user[1],  # name
                user[2],  # email
                user[3][:50] + "..." if user[3] and len(user[3]) > 50 else user[3],  # password (truncated)
                user[4],  # type
                user[5],  # created
                user[6],  # verified
                user[7],  # banned
                user[8],  # hidden
            ])
        
        print(f"\\nFound {len(users)} users:")
        print(tabulate(user_data, headers=headers, tablefmt="grid"))
        
        # Also query admins table if it exists
        try:
            print("\\nQuerying admins table...")
            result = session.execute(text("""
                SELECT id, name, email, password, type, created
                FROM admins
                ORDER BY id
            """))
            
            admins = result.fetchall()
            
            if admins:
                admin_headers = ["ID", "Username", "Email", "Password Hash", "Type", "Created"]
                admin_data = []
                
                for admin in admins:
                    admin_data.append([
                        admin[0],  # id
                        admin[1],  # name
                        admin[2],  # email
                        admin[3][:50] + "..." if admin[3] and len(admin[3]) > 50 else admin[3],  # password (truncated)
                        admin[4],  # type
                        admin[5],  # created
                    ])
                
                print(f"\\nFound {len(admins)} admins:")
                print(tabulate(admin_data, headers=admin_headers, tablefmt="grid"))
            else:
                print("No admins found in the database.")
                
        except Exception as e:
            print(f"Could not query admins table: {e}")
        
        session.close()
        return users
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return []

def extract_password_hashes():
    """Extract just usernames and password hashes"""
    try:
        # Get database URL
        database_url = get_ctfd_database_url()
        print(f"Connecting to database: {database_url}")
        
        # Create engine
        engine = create_engine(database_url)
        
        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Query for usernames and password hashes
        print("\\nExtracting usernames and password hashes...")
        result = session.execute(text("""
            SELECT name, password, email, type
            FROM users 
            WHERE password IS NOT NULL AND password != ''
            ORDER BY name
        """))
        
        users = result.fetchall()
        
        if not users:
            print("No users with passwords found in the database.")
            return []
        
        print(f"\\nFound {len(users)} users with passwords:")
        print("-" * 80)
        
        for user in users:
            username = user[0]
            password_hash = user[1]
            email = user[2]
            user_type = user[3]
            
            print(f"Username: {username}")
            print(f"Email: {email}")
            print(f"Type: {user_type}")
            print(f"Password Hash: {password_hash}")
            print("-" * 80)
        
        session.close()
        return users
        
    except Exception as e:
        print(f"Error extracting password hashes: {e}")
        return []

if __name__ == "__main__":
    print("CTFd User Database Extractor")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--hashes-only":
        extract_password_hashes()
    else:
        extract_ctfd_users()
        
        print("\\n" + "=" * 40)
        print("To see only usernames and password hashes, run:")
        print("python ctfd_user_extractor.py --hashes-only")
