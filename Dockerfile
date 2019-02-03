FROM python:3.7-stretch

ADD ./src /app
ADD ./requirements.txt /requirements.txt

RUN pip install --upgrade pip
RUN pip install -r /requirements.txt

WORKDIR /app
