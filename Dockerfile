FROM python:3.8.9-slim

ENV PRIVATE_KEY=

RUN apt-get update \
    && apt-get install -y gcc \
    && apt-get clean

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

ENTRYPOINT python relayer-launcher.py launch -k $PRIVATE_KEY
