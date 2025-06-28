#!/bin/bash

# This script sets up Azure resources for the financial forecasting pipeline

set -e  # Exit on any error

# Function to check if a provider is registered
check_provider() {
    local provider=$1
    local status=$(az provider show --namespace $provider --query "registrationState" -o tsv 2>/dev/null || echo "NotRegistered")
    echo $status
}

# Function to register a provider and wait for completion
register_provider() {
    local provider=$1
    echo "Checking registration status for $provider..."
    
    local status=$(check_provider $provider)
    if [ "$status" != "Registered" ]; then
        echo "Registering $provider..."
        az provider register --namespace $provider
        
        echo "Waiting for $provider registration to complete..."
        while [ "$(check_provider $provider)" != "Registered" ]; do
            echo "Still waiting for $provider registration..."
            sleep 30
        done
        echo "$provider is now registered!"
    else
        echo "$provider is already registered."
    fi
}

# Generate a unique storage account name using timestamp (must be lowercase and globally unique)
TIMESTAMP=$(date +%s)
RANDOM_SUFFIX=$(echo $TIMESTAMP | tail -c 7)

# Set variables
RESOURCE_GROUP="financial-forecasting-rg"
LOCATION="eastus"
STORAGE_ACCOUNT_NAME="forecastsa${RANDOM_SUFFIX}"  # Shorter name, lowercase
CONTAINER_NAME="forecast-predictions"
FILE_SHARE_NAME="forecast-pipeline-share"
ACR_NAME="forecastacr${RANDOM_SUFFIX}"  # Shorter name
LOG_ANALYTICS_WORKSPACE="financial-forecast-logs"
CONTAINER_GROUP_NAME="financial-forecast-container"
IDENTITY_NAME="financial-forecast-identity"

echo "Using storage account name: $STORAGE_ACCOUNT_NAME"
echo "Using ACR name: $ACR_NAME"

# Login to Azure (uncomment if not already logged in)
# az login

# Register required Azure providers
echo "Registering required Azure providers..."
register_provider "Microsoft.Storage"
register_provider "Microsoft.ContainerRegistry"
register_provider "Microsoft.ContainerInstance"
register_provider "Microsoft.OperationalInsights"
register_provider "Microsoft.ManagedIdentity"

# Create resource group
echo "Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create storage account
echo "Creating storage account: $STORAGE_ACCOUNT_NAME..."
az storage account create \
  --name $STORAGE_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --enable-hierarchical-namespace false

# Wait for storage account to be ready
echo "Waiting for storage account to be fully provisioned..."
sleep 30

# Get storage account key and connection string
echo "Retrieving storage account credentials..."
STORAGE_ACCOUNT_KEY=$(az storage account keys list --resource-group $RESOURCE_GROUP --account-name $STORAGE_ACCOUNT_NAME --query "[0].value" -o tsv)
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string --resource-group $RESOURCE_GROUP --name $STORAGE_ACCOUNT_NAME --query connectionString -o tsv)

if [ -z "$STORAGE_ACCOUNT_KEY" ]; then
    echo "ERROR: Failed to retrieve storage account key"
    exit 1
fi

# Create container
echo "Creating blob container..."
az storage container create \
  --name $CONTAINER_NAME \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key "$STORAGE_ACCOUNT_KEY" \
  --public-access blob

# Create Azure Container Registry
echo "Creating Azure Container Registry: $ACR_NAME..."
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true \
  --location $LOCATION

# Wait for ACR to be ready
echo "Waiting for ACR to be fully provisioned..."
sleep 30

# Get ACR credentials
echo "Retrieving ACR credentials..."
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

if [ -z "$ACR_USERNAME" ] || [ -z "$ACR_PASSWORD" ]; then
    echo "ERROR: Failed to retrieve ACR credentials"
    exit 1
fi

# Create Log Analytics workspace for monitoring
echo "Creating Log Analytics workspace..."
az monitor log-analytics workspace create \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $LOG_ANALYTICS_WORKSPACE \
  --location $LOCATION

# Wait for workspace to be ready
echo "Waiting for Log Analytics workspace to be ready..."
sleep 30

