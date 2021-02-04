import os


integers = [(0, 0, 0, 'nulls'), (-10, 5, 0, 'positive_and_negative'),
            (0, 10, 10, "positive_and_null"), (-10, -1, -2, "negative"),
            (1, 10, 5, "positive")]
floats = [(0.0, 0.0, 0.0, 'nulls'), (-10.5, 0.2, 0.1, 'positive_and_negative'),
          (0, 10.5, 2.5, "positive_and_null"), (-10.3, -1.4444, -2.234, "negative"),
          (1.1, 20.2, 5.5, "positive")]
float_template = """
- type: cluster
  name: numbers_test
  version: 1
  config:
    - name: numbers_test
      type: float
      required: true
      min: {0}
      max: {1}
      default: {2}
"""
integer_template = """
- type: cluster
  name: numbers_test
  version: 1
  config:
    - name: numbers_test
      type: integer
      required: true
      min: {0}
      max: {1}
      default: {2}
"""

for fl in floats:
    d_name = "bundles/{}".format("float-{}".format(fl[3]))
    os.makedirs(d_name)
    with open("{}/config.yaml".format(d_name), "w+") as f:
        f.write(float_template.format(fl[0], fl[1], fl[2]))

for i in integers:
    d_name = "bundles/{}".format("integer-{}".format(i[3]))
    os.makedirs(d_name)
    with open("{}/config.yaml".format(d_name), "w+") as f:
        f.write(integer_template.format(i[0], i[1], i[2]))
