#!/usr/bin/env python3
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

import os
import sys
import signal
import logging
import argparse

import adcm.init_django  # noqa: F401, isort:skip

from application.di.containers import get_main_providers
from core.legacy.job.runners import JobFilterPredicate, TaskRunner, always_true, non_success
import dishka


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["start", "restart"])
    parser.add_argument("task_id", type=int)
    args = parser.parse_args()

    container_context = {JobFilterPredicate: non_success if args.command == "restart" else always_true}

    container = dishka.make_container(*get_main_providers(), context=container_context)

    with container():
        runner = container.get(TaskRunner)

    logger = logging.getLogger("task-runner")

    exit_ = {"code": 0}

    def terminate(signum, frame):
        _ = frame

        logger.info(f"Cancelling runner at {os.getpid()} with {signum}")

        exit_["code"] = signum
        try:
            runner.terminate()
        except:  # noqa: E722
            logger.exception("Unhandled error occurred during runner termination")

            runner.consider_broken()

            exit_["code"] = 1

    signal.signal(signal.SIGTERM, terminate)

    try:
        runner.run(task_id=args.task_id)
    except:  # noqa: E722
        logger.exception("Unhandled error occurred during runner execution")

        runner.consider_broken()

        exit_["code"] = 1

    sys.exit(exit_["code"])


if __name__ == "__main__":
    main()
