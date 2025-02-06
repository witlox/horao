# HORAO: management engine for hybrid multi-cloud environments

[![Python package](https://github.com/witlox/horao/actions/workflows/build-test.yml/badge.svg)](https://github.com/witlox/horao/actions/workflows/tox.yml) ![Python package](https://github.com/witlox/horao/actions/workflows/type-checks.yml/badge.svg) [![codecov](https://codecov.io/github/witlox/horao/graph/badge.svg?token=WP4MHBX34H)](https://codecov.io/github/witlox/horao)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fwitlox%2Fhorao.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fwitlox%2Fhorao?ref=badge_shield)

The goal of `HORAO` is to be able to manage tenants across various hybrid multi-cloud environments. The engine is designed to be able to manage resources across various cloud providers, such as AWS, Azure, and GCP as well as on-prem with engines like [OCHAMI](https://www.ochami.org).
One of the key design features is to provide a model-based approach to managing resources, which allows for a high level of abstraction and automation.
`HORAO` will be able to check the current allocation state of the distributed resources, and users will be able to create reservations based on time and availability.
Secondary, site administrators will be able to plan maintenance events, to validate what the impact of a maintenance event will be on the tenants. 

For development please check out the [Architecture](docs/Architecture.md) and [Development notes](docs/Development.md).

## Installation

### Prerequisites

- Python 3.11 or higher
- Poetry
- A virtual environment
- (Optional) Docker
- (Optional) Docker-compose
- (Optional) Redis
- (Optional but recommended) NTP

### Steps
The command line way:
```bash 
1. Clone the repository
2. Create a virtual environment (`python -m venv .venv`)
3. Activate the virtual environment (`source .venv/bin/activate`)
4. Install poetry (`pip install poetry`)
5. Add the dotenv plugin to poetry (`poetry self add poetry-dotenv-plugin`)
6. Install the required packages (`poetry install`)
4. Run the project
  a. `poetry run python horao/main.py`
  b. `poetry run gunicorn horao:init -k uvicorn.workers.UvicornWorker --reload`
```

The docker way, either use the `devcontainer` or run with `docker-compose`:
```bash
1. Clone the repository
2. Run the project
  a. `docker-compose -f docker-compose.yml build`
  b. `docker-compose -f docker-compose.yml up`
```

## Settings

The settings are stored in a `.env` file. The default selected by poetry is `.env` which is configured for development.
The following settings should be configured:
```dotenv
DEBUG: False #boolean, default=False; set to True to enable debug mode, very chatty
UI: False #boolean, default=False; set to True to enable the UI for the API
CORS: * #string, default=*; set to the allowed origins for CORS
PEER_SECRET: abracadabra #string, default=""; set the secret for authenticating peers
PEERS: a,b,c #string, default=""; set the comma seperated list of peers to sync with 
REDIS_URL: redis://localhost:6379/0 #string, default="redis://redis:6379/0"; set the URL for the Redis database
```
For all other settings, please check the relevant documentation at https://witlox.github.io/horao/.


## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fwitlox%2Fhorao.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fwitlox%2Fhorao?ref=badge_large)