# Azure File Share Integration

This documentation explains how to use Azure File Share with the financial forecasting pipeline for persistent data storage across container runs.

## Overview

The pipeline has been updated to use Azure File Share mounted at `/app` within the container, ensuring that the following directories persist between runs:

- `/app/scraping/scraped_data` - Historical market and company data
- `/app/modelling/predictions` - Generated model predictions
- `/app/modelling/cache` - Model cache files for faster retraining
- `/app/forecasting/data` - Combined data and final forecasts

## Setup

Azure File Share is automatically created during the resource setup process using either:
- `setup_azure_resources.sh` (Linux/macOS)
- `setup_azure_resources.bat` (Windows)

## How Data Persistence Works

The Azure File Share is mounted directly at the `/app` path within the container. This means all file operations are transparently redirected to the file share. Your code does not need to change as all file paths remain the same.

### Benefits

1. **Data Preservation**: All data persists between container runs
2. **No Code Changes**: File paths remain the same (e.g., `./scraping/scraped_data/file.csv`)
3. **Performance**: Local file operations are faster than API calls to blob storage
4. **Simplicity**: No need to download/upload files between runs

## Accessing Files Manually

### Azure Portal

1. Navigate to your storage account in the Azure Portal
2. Select "File shares" from the left navigation
3. Choose the "forecast-pipeline-share" file share
4. Browse or upload files through the interface

### Azure Storage Explorer

1. Install [Azure Storage Explorer](https://azure.microsoft.com/en-us/features/storage-explorer/)
2. Connect to your Azure account
3. Navigate to the "forecast-pipeline-share" file share
4. Download, upload, or modify files directly

### Programmatic Access

You can access files programmatically using the Azure Files SDK:

```python
from azure.storage.fileshare import ShareServiceClient

# Connect to the file share service
connection_string = "YOUR_CONNECTION_STRING"
share_service_client = ShareServiceClient.from_connection_string(connection_string)
share_client = share_service_client.get_share_client("forecast-pipeline-share")

# Download a file
file_client = share_client.get_file_client("modelling/predictions/latest_predictions.csv")
with open("./downloaded_predictions.csv", "wb") as file_handle:
    data = file_client.download_file()
    data.readinto(file_handle)

# Upload a file
with open("./new_data.csv", "rb") as source_file:
    file_client = share_client.get_file_client("forecasting/data/new_data.csv")
    file_client.upload_file(source_file)
```

## Deployment

### Using GitHub Actions

The GitHub Actions workflow (`deploy-pipeline.yml`) has been updated to automatically mount the file share during deployment.

### Manual Deployment

To deploy the container with the file share mount:

```bash
# Linux/macOS
./deploy_container_with_fileshare.sh

# Windows
deploy_container_with_fileshare.bat
```

## Bicep Templates

For infrastructure-as-code deployments, Bicep templates are provided:

- `infrastructure/main.bicep` - Main resource template
- `infrastructure/containerInstance.bicep` - Container instance with file share mount

Deploy using:

```bash
# First, deploy the main infrastructure
az deployment group create --resource-group financial-forecasting-rg --template-file infrastructure/main.bicep

# Then deploy the container instance
az deployment group create \
  --resource-group financial-forecasting-rg \
  --template-file infrastructure/containerInstance.bicep \
  --parameters \
    containerGroupName=financial-forecasting-container \
    containerImage=financialforecastacr.azurecr.io/financial-forecasting:latest \
    registryServer=financialforecastacr.azurecr.io \
    registryUsername=<username> \
    registryPassword=<password> \
    storageAccountName=financialforecastsa \
    storageAccountKey=<key> \
    fileShareName=forecast-pipeline-share \
    storageConnectionString=<connection-string>
```

## Important Notes

1. The blob upload functionality still works for final results - Azure File Share is only used for internal data persistence.
2. Container runs remain short-lived (`--restart-policy Never`) as requested.
3. The file share is mounted as writable, allowing the container to modify files.
4. Container image is still pushed to ACR and deployed from there.
