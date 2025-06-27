#!/bin/bash

# This script sets up Azure resources for the financial forecasting pipeline

# Set variables
RESOURCE_GROUP="financial-forecasting-rg"
LOCATION="eastus"
STORAGE_ACCOUNT_NAME="financialforecastsa"
CONTAINER_NAME="forecast-predictions"
FILE_SHARE_NAME="forecast-pipeline-share"
ACR_NAME="financialforecastacr"
LOG_ANALYTICS_WORKSPACE="financial-forecast-logs"
CONTAINER_GROUP_NAME="financial-forecast-container"
IDENTITY_NAME="financial-forecast-identity"

# Login to Azure (uncomment if not already logged in)
# az login

# Create resource group
echo "Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create storage account
echo "Creating storage account..."
az storage account create \
  --name $STORAGE_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --enable-hierarchical-namespace false

# Get storage account key and connection string
STORAGE_ACCOUNT_KEY=$(az storage account keys list --resource-group $RESOURCE_GROUP --account-name $STORAGE_ACCOUNT_NAME --query "[0].value" -o tsv)
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string --resource-group $RESOURCE_GROUP --name $STORAGE_ACCOUNT_NAME --query connectionString -o tsv)

# Create container
echo "Creating blob container..."
az storage container create \
  --name $CONTAINER_NAME \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY \
  --public-access blob

# Create Azure Container Registry
echo "Creating Azure Container Registry..."
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

# Create Log Analytics workspace for monitoring
echo "Creating Log Analytics workspace..."
az monitor log-analytics workspace create \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $LOG_ANALYTICS_WORKSPACE

WORKSPACE_ID=$(az monitor log-analytics workspace show --resource-group $RESOURCE_GROUP --workspace-name $LOG_ANALYTICS_WORKSPACE --query customerId -o tsv)
WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys --resource-group $RESOURCE_GROUP --workspace-name $LOG_ANALYTICS_WORKSPACE --query primarySharedKey -o tsv)

# Create managed identity
echo "Creating managed identity..."
az identity create \
  --resource-group $RESOURCE_GROUP \
  --name $IDENTITY_NAME

# Get identity details
IDENTITY_ID=$(az identity show --resource-group $RESOURCE_GROUP --name $IDENTITY_NAME --query id -o tsv)
IDENTITY_PRINCIPAL=$(az identity show --resource-group $RESOURCE_GROUP --name $IDENTITY_NAME --query principalId -o tsv)

# Assign permissions to storage account
echo "Assigning permissions..."
STORAGE_ID=$(az storage account show --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP --query id -o tsv)
az role assignment create \
  --assignee-object-id $IDENTITY_PRINCIPAL \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope $STORAGE_ID

# Create Azure File Share
echo "Creating Azure File Share..."
az storage share create \
  --name $FILE_SHARE_NAME \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY \
  --quota 100

# Create directories in the file share
echo "Creating directory structure in File Share..."
az storage directory create \
  --share-name $FILE_SHARE_NAME \
  --name "scraping/scraped_data" \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY

az storage directory create \
  --share-name $FILE_SHARE_NAME \
  --name "modelling/predictions" \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY

az storage directory create \
  --share-name $FILE_SHARE_NAME \
  --name "modelling/cache" \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY

az storage directory create \
  --share-name $FILE_SHARE_NAME \
  --name "forecasting/data" \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY

# Display summary
echo ""
echo "======== Azure Resources Setup Complete ========"
echo "Resource Group:            $RESOURCE_GROUP"
echo "Location:                  $LOCATION"
echo "Storage Account:           $STORAGE_ACCOUNT_NAME"
echo "Blob Container:            $CONTAINER_NAME"
echo "File Share:                $FILE_SHARE_NAME"
echo "Container Registry:        $ACR_NAME"
echo "ACR Login Server:          $ACR_LOGIN_SERVER"
echo "Log Analytics Workspace:   $LOG_ANALYTICS_WORKSPACE"
echo "Managed Identity:          $IDENTITY_NAME"
echo ""
echo "Use the following values in your GitHub repository secrets:"
echo "AZURE_RESOURCE_GROUP:           $RESOURCE_GROUP"
echo "ACR_LOGIN_SERVER:               $ACR_LOGIN_SERVER"
echo "ACR_USERNAME:                   $ACR_USERNAME"
echo "ACR_PASSWORD:                   $ACR_PASSWORD"
echo "AZURE_STORAGE_CONNECTION_STRING:$STORAGE_CONNECTION_STRING"
echo ""
echo "You'll also need to add your FRED_API_KEY as a secret."
echo ""
echo "Direct Blob URL pattern for accessing predictions:"
echo "https://$STORAGE_ACCOUNT_NAME.blob.core.windows.net/$CONTAINER_NAME/next_friday_predictions_YYYYMMDD.json"
