#!/usr/bin/env pwsh
# Script to push Docker images to Azure Container Registry

Write-Host "🚀 Azure Container Registry Image Push Script" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# Load environment variables from .env file if it exists
if (Test-Path ".env") {
    Get-Content ".env" | Where-Object { $_ -notmatch "^#" -and $_ -match "=" } | ForEach-Object {
        $varName, $varValue = $_ -split "=", 2
        Set-Variable -Name $varName -Value $varValue
    }
}

# Use environment variables or defaults
$acrName = if ($env:ACR_NAME) { $env:ACR_NAME } else { $ACR_NAME }
$acrServer = if ($env:ACR_SERVER) { $env:ACR_SERVER } else { $ACR_SERVER }

if (-not $acrName -or -not $acrServer) {
    Write-Host "❌ ACR_NAME and ACR_SERVER must be set in environment variables or .env file" -ForegroundColor Red
    exit 1
}

# Step 1: Login to ACR
Write-Host "`n🔐 Logging into Azure Container Registry..." -ForegroundColor Yellow
az acr login --name $acrName

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to login to ACR. Make sure you're logged into Azure." -ForegroundColor Red
    exit 1
}

# Step 2: Pull your existing image from Docker Hub
Write-Host "`n📥 Pulling toasty3302/eaas from Docker Hub..." -ForegroundColor Yellow
docker pull toasty3302/eaas:latest

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to pull image from Docker Hub." -ForegroundColor Red
    exit 1
}

# Step 3: Tag the image for ACR
Write-Host "`n🏷️  Tagging image for ACR..." -ForegroundColor Yellow
docker tag toasty3302/eaas:latest "$acrServer/eaas:latest"

# Step 4: Push to ACR
Write-Host "`n📤 Pushing image to ACR..." -ForegroundColor Yellow
docker push "$acrServer/eaas:latest"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Successfully pushed image to ACR!" -ForegroundColor Green
    Write-Host "   Image URL: $acrServer/eaas:latest" -ForegroundColor Cyan
    
    # Step 5: Get ACR credentials for the Python script
    Write-Host "`n🔑 Getting ACR credentials..." -ForegroundColor Yellow
    $credentials = az acr credential show --name $acrName | ConvertFrom-Json
    
    Write-Host "`n📋 Update your Python script with these credentials:" -ForegroundColor Cyan
    Write-Host "   Server: $acrServer" -ForegroundColor White
    Write-Host "   Username: $($credentials.username)" -ForegroundColor White
    Write-Host "   Password: $($credentials.passwords[0].value)" -ForegroundColor White
    
    Write-Host "`n💡 Replace 'REPLACE_WITH_ACR_PASSWORD' in simple_azure_test.py with:" -ForegroundColor Yellow
    Write-Host "   $($credentials.passwords[0].value)" -ForegroundColor White
} else {
    Write-Host "`n❌ Failed to push image to ACR." -ForegroundColor Red
}

Write-Host "`n🎉 Script completed!" -ForegroundColor Green
