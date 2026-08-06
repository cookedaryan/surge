FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /service

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