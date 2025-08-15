# Cornell CTF Challenge Instancer

A web application that integrates with CTFd for authentication and creates Azure Container Instances for CTF challenges.

> **Note**: This application now connects directly to the CTFd database for user authentication, allowing users to login with their existing CTFd credentials.

## Features

🔐 **CTFd Authentication**: Direct integration with CTFd database for seamless user login  
🎯 **Challenge Management**: Multiple challenge categories (Web, Crypto, Pwn, Forensics)  
☁️ **Azure Integration**: Automatic container provisioning on Azure Container Instances  
🌐 **Custom URLs**: Unique FQDN generation using UUIDs and hex suffixes  
⏰ **Auto-Expiry**: Instances automatically expire after 4 hours  
📊 **Instance Tracking**: Real-time status monitoring and management  
🔒 **Password Compatibility**: Uses CTFd's bcrypt-sha256 hashing for existing user passwords  

## Architecture

### URL Format
```
http://cornell-{challenge_id}-{user_uuid}-{16_hex_chars}.eastus2.azurecontainer.io:{port}/
```

Example:
```
http://cornell-eaas-demo-a1b2c3d4-e5f6-7890-abcd-ef1234567890-a1b2c3d4e5f67890.eastus2.azurecontainer.io:1337/
```

### Components

- **Flask Web App**: User interface and API endpoints
- **SQLite Database**: User and instance tracking
- **Azure Container Instances**: Challenge hosting
- **Azure Container Registry**: Private image storage

## Quick Start

The easiest way to start the instancer is using the automated launcher:

### Windows Users
```bash
# Double-click this file or run in command prompt
start_instancer.bat
```

### All Platforms
```bash
python start_instancer.py
```

The launcher will automatically:
1. ✅ Check if Azure CLI is installed
2. 🔐 Login to Azure if not already authenticated
3. 📋 Set the correct subscription (8d921fbe-fb05-4594-ae9d-5c1edaa99006)
4. 🔍 Verify Azure access
5. 🚀 Start the Flask application on http://localhost:5000

### Prerequisites

1. **Azure CLI** installed and configured
2. **Python 3.8+** with pip
3. **Azure subscription** with Container Instance permissions
4. **Azure Container Registry** (cornellctfregistry2.azurecr.io)
5. **CTFd Database Access** (MariaDB/MySQL container running)

### Installation

