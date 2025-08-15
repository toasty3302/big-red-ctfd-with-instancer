# Azure Service Principal Setup Guide

The containerized instancer requires Azure Service Principal credentials to authenticate with Azure Container Registry and create container instances.

## 🔑 Creating a Service Principal

### Step 1: Create the Service Principal
```bash
az ad sp create-for-rbac --name "ctfd-instancer" --role contributor --scopes /subscriptions/8d921fbe-fb05-4594-ae9d-5c1edaa99006
```

This will output something like:
```json
{
  "appId": "12345678-1234-1234-1234-123456789012",
  "displayName": "ctfd-instancer",
  "password": "your-secret-here",
  "tenant": "87654321-4321-4321-4321-210987654321"
}
```

### Step 2: Grant ACR Access
```bash
# Give the service principal permission to pull from ACR
az role assignment create \
  --assignee 12345678-1234-1234-1234-123456789012 \
  --role AcrPull \
  --scope /subscriptions/8d921fbe-fb05-4594-ae9d-5c1edaa99006/resourceGroups/cornell/providers/Microsoft.ContainerRegistry/registries/cornellctfregistry2
```

### Step 3: Update .env File
Using the output from Step 1, update your `.env` file:

```properties
AZURE_CLIENT_ID=12345678-1234-1234-1234-123456789012
AZURE_CLIENT_SECRET=your-secret-here
AZURE_TENANT_ID=87654321-4321-4321-4321-210987654321
```

## 🛡️ Required Permissions

Your service principal needs:
- **Contributor** role on the subscription (to create container instances)
- **AcrPull** role on the container registry (to pull images)

## 🧪 Testing Authentication

After setting up the service principal, test it:
```bash
# Test login with service principal
az login --service-principal \
  --username 12345678-1234-1234-1234-123456789012 \
  --password your-secret-here \
  --tenant 87654321-4321-4321-4321-210987654321

# Test ACR access
az acr login --name cornellctfregistry2
```

## ⚠️ Security Notes

- Store the client secret securely
- Rotate credentials regularly
- Use least-privilege principle
- Never commit service principal credentials to source control
