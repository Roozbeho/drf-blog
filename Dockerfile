FROM public.ecr.aws/docker/library/python:3.12.3-alpine

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apk update && apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    postgresql-client  # Adds pg_isready

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

COPY boot.sh .
RUN chmod +x boot.sh
