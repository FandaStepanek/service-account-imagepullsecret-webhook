FROM python:3.10

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-b", "0.0.0.0:8124", "--certfile=/certs/tls.crt", "--keyfile=/certs/tls.key", "webhook:app"]