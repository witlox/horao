FROM python:3.11-slim-stretch

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/

RUN pip3 install --no-cache-dir -r requirements.txt --upgrade

COPY horao /usr/src/app

EXPOSE 8081

ENTRYPOINT [ "gunicorn" ]
CMD ["-w", "2", "-b", "0.0.0.0:8081", "ASGI_APP"]
