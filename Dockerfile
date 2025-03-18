FROM python:3.9

WORKDIR /app
COPY webhook.py /app/webhook.py

RUN pip install flask

CMD ["python", "/app/webhook.py"]