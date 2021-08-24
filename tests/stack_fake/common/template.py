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
import json
from jinja2 import Template


def render(template_file_name, context):
    try:
        fd = open(template_file_name, encoding='utf_8')
    except FileNotFoundError:
        print("Can't open template file: '{}'".format(template_file_name))
        sys.exit(2)
    tmpl = Template(fd.read())
    fd.close()
    return tmpl.render(c=context)


def render_to_file(template_file_name, out_file_name, context):
    try:
        fd = open(out_file_name, 'w', encoding='utf_8')
    except FileNotFoundError:
        print("Can't open output file: '{}'".format(out_file_name))
        sys.exit(2)
    fd.write(render(template_file_name, context))
    fd.close()


def read_json(json_file_name):
    try:
        fd = open(json_file_name, encoding='utf_8')
    except FileNotFoundError:
        print("Can't open json config file: '{}'".format(json_file_name))
        sys.exit(2)
    config = json.load(fd)
    fd.close()
    return config


def template(tmpl, out_file, config):
    json_conf = read_json(config)
    render_to_file(tmpl, out_file, json_conf)


def do():
    if len(sys.argv) < 4:
        print("\nUsage:\n{} template out_file config.json\n".format(os.path.basename(sys.argv[0])))
        sys.exit(4)
    else:
        template(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == '__main__':
    do()
