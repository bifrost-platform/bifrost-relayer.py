FROM python:3.10-slim

ENV PRIVATE_KEY=

RUN apt update && apt install -y build-essential gcc

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

ENTRYPOINT python relayer-launcher.py launch -k $PRIVATE_KEY