1. **Clone and navigate to the instancer directory:**
   ```bash
   cd c:\Users\billn\Downloads\big-red-ctfd\instancer
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup Azure authentication:**
   ```bash
   python setup_azure.py
   ```
   Or manually:
   ```bash
   az login
   az account set --subscription 8d921fbe-fb05-4594-ae9d-5c1edaa99006
   ```

4. **Verify CTFd database connection:**
   ```bash
   python test_password_verification.py
   ```

5. **Run setup script:**
5. **Run setup script:**
   ```bash
   python setup.py
   ```

6. **Start the application with automatic Azure login:**
   ```bash
   python start_instancer.py
   ```
   
   Or on Windows, double-click:
   ```
   start_instancer.bat
   ```

   **Alternative (manual):**
   ```bash
   az login
   az account set --subscription 8d921fbe-fb05-4594-ae9d-5c1edaa99006
   python app.py
   ```

7. **Access the application:**
   ```
   http://localhost:5000
   ```

## CTFd Integration

### Authentication
Users login with their existing CTFd credentials:
- **Username**: CTFd username (e.g., `toasty`)
- **Password**: CTFd password (e.g., `Dcba!2345`)

The application connects directly to the CTFd MariaDB database and uses the same password hashing algorithm (`bcrypt-sha256`) to verify credentials.

### Database Configuration
The app expects CTFd database to be accessible at:
```
Host: localhost
Port: 3306
Database: ctfd
Username: ctfd
Password: ctfd
```

### Challenge Instance Tracking
A new table `challenge_instances` is created in the CTFd database to track user instances:

```sql
CREATE TABLE challenge_instances (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    challenge_id VARCHAR(255) NOT NULL,
    container_name VARCHAR(255) UNIQUE NOT NULL,
    fqdn VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'creating',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## Configuration

### Azure Settings

Update `AZURE_CONFIG` in `app.py`:

```python
AZURE_CONFIG = {
    'subscription_id': 'your-subscription-id',
    'resource_group': 'your-resource-group',
    'location': 'East US 2',
    'acr_server': 'your-registry.azurecr.io',
    'acr_username': 'your-registry-username',
    'acr_password': 'your-registry-password'
}
```

### Challenge Definitions

Add new challenges in the `CHALLENGES` dictionary:

```python
'new-challenge': {
    'name': 'New Challenge Name',
    'description': 'Challenge description',
    'image': 'cornellctfregistry2.azurecr.io/new-challenge:latest',
    'port': 8080,
    'category': 'Web'
}
```

## Usage

### For CTFd Users

1. **Login**: Use your existing CTFd username and password
2. **Browse Challenges**: View available challenges by category
3. **Create Instance**: Click "Make Instance" for any challenge
4. **Access Challenge**: Use the provided URL to access your instance
5. **Manage Instances**: Delete instances when done

### For Administrators

1. **Add Challenges**: Update the `CHALLENGES` dictionary
2. **Push Images**: Upload challenge containers to ACR
3. **Monitor Usage**: Check database for instance statistics
4. **Manage Costs**: Instances auto-expire after 4 hours

## Database Schema

### CTFd Users Table (Existing)
Connected to existing CTFd `users` table for authentication.

### Challenge Instances Table (New)
```sql
CREATE TABLE challenge_instances (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    challenge_id VARCHAR(255) NOT NULL,
    container_name VARCHAR(255) UNIQUE NOT NULL,
    fqdn VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'creating',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## API Endpoints

- `GET /` - Dashboard (requires authentication)
- `GET /login` - Login page
- `POST /login` - Authenticate user
- `GET /register` - Registration page
- `POST /register` - Create new user
- `POST /create_instance` - Create challenge instance
- `POST /delete_instance` - Delete challenge instance
- `GET /logout` - Logout user

## Security Features

- **Password Hashing**: Uses Werkzeug's secure password hashing
- **Session Management**: Flask sessions with secure secret key
- **UUID Isolation**: Each user gets unique identifiers
- **Resource Isolation**: Separate containers per user per challenge
- **Auto-Cleanup**: Prevents resource accumulation

## Troubleshooting

### Common Issues

**Azure Authentication Error:**
```bash
python setup_azure.py
# Or manually:
az login
az account set --subscription 8d921fbe-fb05-4594-ae9d-5c1edaa99006
python check_azure_auth.py
```

**CTFd Database Connection Error:**
```bash
# Check if CTFd database container is running
docker ps | grep big-red-ctfd-db-1

# Test database connection
docker exec -it big-red-ctfd-db-1 mysql -u ctfd -pctfd ctfd -e "SELECT id, name FROM users LIMIT 5;"

# Test password verification
python test_password_verification.py
```

**Container Creation Fails:**
- Check Azure quotas and permissions
- Verify ACR credentials
- Ensure resource group exists

**Login Issues:**
- Verify CTFd username and password are correct
- Check that passlib==1.7.4 and bcrypt==4.0.1 are installed
- Ensure CTFd database is accessible

### Logs and Debugging

Enable Flask debug mode:
```python
app.run(debug=True)
```

Check Azure Container Instance logs:
```bash
az container logs --resource-group cornell --name container-name
```

## Cost Management

### Estimated Costs (per instance)
- **Container Instance**: ~$1.30/hour (0.25 vCPU, 0.5GB RAM)
- **ACR Storage**: ~$0.10/GB/month
- **Bandwidth**: ~$0.087/GB

### Optimization Tips
- Set appropriate auto-expiry times
- Use smaller container resources when possible
- Monitor and clean up unused instances
- Consider scheduled cleanup jobs

## Development

### Adding New Features

1. **New Challenge Types**: Update `CHALLENGES` dictionary
2. **Custom Expiry**: Modify `create_challenge_instance()`
3. **User Roles**: Extend user model and authentication
4. **Instance Monitoring**: Add health check endpoints

### Testing

```bash
# Test Azure authentication
python check_azure_auth.py

# Test CTFd password verification
python test_password_verification.py

# Test with CTFd user credentials
# Username: toasty
# Password: Dcba!2345

# Test challenge creation
curl -X POST http://localhost:5000/create_instance \
  -d "challenge_id=eaas-demo" \
  --cookie "session=your-session-cookie"
```

## License

MIT License - See LICENSE file for details

## Support

For issues and support:
- Create GitHub issues for bugs
- Check Azure documentation for infrastructure issues
- Review Flask documentation for web app issues
