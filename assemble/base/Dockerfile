FROM python:3.9.2-alpine

COPY requirements-base.txt /
COPY build.sh /

RUN /build.sh

CMD ["/bin/sh"]
