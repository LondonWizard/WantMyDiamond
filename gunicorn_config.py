# Gunicorn configuration file
import multiprocessing

# Socket path
bind = "127.0.0.1:8000"

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Log files
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"

# Process naming
proc_name = "wantmydiamond"

# Server mechanics
daemon = False
pidfile = "/var/run/gunicorn/wantmydiamond.pid"
user = "www-data"
group = "www-data"
tmp_upload_dir = None 