FROM arenadata/adcmbase:20200812154141

COPY . /adcm/

RUN cp -r /adcm/os/* / && rm -rf /adcm/os; cp -r /adcm/python/ansible/* /usr/local/lib/python3.8/site-packages/ansible/ && rm -rf /adcm/python/ansible && rmdir /var/log/nginx;

# Secret_key is mandatory for build_static procedure,
# but should not be hardcoded in the image.
# It will be generated on first start.
RUN /adcm/web/build_static.sh && rm -f /adcm/web/build_static.sh

EXPOSE 8000

CMD ["/etc/startup.sh"]
