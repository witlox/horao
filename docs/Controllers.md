# Controllers to connect to the resource providers
> This projects follows a microservices architecture, as such we expect to have an instance of `HORAO` per provider.
> E.g. one for AWS, one for Azure, one for GCP, one for each management plane of OCHAMI or CSM, etc.

The providers follow the default authentication and authorization flow supplied by given providers.
## Selecting a provider
Currently the following providers are supported:
- Amazon Web Services (AWS)
- Microsoft Azure (MA)
- Google Cloud Platform (GCP)

Planned future providers:
- Open Cloud Hybrid API Management Interface (OCHAMI)
- Cray System Manager (CSM)

In order to select a provider, the following environment variables need to be set:
```dotenv
CONTROLLER_BACKEND=AWS
```
This will select the AWS provider (use the key between brackets in the list above).

### Pull vs push mechanisms
Data from the provider can be pulled (scanned), the following environment variables need to be set:
```dotenv
CONTROLLER_PULL_INTERVAL=60 #integer, default=60; set the interval in seconds to pull data from the provider
```
In the future we will include push (events) support where possible, the subscription mechanism will be provider specific. 
Note that a (slow) pull mechanism will always be needed to have a consistent state.

## AWS
The AWS provider uses the `boto3` library to connect to the AWS API. The following environment variables need to be set:
```dotenv
AWS_ACCESS_KEY_ID=access_key_id
AWS_SECRET_ACCESS_KEY=secret_access_key
AWS_REGION=region
```
For AWS we assume that a specific TAG with a specific value is set on the instances that need to be managed. The following environment variables need to be set:
```dotenv
AWS_TAG=tag_key
AWS_TAG_VALUE=tag_value
```
## Microsoft Azure
The Microsoft Azure provider uses the `azure-mgmt-compute` library to connect to the Azure API. The following environment variables need to be set:
```dotenv
AZURE_CLIENT_ID=client_id
AZURE_CLIENT_SECRET=client_secret
AZURE_TENANT_ID=tenant_id
AZURE_SUBSCRIPTION_ID=subscription_id
```
For Azure we assume that a specific TAG with a specific value is set on the instances that need to be managed. The following environment variables need to be set:
```dotenv
AZURE_TAG=tag_key
```
## Google Cloud Platform
The Google Cloud Platform provider uses the `google-cloud-compute` library to connect to the GCP API. The following environment variables need to be set:
```dotenv
GCP_PROJECT=project
GCP_ZONE=zone
```
For GCP we assume that a specific TAG with a specific value is set on the instances that need to be managed. The following environment variables need to be set:
```dotenv
GCP_TAG=tag_key
```
