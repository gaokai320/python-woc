FROM python:3

WORKDIR /home/python

COPY oscar.py requirements.txt setup.cfg setup.py test.py docs/ Makefile  ./
RUN pip install --no-cache-dir -r requirements.txt
