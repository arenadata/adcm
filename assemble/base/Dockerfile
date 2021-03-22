FROM python:3.9-alpine

COPY requirements-base.txt /
COPY build.sh /

RUN /build.sh

CMD ["/bin/sh"]
