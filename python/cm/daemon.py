# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import atexit
import os
import sys
import time
from signal import SIGTERM

from django.conf import settings


class Daemon:
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """

    def __init__(self, pidfile, stdin="/dev/null", stdout="/dev/null", stderr="/dev/null"):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """

        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write(f"fork #1 failed: {e.errno:d} ({e.strerror})\n")
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write(f"fork #2 failed: {e.errno:d} ({e.strerror})\n")
            sys.exit(1)

        try:
            pidfile = open(self.pidfile, "w+", encoding=settings.ENCODING_UTF_8)  # pylint: disable=consider-using-with
        except OSError as e:
            sys.stderr.write(f"Can't open pid file {self.pidfile}\n")
            sys.stderr.write(f"{e.strerror}\n")
            sys.exit(1)

        sys.stdout.flush()
        sys.stderr.flush()
        stdin_file = open(self.stdin, encoding=settings.ENCODING_UTF_8)  # pylint: disable=consider-using-with
        stdout_file = open(self.stdout, "a+", encoding=settings.ENCODING_UTF_8)  # pylint: disable=consider-using-with
        stderr_file = open(self.stderr, "w+", encoding=settings.ENCODING_UTF_8)  # pylint: disable=consider-using-with
        os.dup2(stdin_file.fileno(), sys.stdin.fileno())
        os.dup2(stdout_file.fileno(), sys.stdout.fileno())
        os.dup2(stderr_file.fileno(), sys.stderr.fileno())

        atexit.register(self.delpid)
        pid = str(os.getpid())
        pidfile.write(f"{pid}\n")

    def delpid(self):
        os.remove(self.pidfile)

    def getpid(self):
        try:
            file_handler = open(self.pidfile, encoding=settings.ENCODING_UTF_8)  # pylint: disable=consider-using-with
            try:
                pid = int(file_handler.read().strip())
            except ValueError:
                pid = None

            file_handler.close()
        except OSError:
            pid = None

        return pid

    def checkpid(self):
        pid = self.getpid()
        if pid is None:
            return False
        elif pid == 0:
            return False

        try:
            os.kill(pid, 0)
        except OSError:
            return False

        return True

    def start(self):
        # Check for a pidfile to see if the daemon already runs
        if self.getpid():
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        self.daemonize()
        self.run()

    def stop(self):
        pid = self.getpid()
        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)

            return  # not an error in a restart

        try:
            while True:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print(str(err))
                sys.exit(1)

    def restart(self):
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon.
        It will be called after the process has been daemonized by start() or restart().
        """
