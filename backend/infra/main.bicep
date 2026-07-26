// Subscription-scoped entry point for `azd up`. Creates the resource group and
// hands everything else to resources.bicep. azd fills environmentName/location
// from the azd env; it prompts for the SQL admin password (a @secure param not
// listed in main.parameters.json) and stores it in .azure/<env>/.env.
targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('azd environment name — derives resource names + the resource group.')
param environmentName string

@minLength(1)
@description('Primary region for all resources.')
param location string

@description('Azure SQL administrator login.')
param sqlAdminLogin string = 'alarmiadmin'

@secure()
@minLength(12)
@description('Azure SQL admin password. Must meet SQL complexity (upper+lower+digit) and be URL-safe — avoid @ : / ? # & % so it embeds cleanly in the connection string.')
param sqlAdminPassword string

@description('Allowed browser origins as a JSON array string, e.g. ["https://app.example.com"]. Empty = localhost-only (regex default). Set once the web app is deployed.')
param corsOrigins string = ''

var tags = { 'azd-env-name': environmentName }

resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module resources 'resources.bicep' = {
  name: 'resources'
  scope: rg
  params: {
    location: location
    tags: tags
    resourceToken: toLower(uniqueString(subscription().id, environmentName, location))
    sqlAdminLogin: sqlAdminLogin
    sqlAdminPassword: sqlAdminPassword
    corsOrigins: corsOrigins
  }
}

output AZURE_LOCATION string = location
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.registryLoginServer
output SERVICE_API_ENDPOINT string = resources.outputs.apiEndpoint
output AZURE_SQL_SERVER string = resources.outputs.sqlServerFqdn
