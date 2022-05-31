ARG ADCMBASE_IMAGE
ARG ADCMBASE_TAG
FROM $ADCMBASE_IMAGE:$ADCMBASE_TAG

COPY . /adcm/
COPY assemble/app/build_venv.sh /

RUN cp -r /adcm/os/* / && rm -rf /adcm/os; /build_venv.sh && rm -f /build_venv.sh && rm -rf /adcm/python/ansible && rmdir /var/log/nginx;

RUN /venv.sh reqs default /adcm/requirements.txt
RUN /venv.sh reqs 2.9 /adcm/requirements.txt


# Secret_key is mandatory for build_static procedure,
# but should not be hardcoded in the image.
# It will be generated on first start.
RUN /venv.sh run default /adcm/web/build_static.sh && rm -f /adcm/web/build_static.sh

EXPOSE 8000

CMD ["/etc/startup.sh"]
