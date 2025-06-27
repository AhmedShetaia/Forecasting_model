// Azure Bicep template for deploying a container instance with Azure File Share mount
// containerInstance.bicep

@description('Name of the container group')
param containerGroupName string

@description('Location for all resources.')
param location string = resourceGroup().location

@description('Container image to deploy')
param containerImage string

@description('Container registry server')
param registryServer string

@description('Container registry username')
param registryUsername string

@description('Container registry password')
@secure()
param registryPassword string

@description('FRED API Key')
@secure()
param fredApiKey string

@description('Azure Storage Connection String')
@secure()
param storageConnectionString string

@description('Storage account name')
param storageAccountName string

@description('Storage account key')
@secure()
param storageAccountKey string

@description('File share name')
param fileShareName string

// Container Instance with File Share Mount
resource containerGroup 'Microsoft.ContainerInstance/containerGroups@2023-05-01' = {
  name: containerGroupName
  location: location
  properties: {
    containers: [
      {
        name: 'financial-forecasting'
        properties: {
          image: containerImage
          environmentVariables: [
            {
              name: 'FRED_API_KEY'
              value: fredApiKey
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              value: storageConnectionString
            }
          ]
          resources: {
            requests: {
              cpu: 2
              memoryInGB: 8
            }
          }
          volumeMounts: [
            {
              name: 'filesharemount'
              mountPath: '/app'
              readOnly: false
            }
          ]
        }
      }
    ]
    osType: 'Linux'
    restartPolicy: 'Never'
    imageRegistryCredentials: [
      {
        server: registryServer
        username: registryUsername
        password: registryPassword
      }
    ]
    volumes: [
      {
        name: 'filesharemount'
        azureFile: {
          shareName: fileShareName
          storageAccountName: storageAccountName
          storageAccountKey: storageAccountKey
        }
      }
    ]
  }
}

// Outputs
output containerIPv4Address string = containerGroup.properties.ipAddress.ip
