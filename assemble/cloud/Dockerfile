ARG ADCM_IMAGE
ARG ADCM_TAG
FROM $ADCM_IMAGE:$ADCM_TAG

RUN apk add git && pip install adcm-client

EXPOSE 8000

CMD ["/etc/startup.sh"]
