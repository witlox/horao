# A very trivial guide to creating your virtual enviroment for running this project locally

Steps:

1. Install Python 3.11 or higher
2. Create a virtual environment under the root folder of this project (`python -m venv .venv`)
3. Activate the environment (`source .venv/bin/activate`)
4. Install poetry (`pip install poetry`)
4. Install the required packages (`poetry install`)
   - If you want to install the development dependencies as well, you can run `poetry install --with dev`
   - If you want to install with only testing dependencies, you can run `poetry install --with test`
5. Run the project (`poetry run python horao/main.py`)

## Note on testing

In order to install the testing dependencies you can run the following command `poetry install --with test`.
You can run the tests using the `poetry run pytest` command. This will run the tests in a virtual environment and ensure that the tests are run in a clean environment.

### Coverage
A coverage report is automatically generated when running `pytest`.
