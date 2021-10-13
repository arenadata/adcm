FROM python:3.10-alpine

COPY requirements-base.txt /
COPY build.sh /

RUN /build.sh

CMD ["/bin/sh"]
