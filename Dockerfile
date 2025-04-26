FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY soap_service_multiqueue.py .
COPY color_producer_soap.py .
COPY multithread_mdbs_routing_keys.py .
COPY statistics_client.py .



CMD ["python", "soap_service_multiqueue.py"]