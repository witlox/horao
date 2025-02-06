FROM python:3.12-slim

RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install --no-cache-dir poetry

RUN mkdir /code
WORKDIR /code
COPY pyproject.toml poetry.lock .env.production /code/
ENV POETRY_PLUGIN_DOTENV_LOCATION="/code/.env.production"
RUN poetry self add poetry-dotenv-plugin
RUN poetry config virtualenvs.create false
COPY . /code
RUN poetry install

EXPOSE 8080

ENTRYPOINT [ "gunicorn" ]
CMD ["-b", "0.0.0.0:8080", "horao:init", "-k", "uvicorn.workers.UvicornWorker"]