WORKSPACE_ID=$(az monitor log-analytics workspace show --resource-group $RESOURCE_GROUP --workspace-name $LOG_ANALYTICS_WORKSPACE --query customerId -o tsv)
WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys --resource-group $RESOURCE_GROUP --workspace-name $LOG_ANALYTICS_WORKSPACE --query primarySharedKey -o tsv)

# Create managed identity
echo "Creating managed identity..."
az identity create \
  --resource-group $RESOURCE_GROUP \
  --name $IDENTITY_NAME \
  --location $LOCATION

# Wait for identity to be ready
echo "Waiting for managed identity to be ready..."
sleep 30

# Get identity details
IDENTITY_ID=$(az identity show --resource-group $RESOURCE_GROUP --name $IDENTITY_NAME --query id -o tsv)
IDENTITY_PRINCIPAL=$(az identity show --resource-group $RESOURCE_GROUP --name $IDENTITY_NAME --query principalId -o tsv)

if [ -z "$IDENTITY_PRINCIPAL" ]; then
    echo "ERROR: Failed to retrieve managed identity principal ID"
    exit 1
fi

# Assign permissions to storage account
echo "Assigning permissions..."
STORAGE_ID=$(az storage account show --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP --query id -o tsv)

if [ -n "$STORAGE_ID" ] && [ -n "$IDENTITY_PRINCIPAL" ]; then
    az role assignment create \
      --assignee-object-id $IDENTITY_PRINCIPAL \
      --assignee-principal-type ServicePrincipal \
      --role "Storage Blob Data Contributor" \
      --scope $STORAGE_ID
    
    echo "Storage permissions assigned successfully."
else
    echo "WARNING: Could not assign storage permissions - missing storage ID or identity principal"
fi

# Create Azure File Share
echo "Creating Azure File Share..."
az storage share create \
  --name $FILE_SHARE_NAME \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key "$STORAGE_ACCOUNT_KEY" \
  --quota 100

# Create directories in the file share
echo "Creating directory structure in File Share..."

# Check if file share was created successfully before creating directories
if az storage share exists --name $FILE_SHARE_NAME --account-name $STORAGE_ACCOUNT_NAME --account-key "$STORAGE_ACCOUNT_KEY" --query exists -o tsv | grep -q "true"; then
    echo "File share created successfully. Creating directories..."
    
    # Create parent directories first
    az storage directory create \
      --share-name $FILE_SHARE_NAME \
      --name "scraping" \
      --account-name $STORAGE_ACCOUNT_NAME \
      --account-key "$STORAGE_ACCOUNT_KEY"
    
    az storage directory create \
      --share-name $FILE_SHARE_NAME \
      --name "scraping/scraped_data" \
      --account-name $STORAGE_ACCOUNT_NAME \
      --account-key "$STORAGE_ACCOUNT_KEY"

    az storage directory create \
      --share-name $FILE_SHARE_NAME \
      --name "modelling" \
      --account-name $STORAGE_ACCOUNT_NAME \
      --account-key "$STORAGE_ACCOUNT_KEY"

    az storage directory create \
      --share-name $FILE_SHARE_NAME \
      --name "modelling/predictions" \
      --account-name $STORAGE_ACCOUNT_NAME \
      --account-key "$STORAGE_ACCOUNT_KEY"

    az storage directory create \
      --share-name $FILE_SHARE_NAME \
      --name "modelling/cache" \
      --account-name $STORAGE_ACCOUNT_NAME \
      --account-key "$STORAGE_ACCOUNT_KEY"

    az storage directory create \
      --share-name $FILE_SHARE_NAME \
      --name "forecasting" \
      --account-name $STORAGE_ACCOUNT_NAME \
      --account-key "$STORAGE_ACCOUNT_KEY"

    az storage directory create \
      --share-name $FILE_SHARE_NAME \
      --name "forecasting/data" \
      --account-name $STORAGE_ACCOUNT_NAME \
      --account-key "$STORAGE_ACCOUNT_KEY"
    
    echo "Directory structure created successfully."
else
    echo "WARNING: File share creation may have failed. Skipping directory creation."
fi

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
