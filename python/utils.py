import os

from django.conf import settings


def write_to_wsgi_stdout(msg: str) -> None:
    with open(settings.PID_FILE, encoding="utf-8") as f:
        uwsgi_pid = f.read().strip()
    fd = os.open(f"/proc/{uwsgi_pid}/fd/1", os.O_WRONLY)
    if not msg.endswith(os.linesep):
        msg = f"{msg}{os.linesep}"
    os.write(fd, msg.encode("utf-8"))
