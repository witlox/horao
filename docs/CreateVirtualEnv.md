# A very trivial guide to creating your virtual enviroment for running this project locally

Steps:

1. Install Python 3.11 or higher
2. Create a virtual environment under the root folder of this project (`python -m venv .venv`)
3. Activate the environment (`source .venv/bin/activate`)
4. Install the required packages (`pip install -r requirements.txt`)
5. Run the project (`python horao/main.py`)

## Note on testing

In order to install the testing dependencies you can run the following command `pip install -r test-requirements.txt`.
You can run the tests using the `tox` command. This will run the tests in a virtual environment and ensure that the tests are run in a clean environment.

```bash
pip install -r test-requirements.txt
tox
```
