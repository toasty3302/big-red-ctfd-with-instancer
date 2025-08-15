# Get all resource groups
$resourceGroups = az group list --query "[].name" --output tsv

foreach ($rg in $resourceGroups) {
    Write-Host "Processing Resource Group: $rg"

    # Get all container instances in the current resource group
    $containerInstances = az container list --resource-group $rg --query "[].name" --output tsv

    if ($containerInstances) {
        foreach ($ci in $containerInstances) {
            Write-Host "Deleting Container Instance: $ci in Resource Group: $rg"
            # Delete the container instance without confirmation
            az container delete --name $ci --resource-group $rg --yes
        }
    } else {
        Write-Host "No Container Instances found in Resource Group: $rg"
    }
}

Write-Host "Deletion process complete."