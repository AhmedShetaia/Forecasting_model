@echo off
REM Script to deploy a container instance with Azure File Share mount

REM Set default variables
set RESOURCE_GROUP=financial-forecasting-rg
set CONTAINER_GROUP_NAME=financial-forecasting-container
set IMAGE_NAME=financialforecastacr.azurecr.io/financial-forecasting:latest
set STORAGE_ACCOUNT_NAME=financialforecastsa
set FILE_SHARE_NAME=forecast-pipeline-share
set ACR_NAME=financialforecastacr
set LOCATION=eastus

REM Parse command line arguments (basic implementation)
:parse_args
if "%~1"=="" goto end_parse_args
if "%~1"=="--resource-group" (
    set RESOURCE_GROUP=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--container-name" (
    set CONTAINER_GROUP_NAME=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--image" (
    set IMAGE_NAME=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--storage-account" (
    set STORAGE_ACCOUNT_NAME=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--file-share" (
    set FILE_SHARE_NAME=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--acr-name" (
    set ACR_NAME=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--location" (
    set LOCATION=%~2
    shift
    shift
    goto parse_args
)
shift
goto parse_args
:end_parse_args

REM Get ACR credentials
echo Getting ACR credentials...
FOR /F "tokens=*" %%g IN ('az acr credential show --name %ACR_NAME% --query username -o tsv') do (SET ACR_USERNAME=%%g)
FOR /F "tokens=*" %%g IN ('az acr credential show --name %ACR_NAME% --query "passwords[0].value" -o tsv') do (SET ACR_PASSWORD=%%g)
FOR /F "tokens=*" %%g IN ('az acr show --name %ACR_NAME% --query loginServer -o tsv') do (SET ACR_LOGIN_SERVER=%%g)

REM Get storage account key
echo Getting storage account key...
FOR /F "tokens=*" %%g IN ('az storage account keys list --resource-group %RESOURCE_GROUP% --account-name %STORAGE_ACCOUNT_NAME% --query "[0].value" -o tsv') do (SET STORAGE_ACCOUNT_KEY=%%g)

REM Get storage connection string
echo Getting storage connection string...
FOR /F "tokens=*" %%g IN ('az storage account show-connection-string --resource-group %RESOURCE_GROUP% --name %STORAGE_ACCOUNT_NAME% --query connectionString -o tsv') do (SET STORAGE_CONNECTION_STRING=%%g)

REM Check if file share exists, create if not
echo Checking file share existence...
FOR /F "tokens=*" %%g IN ('az storage share exists --name %FILE_SHARE_NAME% --account-name %STORAGE_ACCOUNT_NAME% --account-key %STORAGE_ACCOUNT_KEY% --query exists -o tsv') do (SET SHARE_EXISTS=%%g)

if "%SHARE_EXISTS%"=="false" (
    echo Creating file share %FILE_SHARE_NAME%...
    az storage share create --name %FILE_SHARE_NAME% --account-name %STORAGE_ACCOUNT_NAME% --account-key %STORAGE_ACCOUNT_KEY%
    
    echo Creating directory structure in file share...
    az storage directory create --share-name %FILE_SHARE_NAME% --name "scraping/scraped_data" --account-name %STORAGE_ACCOUNT_NAME% --account-key %STORAGE_ACCOUNT_KEY%
    az storage directory create --share-name %FILE_SHARE_NAME% --name "modelling/predictions" --account-name %STORAGE_ACCOUNT_NAME% --account-key %STORAGE_ACCOUNT_KEY%
    az storage directory create --share-name %FILE_SHARE_NAME% --name "modelling/cache" --account-name %STORAGE_ACCOUNT_NAME% --account-key %STORAGE_ACCOUNT_KEY%
    az storage directory create --share-name %FILE_SHARE_NAME% --name "forecasting/data" --account-name %STORAGE_ACCOUNT_NAME% --account-key %STORAGE_ACCOUNT_KEY%
)

REM Deploy container with file share mount
echo Deploying container instance with file share mount...
az container create ^
  --resource-group %RESOURCE_GROUP% ^
  --name %CONTAINER_GROUP_NAME% ^
  --image %IMAGE_NAME% ^
  --registry-login-server %ACR_LOGIN_SERVER% ^
  --registry-username %ACR_USERNAME% ^
  --registry-password %ACR_PASSWORD% ^
  --environment-variables AZURE_STORAGE_CONNECTION_STRING=%STORAGE_CONNECTION_STRING% ^
  --azure-file-volume-account-name %STORAGE_ACCOUNT_NAME% ^
  --azure-file-volume-account-key %STORAGE_ACCOUNT_KEY% ^
  --azure-file-volume-share-name %FILE_SHARE_NAME% ^
  --azure-file-volume-mount-path /app ^
  --cpu 2 ^
  --memory 8 ^
  --restart-policy Never ^
  --location %LOCATION%

echo Container deployment complete!
