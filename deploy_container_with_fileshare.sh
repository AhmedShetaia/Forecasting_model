#!/bin/bash

# Script to deploy a container instance with Azure File Share mount

# Set variables (replace with your actual values or use parameters)
RESOURCE_GROUP="financial-forecasting-rg"
CONTAINER_GROUP_NAME="financial-forecasting-container"
IMAGE_NAME="financialforecastacr.azurecr.io/financial-forecasting:latest"
STORAGE_ACCOUNT_NAME="financialforecastsa"
FILE_SHARE_NAME="forecast-pipeline-share"
ACR_NAME="financialforecastacr"
LOCATION="eastus"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --resource-group)
      RESOURCE_GROUP="$2"
      shift
      shift
      ;;
    --container-name)
      CONTAINER_GROUP_NAME="$2"
      shift
      shift
      ;;
    --image)
      IMAGE_NAME="$2"
      shift
      shift
      ;;
    --storage-account)
      STORAGE_ACCOUNT_NAME="$2"
      shift
      shift
      ;;
    --file-share)
      FILE_SHARE_NAME="$2"
      shift
      shift
      ;;
    --acr-name)
      ACR_NAME="$2"
      shift
      shift
      ;;
    --location)
      LOCATION="$2"
      shift
      shift
      ;;
    *)
      shift
      ;;
  esac
done

# Get ACR credentials
echo "Getting ACR credentials..."
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

# Get storage account key
echo "Getting storage account key..."
STORAGE_ACCOUNT_KEY=$(az storage account keys list --resource-group $RESOURCE_GROUP --account-name $STORAGE_ACCOUNT_NAME --query "[0].value" -o tsv)

# Get storage connection string
echo "Getting storage connection string..."
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string --resource-group $RESOURCE_GROUP --name $STORAGE_ACCOUNT_NAME --query connectionString -o tsv)

# Check if file share exists, create if not
echo "Checking file share existence..."
SHARE_EXISTS=$(az storage share exists --name $FILE_SHARE_NAME --account-name $STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --query exists -o tsv)

if [ "$SHARE_EXISTS" != "true" ]; then
  echo "Creating file share $FILE_SHARE_NAME..."
  az storage share create --name $FILE_SHARE_NAME --account-name $STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY
  
  # Create directory structure
  echo "Creating directory structure in file share..."
  az storage directory create --share-name $FILE_SHARE_NAME --name "scraping/scraped_data" --account-name $STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY
  az storage directory create --share-name $FILE_SHARE_NAME --name "modelling/predictions" --account-name $STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY
  az storage directory create --share-name $FILE_SHARE_NAME --name "modelling/cache" --account-name $STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY
  az storage directory create --share-name $FILE_SHARE_NAME --name "forecasting/data" --account-name $STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY
fi

# Deploy container with file share mount
echo "Deploying container instance with file share mount..."
az container create \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_GROUP_NAME \
  --image $IMAGE_NAME \
  --registry-login-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --environment-variables AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONNECTION_STRING \
  --azure-file-volume-account-name $STORAGE_ACCOUNT_NAME \
  --azure-file-volume-account-key $STORAGE_ACCOUNT_KEY \
  --azure-file-volume-share-name $FILE_SHARE_NAME \
  --azure-file-volume-mount-path /app \
  --cpu 2 \
  --memory 8 \
  --restart-policy Never \
  --location $LOCATION

echo "Container deployment complete!"
