# Development notes

## Redoc definition
All of the API calls are commented redoc style in the code.
When running with the DEBUG flag, redoc is available at the `/docs` endpoint.

## Python checks
The project is checked with the following tools:
- Coding style: [Black](https://black.readthedocs.io/en/stable/index.html)
- Type checking: [Mypy](https://mypy.readthedocs.io/en/stable/index.html)
- Linting: [Flake8](https://flake8.pycqa.org/en/latest/)
- Testing: [Pytest](https://docs.pytest.org/en/stable/)
- Coverage: [pytest-cov](https://pytest-cov.readthedocs.io/en/latest/)

# Environments
The project is managed using [Poetry](https://python-poetry.org/).
The environment variables are managed via poetry using [poetry-dotenv-plugin](https://github.com/mpeteuil/poetry-dotenv-plugin).
## Poetry
There are 3 specific environment flags that are configured in the `pyproject.toml` file:
- default: all packages necessary to run the code in production
- dev: all packages necessary to run the code in development with the checks
- test: all packages necessary to run the tests and coverage
## DotEnv
There are 2 dotenv files that are supplied:
- `.env` for development
- `.env.production` for production (with recommended settings)

## Launch tests

After enabling your virtual environment, run the following command:

```bash
pip install poetry
poetry install --with test --with dev
```

Then run the following command:

```bash
poetry run pytest
```
