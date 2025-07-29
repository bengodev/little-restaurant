### Production strategy with Websocket and notification setup.

```bash
daphne projrestaurant.asgi:application -b 0.0.0.0 -p 8000
python3 manage.py listen_notify
```

Those two commands **work**, but for **production** you must wrap them in **supervision** (systemd, supervisor, Docker, etc.) and add a **reverse-proxy** (Nginx).  
Below is a concise checklist you can copy-paste into any Linux server.

────────────────────────────────────────
1. Run Redis in production
────────────────────────────────────────
```bash
sudo apt install redis-server
sudo systemctl enable --now redis-server
```

────────────────────────────────────────
2. Run Daphne under systemd
────────────────────────────────────────
`/etc/systemd/system/daphne.service`

```ini
[Unit]
Description=Daphne ASGI server
After=network.target redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/projrestaurant
ExecStart=/srv/projrestaurant/venv/bin/daphne \
          -b 0.0.0.0 -p 8000 \
          projrestaurant.asgi:application
Restart=on-failure
Environment=DJANGO_SETTINGS_MODULE=projrestaurant.settings_prod

[Install]
WantedBy=multi-user.target
```

────────────────────────────────────────
3. Run the listener under systemd
────────────────────────────────────────
`/etc/systemd/system/listen_notify.service`

```ini
[Unit]
Description=Django Postgres Listener
After=network.target redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/projrestaurant
ExecStart=/srv/projrestaurant/venv/bin/python manage.py listen_notify
Restart=on-failure
Environment=DJANGO_SETTINGS_MODULE=projrestaurant.settings_prod

[Install]
WantedBy=multi-user.target
```

Enable & start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now daphne listen_notify
```

────────────────────────────────────────
4. Nginx as reverse-proxy + static files
────────────────────────────────────────
`/etc/nginx/sites-available/projrestaurant`

```nginx
upstream daphne {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://daphne;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /static/ {
        alias /srv/projrestaurant/staticfiles/;
    }

    location /media/ {
        alias /srv/projrestaurant/media/;
    }
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/projrestaurant /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

────────────────────────────────────────
5. Production settings differences
────────────────────────────────────────
- `DEBUG = False`  
- `ALLOWED_HOSTS = ['your-domain.com']`  
- Use PostgreSQL (already done).  
- `STATIC_ROOT = BASE_DIR / 'staticfiles'` (run `collectstatic`).  
- Use HTTPS (add certificates via Let’s Encrypt).

────────────────────────────────────────
6. Restart after every deploy
────────────────────────────────────────
```bash
sudo systemctl restart daphne listen_notify
```

That is the minimal production-ready setup.