FROM python:3.12.2-slim
LABEL maintainer="evgeniy97v@gmail.com"

ENV PYTHONUNBUFFERED 1

WORKDIR app/

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /files/media

RUN adduser \
    --disabled-password \
    --no-create-home \
    user


RUN chown -R user /files/media
RUN chmod -R 755 /files/media


USER user
