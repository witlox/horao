# HORAO: management engine for hybrid multi-cloud environments

[![Python package](https://github.com/witlox/horao/actions/workflows/python.yml/badge.svg)](https://github.com/witlox/horao/actions/workflows/tox.yml)

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

1. Clone the repository
2. Install the required packages (`poetry install`)
3. Install the project (`poetry install`)
4. Run the project (`horao`)

## Settings

The settings are stored in a `.env` file. The following settings are available:
- DEBUG: boolean, default=False; set to True to enable debug mode
- UI: boolean, default=False; set to True to enable the UI for the API
- CORS: string, default="*"; set to the allowed origins for CORS
- PEER_SECRET: string, default=""; set the secret for authenticating peers 
- CLOCK_OFFSET: float, default=0.0; set the allowed clock offset for synchronization
- SHARES: int, default=1; set the number of shares for the fair-share scheduler
