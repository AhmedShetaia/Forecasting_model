// Azure Bicep template for deploying Azure resources for the financial forecasting pipeline
// main.bicep

@description('Name of the resource group to deploy resources into')
param resourceGroupName string = 'financial-forecasting-rg'

@description('Location for all resources.')
param location string = resourceGroup().location

@description('Name of the storage account')
param storageAccountName string = 'financialforecastsa'

@description('Name of the blob container')
param blobContainerName string = 'forecast-predictions'

@description('Name of the Azure file share')
param fileShareName string = 'forecast-pipeline-share'

@description('Name for the container registry')
param acrName string = 'financialforecastacr'

@description('Name for the log analytics workspace')
param logAnalyticsWorkspaceName string = 'financial-forecast-logs'

@description('Name for the managed identity')
param identityName string = 'financial-forecast-identity'

@description('Container group name')
param containerGroupName string = 'financial-forecast-container'

// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2022-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
  }
}

// Blob Container
resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2022-05-01' = {
  name: '${storageAccount.name}/default/${blobContainerName}'
  properties: {
    publicAccess: 'Blob'
  }
}

// File Share
resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2022-05-01' = {
  name: '${storageAccount.name}/default/${fileShareName}'
  properties: {
    shareQuota: 100
  }
}

// Azure Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2021-06-01-preview' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// Log Analytics Workspace
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Managed Identity
resource userIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2018-11-30' = {
  name: identityName
  location: location
}

// Role Assignment for Storage Access
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, userIdentity.id, 'blob-data-contributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor role
    principalId: userIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output storageAccountName string = storageAccount.name
output storageAccountId string = storageAccount.id
output blobContainerName string = blobContainerName
output fileShareName string = fileShareName
output acrLoginServer string = containerRegistry.properties.loginServer
output identityId string = userIdentity.id
output identityClientId string = userIdentity.properties.clientId
output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.properties.customerId
