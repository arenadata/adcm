import os

DATA = [("invisible", "true", "advanced", "true"),
        ("invisible", "false", "advanced", "false"),
        ("invisible", "false", "advanced", "true"),
        ('invisible', "true", "advanced", "false")]
TYPES = ("string", "password", "integer", "text", 'boolean',
         'float', 'option', 'list', 'map', 'json', 'file')
template_textboxes = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      default: {4}
      ui_options:
         {0}: {1}
         {2}: {3}
"""

template_password = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      default: password
      ui_options:
         {0}: {1}
         {2}: {3}
"""

template_text = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      default: text
      ui_options:
         {0}: {1}
         {2}: {3}
"""

template_numbers = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      default: 1
      ui_options:
         {0}: {1}
         {2}: {3}
"""

template_boolean = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      default: true
      ui_options:
         {0}: {1}
         {2}: {3}
"""

template_file = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      ui_options:
         {0}: {1}
         {2}: {3}
"""

template_json = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      default: {{}}
      ui_options:
         {0}: {1}
         {2}: {3}
"""
template_map = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      default:
        name: Joe
        age: "24"
        sex: m
      ui_options:
         {0}: {1}
         {2}: {3}
"""

template_list = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      default:
        - /dev/rdisk0s1
        - /dev/rdisk0s2
        - /dev/rdisk0s3
      ui_options:
         {0}: {1}
         {2}: {3}
"""

template_option = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      option: {{http: 80, https: 443}}
      default: 80
      ui_options:
         {0}: {1}
         {2}: {3}
"""
TEMPLATES = {"string": template_textboxes, "password": template_password,
             "integer": template_numbers, "text": template_text,
             'boolean': template_boolean, 'float': template_numbers,
             'option': template_option, 'list': template_list, 'map': template_map,
             'json': template_json, 'file': template_file}


for t in TYPES:
    for config in DATA:
        d_name = "{}_{}/{}_{}/{}".format(config[0], config[1], config[2], config[3], t)
        os.makedirs(d_name)
        tmpl = ''
        with open("{}/config.yaml".format(d_name), "w+") as f:
            f.write(TEMPLATES[t].format(config[0], config[1], config[2], config[3], t))
