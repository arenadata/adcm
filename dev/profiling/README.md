# Gather ADCM Performance Statistics

## Summary

By target

| Target | Tools            |
|--------|------------------|
| API    | Silk, nginx logs |
| DB     | Silk, PGBadger   |
| Python | Silk, CProfile   |

## Tools

### Nginx Logs

#### Description

Altering format of Nginx logs can be useful for gathering info about time spent on requests.

Thou it can't help with monitoring DB interactions or resource usage, 
it doesn't require container restart, image re-build, etc.

#### How To

ADCM has custom nginx config stored in project at `os/etc/nginx/http.d/adcm.conf`
which is placed at `/etc/nginx/http.d/adcm.conf` inside the container.

What we need to do is to:
1. Edit this file in container
2. Add custom log format at "root" (a.k.a. `http` node)
```
log_format upstream_time '$request_method | $status | '
                         'request_time=$request_time | upstream=$upstream_response_time | '
                         '$uri | $query_string';
```
2. Add `access_log /adcm/data/log/nginx/upstream_time.log upstream_time;`
   to `server` nodes we want to log
3. Save changes, validate them with `nginx -t`
4. Reload `nginx -s reload`

Example of `adcm.conf` after changes:
```text
upstream django {
    server unix:///run/adcm.sock; 
}

map $status $abnormal {
    ~^200  0;
    default 1;
}

log_format upstream_time '$request_method | $status | '
                         'request_time=$request_time | upstream=$upstream_response_time | '
                         '$uri | $query_string';

server {
    listen      8000;
    access_log /adcm/data/log/nginx/upstream_time.log upstream_time;
    include "http.d/proxy.inc";
}

server {
    listen      8443 ssl;
    access_log /adcm/data/log/nginx/upstream_time.log upstream_time;
    ssl_certificate         /adcm/data/conf/ssl/cert.pem;
    ssl_certificate_key     /adcm/data/conf/ssl/key.pem;    
    include "http.d/proxy.inc";
}
```

You can customize `log_format` for your need, check out
[documentation on instruction](https://nginx.org/en/docs/http/ngx_http_log_module.html#log_format) 
and [available variables](https://nginx.org/en/docs/http/ngx_http_core_module.html#var_status)

Logs will be placed at `/adcm/data/log/nginx/upstream_time.log` inside the container

### Silk

#### Description

[django-silk](https://github.com/jazzband/django-silk) 
is a tool to gather information about Django application performance:
API response time, amount of DB queries and time spent on them, python performance.

#### How To

You can set up it by yourself following guidelines from documentation
and checking out examples here.

Below comes the description how to prepare ADCM to be launched with silk.

###### Alter generic settings and URLs

Alternative to editing files by yourself

```shell
# when in ADCM project root
cp dev/profiling/silk/* python/adcm/
```

Then during container launch you can specify `DJANGO_SETTINGS_MODULE` env variable to enable silk
and don't specify it for "regular" launch

```shell
docker run ... -e DJANGO_SETTINGS_MODULE=adcm.silk_settings
```

###### Install dependencies

Silk can be installed with `profiling` dependencies group (or directly via `pip`)

```shell
poetry install --with profiling --no-root
```

The most simple way to prepare ADCM for silk profiling is: 

1. Run ADCM with your code
2. Install profiling group `docker exec adcm poetry install --with profiling --no-root -C /adcm`
   or (if profiling group is not available) `docker exec adcm pip install django-silk`
3. Then collect static for silk with `docker exec -it adcm-pg-code /adcm/python/manage.py collectstatic`
4. Commit your container state to new image (e.g. `docker commit adcm-pg-code hub.adsw.io/adcm/adcm:adcm-prof`)
5. Run container from new image providing `DJANGO_SETTINGS_MODULE` as env variable
   and provide `-e DEBUG=1`


### Django Debug Toolbar

#### Description

[django-debug-toolbar](https://github.com/django-commons/django-debug-toolbar) 
is a configurable set of panels that display various debug information about the current request/response and 
when clicked, display more details about the panel's content.

#### How To
1. Run ADCM container (named `adcm`, for example)
2. Copy files to container and install dependencies
   ```shell
   docker cp dev/profiling/django_debug_toolbar/. adcm:adcm/python/adcm/ && \
   docker exec -it adcm pip install django-debug-toolbar && \
   docker exec -it -e DJANGO_SETTINGS_MODULE=adcm.ddt_settings adcm /adcm/python/manage.py collectstatic
   ```
3. Commit your container state to new image
   ```shell
   docker commit adcm hub.adsw.io/adcm/adcm:adcm-ddt
   ```
4. Run container from new image providing `DJANGO_SETTINGS_MODULE=adcm.ddt_settings`