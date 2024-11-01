# HORAO: management engine for hybrid multi-cloud environments

[![Python package](https://github.com/witlox/horao/actions/workflows/build-test.yml/badge.svg)](https://github.com/witlox/horao/actions/workflows/tox.yml) ![Python package](https://github.com/witlox/horao/actions/workflows/type-checks.yml/badge.svg) [![codecov](https://codecov.io/github/witlox/horao/graph/badge.svg?token=WP4MHBX34H)](https://codecov.io/github/witlox/horao)

There are various cloud based management engines available. These tend to be either very specific to a certain cloud provider, or very generic and complex. The goal of HORAO is to provide a simple, yet powerful, management engine that can be used to manage hybrid multi-cloud environments. One of the key design features is to provide a model-based approach to managing resources, which allows for a high level of abstraction and automation.

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
  b. `poetry run gunicorn horao:init_api -k uvicorn.workers.UvicornWorker --reload`
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
The following settings are available:
- DEBUG: boolean, default=False; set to True to enable debug mode
- UI: boolean, default=False; set to True to enable the UI for the API
- CORS: string, default="*"; set to the allowed origins for CORS
- PEER_SECRET: string, default=""; set the secret for authenticating peers 
- CLOCK_OFFSET: float, default=0.0; set the allowed clock offset for synchronization
- REDIS_URL: string, default="redis://redis:6379/0"; set the URL for the Redis database