FROM python:3.7-alpine

ENV PYTHONUNBUFFERED 1

RUN apk update && apk add jpeg-dev zlib zlib-dev postgresql-dev gcc python3-dev musl-dev
RUN pip install pipenv

RUN mkdir /project
RUN cd /project

COPY ./Pipfile ./Pipfile
COPY ./Pipfile.lock ./Pipfile.lock

RUN pipenv install --system --deploy --ignore-pipfile --dev

RUN mkdir ./app
COPY ./app ./app
WORKDIR /project/app

RUN mkdir -p /vol/web/media
RUN mkdir -p /vol/web/static
# RUN adduser -D user
# RUN chown -R user:user /vol/
# RUN chmod -R 755 /vol/web
# USER user
CMD ["sleep", "365d"]