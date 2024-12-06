# Authentication mechanisms for HORAO

There are 3 configurations that need to be applied, the first is peer authentication using a shared secret.
The second and third are user authentication that need to be configured for regular users and administrators.
Both users and administrators will need to use the same Open ID Connect provider.
Basic information requested is only email, identification of administrators is done by the roles custom claim (so the OIDC provider needs to support this, and needs to be configured, like https://claims.idp.example.com/role).

## Peer authentication
All instances of `HORAO` that form one cluster need to be able to authenticate each other. This is done using a shared secret that is stored in the `.env` file. The shared secret is used to sign the messages that are exchanged between the instances. The shared secret is stored in the `.env` file as follows:
```dotenv
PEER_SECRET=abracadabra
```
Peer synchronization is done using the `PEERS` environment variable. This is a comma separated list of peers that need to be synchronized. The peers are identified by their IP address. The `PEERS` environment variable is stored in the `.env` file as follows:
```dotenv
PEERS=10.0.0.1,some.host.somewhere
```
These are comma separated values that are used to identify the peers that need to be synchronized.
The synchronization happens over the 'synchronize' endpoint on the API.

There is a 'PEER_STRICT' that defaults to 'True'. This means that the peers origin needs to be matched to the value supplied in the 'PEERS' environment variable. If 'PEER_STRICT' is set to 'False' then the origin of the peer is not checked.
The hostname of the system should be fetched automatically, but on internal domains this can return faulty information, this hostname can be set manually:
```dotenv
HOST_ID=some.fqdn.com
```

## Open ID Connect parts
The following variables need to be set in the `.env` file:
```dotenv
OAUTH_NAME=openidc
OAUTH_CLIENT_ID=client_id
OAUTH_CLIENT_SECRET=client_secret
OAUTH_SERVER_METADATA_URL=https://idp.example.com/.well-known/openid-configuration
OAUTH_BASE_URL=https://idp.example.com
OAUTH_AUTHORIZE_URL=https://idp.example.com/authorize
OAUTH_AUTHORIZE_PARAMS={}
OAUTH_ACCESS_TOKEN_URL=https://idp.example.com/token
OAUTH_REQUEST_TOKEN_URL=None
OAUTH_ROLE_URI=https://claims.idp.example.com/role
```
The `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET` are the client id and client secret that are provided by the Open ID Connect provider.

### Administrators
Administrators are identified by the roles custom claim. The roles custom claim is used to identify the administrators. The roles custom claim is stored in the `.env` file as follows:
```dotenv
ADMINISTRATOR_ROLE=administrator
```
### Users
If the roles custom claim is not present, or the user does not have the administrator role, then the user is considered a regular user.