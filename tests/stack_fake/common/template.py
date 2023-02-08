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

# Since this module is beyond QA responsibility we will not fix docstrings here
# pylint: disable=missing-function-docstring, missing-class-docstring, missing-module-docstring

import json
import os
import sys

from jinja2 import Template


def render(template_file_name, context):
    try:
        with open(template_file_name, encoding="utf_8") as file:
            tmpl = Template(file.read())
    except FileNotFoundError:
        print(f"Can't open template file: '{template_file_name}'")
        sys.exit(2)
    return tmpl.render(c=context)


def render_to_file(template_file_name, out_file_name, context):
    try:
        with open(out_file_name, "w", encoding="utf_8") as file:
            file.write(render(template_file_name, context))
    except FileNotFoundError:
        print(f"Can't open output file: '{out_file_name}'")
        sys.exit(2)


def read_json(json_file_name):
    try:
        with open(json_file_name, encoding="utf_8") as file:
            config = json.load(file)
    except FileNotFoundError:
        print(f"Can't open json config file: '{json_file_name}'")
        sys.exit(2)
    return config


def template(tmpl, out_file, config):
    json_conf = read_json(config)
    render_to_file(tmpl, out_file, json_conf)


def main():
    if len(sys.argv) < 4:
        print(f"\nUsage:\n{os.path.basename(sys.argv[0])} template out_file config.json\n")
        sys.exit(4)
    else:
        template(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
