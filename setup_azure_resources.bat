@echo off
REM This script sets up Azure resources for the financial forecasting pipeline

REM Set variables
set RESOURCE_GROUP=financial-forecasting-rg
set LOCATION=eastus
set STORAGE_ACCOUNT_NAME=financialforecastsa
set CONTAINER_NAME=forecast-predictions
set FILE_SHARE_NAME=forecast-pipeline-share
set ACR_NAME=financialforecastacr
set LOG_ANALYTICS_WORKSPACE=financial-forecast-logs
set CONTAINER_GROUP_NAME=financial-forecast-container
set IDENTITY_NAME=financial-forecast-identity

REM Login to Azure (uncomment if not already logged in)
REM az login

REM Create resource group
echo Creating resource group...
az group create --name %RESOURCE_GROUP% --location %LOCATION%

REM Create storage account
echo Creating storage account...
az storage account create ^
  --name %STORAGE_ACCOUNT_NAME% ^
  --resource-group %RESOURCE_GROUP% ^
  --location %LOCATION% ^
  --sku Standard_LRS ^
  --kind StorageV2 ^
  --enable-hierarchical-namespace false

REM Get storage account key and connection string
FOR /F "tokens=*" %%g IN ('az storage account keys list --resource-group %RESOURCE_GROUP% --account-name %STORAGE_ACCOUNT_NAME% --query "[0].value" -o tsv') do (SET STORAGE_ACCOUNT_KEY=%%g)
FOR /F "tokens=*" %%g IN ('az storage account show-connection-string --resource-group %RESOURCE_GROUP% --name %STORAGE_ACCOUNT_NAME% --query connectionString -o tsv') do (SET STORAGE_CONNECTION_STRING=%%g)

REM Create container
echo Creating blob container...
az storage container create ^
  --name %CONTAINER_NAME% ^
  --account-name %STORAGE_ACCOUNT_NAME% ^
  --account-key %STORAGE_ACCOUNT_KEY% ^
  --public-access blob

REM Create Azure Container Registry
echo Creating Azure Container Registry...
az acr create ^
  --resource-group %RESOURCE_GROUP% ^
  --name %ACR_NAME% ^
  --sku Basic ^
  --admin-enabled true

REM Get ACR credentials
FOR /F "tokens=*" %%g IN ('az acr credential show --name %ACR_NAME% --query username -o tsv') do (SET ACR_USERNAME=%%g)
FOR /F "tokens=*" %%g IN ('az acr credential show --name %ACR_NAME% --query "passwords[0].value" -o tsv') do (SET ACR_PASSWORD=%%g)
FOR /F "tokens=*" %%g IN ('az acr show --name %ACR_NAME% --query loginServer -o tsv') do (SET ACR_LOGIN_SERVER=%%g)

REM Create Log Analytics workspace for monitoring
echo Creating Log Analytics workspace...
az monitor log-analytics workspace create ^
  --resource-group %RESOURCE_GROUP% ^
  --workspace-name %LOG_ANALYTICS_WORKSPACE%

FOR /F "tokens=*" %%g IN ('az monitor log-analytics workspace show --resource-group %RESOURCE_GROUP% --workspace-name %LOG_ANALYTICS_WORKSPACE% --query customerId -o tsv') do (SET WORKSPACE_ID=%%g)
FOR /F "tokens=*" %%g IN ('az monitor log-analytics workspace get-shared-keys --resource-group %RESOURCE_GROUP% --workspace-name %LOG_ANALYTICS_WORKSPACE% --query primarySharedKey -o tsv') do (SET WORKSPACE_KEY=%%g)

REM Create managed identity
echo Creating managed identity...
az identity create ^
  --resource-group %RESOURCE_GROUP% ^
  --name %IDENTITY_NAME%

REM Get identity details
FOR /F "tokens=*" %%g IN ('az identity show --resource-group %RESOURCE_GROUP% --name %IDENTITY_NAME% --query id -o tsv') do (SET IDENTITY_ID=%%g)
FOR /F "tokens=*" %%g IN ('az identity show --resource-group %RESOURCE_GROUP% --name %IDENTITY_NAME% --query principalId -o tsv') do (SET IDENTITY_PRINCIPAL=%%g)

REM Assign permissions to storage account
echo Assigning permissions...
FOR /F "tokens=*" %%g IN ('az storage account show --name %STORAGE_ACCOUNT_NAME% --resource-group %RESOURCE_GROUP% --query id -o tsv') do (SET STORAGE_ID=%%g)
az role assignment create ^
  --assignee-object-id %IDENTITY_PRINCIPAL% ^
  --assignee-principal-type ServicePrincipal ^
  --role "Storage Blob Data Contributor" ^
  --scope %STORAGE_ID%

REM Create Azure File Share
echo Creating Azure File Share...
az storage share create ^
  --name %FILE_SHARE_NAME% ^
  --account-name %STORAGE_ACCOUNT_NAME% ^
  --account-key %STORAGE_ACCOUNT_KEY% ^
  --quota 100

REM Create directories in the file share
echo Creating directory structure in File Share...
az storage directory create ^
  --share-name %FILE_SHARE_NAME% ^
  --name "scraping/scraped_data" ^
  --account-name %STORAGE_ACCOUNT_NAME% ^
  --account-key %STORAGE_ACCOUNT_KEY%

az storage directory create ^
  --share-name %FILE_SHARE_NAME% ^
  --name "modelling/predictions" ^
  --account-name %STORAGE_ACCOUNT_NAME% ^
  --account-key %STORAGE_ACCOUNT_KEY%

az storage directory create ^
  --share-name %FILE_SHARE_NAME% ^
  --name "modelling/cache" ^
  --account-name %STORAGE_ACCOUNT_NAME% ^
  --account-key %STORAGE_ACCOUNT_KEY%

az storage directory create ^
  --share-name %FILE_SHARE_NAME% ^
  --name "forecasting/data" ^
  --account-name %STORAGE_ACCOUNT_NAME% ^
  --account-key %STORAGE_ACCOUNT_KEY%

REM Display summary
echo.
echo ======== Azure Resources Setup Complete ========
echo Resource Group:            %RESOURCE_GROUP%
echo Location:                  %LOCATION%
echo Storage Account:           %STORAGE_ACCOUNT_NAME%
echo Blob Container:            %CONTAINER_NAME%
echo File Share:                %FILE_SHARE_NAME%
echo Container Registry:        %ACR_NAME%
echo ACR Login Server:          %ACR_LOGIN_SERVER%
echo Log Analytics Workspace:   %LOG_ANALYTICS_WORKSPACE%
echo Managed Identity:          %IDENTITY_NAME%
echo.
echo Use the following values in your GitHub repository secrets:
echo AZURE_RESOURCE_GROUP:            %RESOURCE_GROUP%
echo ACR_LOGIN_SERVER:                %ACR_LOGIN_SERVER%
echo ACR_USERNAME:                    %ACR_USERNAME%
echo ACR_PASSWORD:                    %ACR_PASSWORD%
echo AZURE_STORAGE_CONNECTION_STRING: %STORAGE_CONNECTION_STRING%
echo.
echo You'll also need to add your FRED_API_KEY as a secret.
echo.
echo Direct Blob URL pattern for accessing predictions:
echo https://%STORAGE_ACCOUNT_NAME%.blob.core.windows.net/%CONTAINER_NAME%/next_friday_predictions_YYYYMMDD.json
