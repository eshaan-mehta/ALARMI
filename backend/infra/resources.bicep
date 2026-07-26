// All ALARMI backend resources, resource-group scoped.
//
//   Container App  ── the FastAPI image (min=max 1 replica: the in-process
//                     BackgroundTask worker isn't durable, so we never scale to
//                     zero and never fan a single upload across replicas)
//   Azure SQL      ── serverless, auto-pauses when idle (metadata store)
//   Storage        ── blob container for IFC sources + GLBs
//   ACR + identity ── registry the image is pushed to, pulled via managed id
//   Log Analytics  ── Container App logs
@description('Region for all resources.')
param location string

@description('Tags applied to every resource.')
param tags object

@description('Short unique suffix for globally-unique names.')
param resourceToken string

param sqlAdminLogin string

@secure()
param sqlAdminPassword string

param corsOrigins string

var databaseName = 'alarmi'
var blobContainerName = 'alarmi'
// azd overwrites this on `azd deploy`; the placeholder just lets provision
// succeed while ACR is still empty.
var placeholderImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

// --- Log Analytics ---
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log-${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// --- Container Registry ---
// Admin user enabled so the Container App pulls with registry username/password
// instead of a managed identity + AcrPull role assignment. This subscription
// denies Microsoft.Authorization/roleAssignments/write, so the role-based path
// isn't available — admin creds need no role assignment.
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'acr${resourceToken}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: true }
}

// --- Storage (blob) ---
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'st${resourceToken}'
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storage
  name: 'default'
}

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: blobContainerName
}

// --- Azure SQL (serverless) ---
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: 'sql-${resourceToken}'
  location: location
  tags: tags
  properties: {
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource sqlDb 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sqlServer
  name: databaseName
  location: location
  tags: tags
  sku: {
    name: 'GP_S_Gen5_1' // General Purpose, serverless, 1 vCore
    tier: 'GeneralPurpose'
    family: 'Gen5'
    capacity: 1
  }
  properties: {
    autoPauseDelay: 60 // pause after 60 min idle (first request after resumes, ~30s cold start)
    minCapacity: json('0.5')
    maxSizeBytes: 2147483648 // 2 GB
    zoneRedundant: false
  }
}

// Special 0.0.0.0 rule = "allow Azure services" (the Container App reaches SQL).
resource sqlFirewall 'Microsoft.Sql/servers/firewallRules@2023-05-01-preview' = {
  parent: sqlServer
  name: 'AllowAllAzureIPs'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// --- Container Apps environment + app ---
resource caEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${resourceToken}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

var databaseUrl = 'mssql+pyodbc://${sqlAdminLogin}:${sqlAdminPassword}@${sqlServer.properties.fullyQualifiedDomainName}:1433/${databaseName}?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no'
var storageConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'

var baseEnv = [
  { name: 'APP_ENV', value: 'azure' }
  { name: 'DATABASE_URL', secretRef: 'database-url' }
  { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'storage-connection-string' }
  { name: 'BLOB_CONTAINER', value: blobContainerName }
]
var corsEnv = empty(corsOrigins) ? [] : [ { name: 'CORS_ORIGINS', value: corsOrigins } ]

resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-api-${resourceToken}'
  location: location
  // azd finds the app to deploy to by this tag (matches the service in azure.yaml).
  tags: union(tags, { 'azd-service-name': 'api' })
  properties: {
    managedEnvironmentId: caEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        { name: 'acr-password', value: acr.listCredentials().passwords[0].value }
        { name: 'database-url', value: databaseUrl }
        { name: 'storage-connection-string', value: storageConnectionString }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: placeholderImage
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          env: concat(baseEnv, corsEnv)
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

output registryLoginServer string = acr.properties.loginServer
output apiEndpoint string = 'https://${api.properties.configuration.ingress.fqdn}'
output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName
