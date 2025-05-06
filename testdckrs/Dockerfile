# ---- alap image ----
    FROM python:3.11-slim

    # ---- környezet ----
    ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1

    WORKDIR /app

    # ---- függőségek ----
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    # ---- forráskód ----
    COPY soap/       soap/
    COPY mdb/        mdb/
    COPY statistics/ statistics/

    # ---- alapértelmezett indulás (compose felülírja) ----
    CMD ["python", "soap/soap_service_multiqueue.py"]