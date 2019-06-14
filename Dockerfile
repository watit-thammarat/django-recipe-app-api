FROM python:3.7-alpine
MAINTAINER Watit Thammarat

ENV PYTHONUNBUFFERED 1

RUN pip install pipenv

RUN mkdir /project
WORKDIR /project
COPY ./Pipfile ./Pipfile
COPY ./Pipfile.lock ./Pipfile.lock
RUN pipenv install --system --deploy --ignore-pipfile --dev
RUN mkdir ./app
COPY ./app ./app

RUN adduser -D user
USER user
