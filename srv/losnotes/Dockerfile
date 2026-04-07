FROM docker.io/library/python:3.12-slim-bookworm

EXPOSE 8080

WORKDIR /usr/src/app
COPY losnotes/requirements.txt losnotes/requirements.txt

RUN pip install -r losnotes/requirements.txt

COPY losnotes losnotes

CMD ["python", "losnotes/_main.py"]