#!/usr/bin/env python3
"""
Test CTFd Authentication in Instancer App
This script tests the login functionality of the instancer app with CTFd credentials
"""

import requests
import time

def test_instancer_login():
    """Test login to the instancer app using CTFd credentials"""
    base_url = "http://localhost:5000"
    
    # Test credentials
    username = "toasty"
    password = "Dcba!2345"
    
    print("🧪 Testing Instancer App CTFd Authentication")
    print("=" * 50)
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    try:
        # First, get the login page to check if app is running
        print("📡 Connecting to instancer app...")
        response = session.get(f"{base_url}/login")
        
        if response.status_code != 200:
            print(f"❌ Cannot access login page. Status: {response.status_code}")
            return False
        
        print("✅ Login page accessible")
        
        # Attempt login with CTFd credentials
        print(f"🔐 Attempting login with username: {username}")
        
        login_data = {
            'username': username,
            'password': password
        }
        
        response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
        
        if response.status_code == 302:  # Redirect indicates successful login
            print("✅ Login successful! (Received redirect)")
            
            # Follow the redirect to the dashboard
            dashboard_response = session.get(f"{base_url}/")
            
            if dashboard_response.status_code == 200:
                if "Available Challenges" in dashboard_response.text:
                    print("✅ Dashboard accessible - CTFd authentication working!")
                    print("🎉 SUCCESS: Instancer app can authenticate against CTFd!")
                    return True
                else:
                    print("⚠️  Dashboard loaded but content unexpected")
            else:
                print(f"❌ Cannot access dashboard. Status: {dashboard_response.status_code}")
        
        elif response.status_code == 200:
            # Login failed, stayed on login page
            if "Invalid credentials" in response.text:
                print("❌ Login failed: Invalid credentials")
            else:
                print("❌ Login failed: Unknown reason")
        
        else:
            print(f"❌ Unexpected response status: {response.status_code}")
        
        return False
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to instancer app. Is it running on port 5000?")
        return False
    except Exception as e:
        print(f"❌ Error testing login: {e}")
        return False

if __name__ == "__main__":
    # Wait a moment for the app to fully start
    print("⏳ Waiting for app to start...")
    time.sleep(2)
    
    success = test_instancer_login()
    
    if success:
        print("\n✅ All tests passed!")
        print("You can now:")
        print("1. Visit http://localhost:5000")
        print("2. Login with:")
        print("   Username: toasty")
        print("   Password: Dcba!2345")
        print("3. Create challenge instances!")
    else:
        print("\n❌ Tests failed. Check the instancer app logs.")
