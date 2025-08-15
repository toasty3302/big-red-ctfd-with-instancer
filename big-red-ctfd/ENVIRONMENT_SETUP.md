# Environment Variables Setup

This project has been updated to use environment variables instead of hardcoded sensitive values for better security.

## Quick Setup

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the `.env` file** with your actual values:
   - Generate a secure 32-character hex password for CTFd: `python -c "import secrets; print(secrets.token_hex(16))"`
   - Add your Azure subscription ID, resource group, and region
   - Add your Azure Container Registry details
   - Optionally add Azure Service Principal credentials for automated authentication

## Required Environment Variables

### Database Configuration
- `CTFD_DB_PASSWORD` - Secure password for CTFd database (32-char hex recommended)
- `MARIADB_ROOT_PASSWORD` - MySQL root password (same as CTFD_DB_PASSWORD)
- `MARIADB_PASSWORD` - MySQL user password (same as CTFD_DB_PASSWORD)

### Azure Configuration
- `AZURE_SUBSCRIPTION_ID` - Your Azure subscription ID
- `AZURE_RESOURCE_GROUP` - Azure resource group name
- `AZURE_LOCATION` - Azure region (e.g., "East US 2")

### Azure Container Registry
- `ACR_SERVER` - Your ACR server URL (e.g., myregistry.azurecr.io)
- `ACR_NAME` - Your ACR name
- `ACR_USERNAME` - ACR username
- `ACR_PASSWORD` - ACR password

### Optional Azure Service Principal (for automation)
- `AZURE_CLIENT_ID` - Service principal client ID
- `AZURE_CLIENT_SECRET` - Service principal secret
- `AZURE_TENANT_ID` - Azure tenant ID

## ⚠️ IMPORTANT: Service Principal Required for Docker Deployment

When running the instancer in Docker containers (which is the default setup), Azure Service Principal credentials are **REQUIRED**, not optional. The containerized app cannot use interactive `az login`.

### Quick Service Principal Setup:
```bash
# Create service principal
az ad sp create-for-rbac --name "ctfd-instancer" --role contributor --scopes /subscriptions/YOUR_SUBSCRIPTION_ID

# Grant ACR access
az role assignment create --assignee YOUR_CLIENT_ID --role AcrPull --scope /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RG/providers/Microsoft.ContainerRegistry/registries/YOUR_ACR
```

See `AZURE_SERVICE_PRINCIPAL_SETUP.md` for detailed instructions.

## Security Notes

- The `.env` file is automatically ignored by git (added to `.gitignore`)
- Never commit sensitive values to version control
- Use strong, randomly generated passwords
- Rotate credentials regularly
- Consider using Azure Key Vault for production deployments

## Running the Application

After setting up your `.env` file:

```bash
docker compose up -d --build
```

The environment variables will be automatically loaded from the `.env` file.
