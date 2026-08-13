FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /service

# rasterio's manylinux wheel dynamically links against libexpat at runtime, which
# python:3.11-slim doesn't ship. Some build environments only allow HTTPS egress, so
# switch the apt sources off plain HTTP first — harmless where HTTP already works.
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install --yes --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.lock.txt

COPY app ./app

RUN useradd \
        --create-home \
        --shell /usr/sbin/nologin \
        surge \
    && chown -R surge:surge /service

USER surge

EXPOSE 8000

CMD [ \
    "uvicorn", \
    "app.main:app", \
    "--host", \
    "0.0.0.0", \
    "--port", \
    "8000" \
]
