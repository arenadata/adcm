    charset     utf-8;

    root /adcm/wwwroot;

    client_max_body_size 100M;
    client_body_temp_path /adcm/data/tmp/nginx_client_temp 1 2;
    client_body_timeout 300s;

    location / {
        if ($arg_nocache) {
            add_header Cache-Control no-cache;
        }
        try_files $uri $uri/ /index.html;
    }

    location /swagger {
        uwsgi_pass  django;
        uwsgi_read_timeout 300s;
        uwsgi_send_timeout 300s;
        include     /adcm/conf/nginx/uwsgi_params;
        proxy_set_header Host $http_host;
    }

    location /api {
        uwsgi_pass  django;
        uwsgi_read_timeout 300s;
        uwsgi_send_timeout 300s;
        include     /adcm/conf/nginx/uwsgi_params;
        proxy_set_header Host $http_host;
    }

    location /cm {
        uwsgi_pass  django;
        include     /adcm/conf/nginx/uwsgi_params;
    }

    location /social {
        uwsgi_pass  django;
        include     /adcm/conf/nginx/uwsgi_params;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8020;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $http_host;
    }

    location /status/ {
        # That takes so many lines in access log for statuses,
        # so it is better to disable access for that url
        access_log /var/log/nginx/access.log combined if=$abnormal;
        proxy_pass http://127.0.0.1:8020/;
        proxy_set_header Host $http_host;
    }
