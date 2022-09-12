import os

from django.conf import settings


def write_to_uwsgi_stdout(msg: str) -> bool:
    if not os.path.exists(settings.PID_FILE):
        return False
    with open(settings.PID_FILE, encoding="utf-8") as f:
        uwsgi_pid = f.read().strip()
    fd_1 = f"/proc/{uwsgi_pid}/fd/1"
    if not os.path.exists(fd_1):
        return False
    fd = os.open(fd_1, os.O_WRONLY)
    if not msg.endswith(os.linesep):
        msg = f"{msg}{os.linesep}"
    os.write(fd, msg.encode("utf-8"))
    return True
