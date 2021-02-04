import os

template = """
- type: cluster
  name: password_confirm_{0}_required_{1}
  version: 1
  config:
  - name: password
    type: password
    required: {1}
    ui_options:
      no_confirm: {0}
"""


for config in [(confirm, required) for confirm in
               ("true", "false") for required in ("true", "false")]:
    d_name = "password_confirm_{0}_required_{1}/".format(
        config[0], config[1])
    os.makedirs(d_name)
    with open("{}/config.yaml".format(d_name), "w+") as f:
        f.write(template.format(config[0], config[1]))
