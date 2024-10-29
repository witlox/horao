FROM python:3.11-slim-stretch

RUN mkdir -p /usr/src/app
COPY horao /usr/src/app
WORKDIR /usr/src/app

RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install --no-cache-dir poetry
RUN poetry config virtualenvs.create false
RUN poetry config virtualenvs.in-project true
RUN poetry config experimental.new-installer false
RUN poetry config virtualenvs.path /usr/src/app/.venv
RUN poetry config cache-dir /usr/src/app/.cache
COPY pyproject.toml poetry.lock /usr/src/app/
RUN poetry install --no-dev

EXPOSE 8081

ENTRYPOINT [ "gunicorn" ]
CMD ["-w", "2", "-b", "0.0.0.0:8081", "ASGI_APP"]
