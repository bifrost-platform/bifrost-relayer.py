FROM python:3.10-slim

ENV PRIVATE_KEY=

RUN apt-get update \
    && apt-get install --no-install-recommends -y git build-essential gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "relayer-launcher.py", "--slow-relayer", "--prometheus"]
