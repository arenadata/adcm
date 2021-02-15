import os

SERVICE_VERSIONS = (
    ("service-less-equal", "2.2", "3.0"),
    ("service-greater-equal", "1.5", "2.2"),
    ("service-equal", "2.2", "2.2"),
    ("service-less", "2.3", "2.4"),
    ("service-greater", "1", "2"),
)

CLUSTER_VERSIONS = (
    ("cluster-less-equal", "1.6", "2.0"),
    ("cluster-greater-equal", "0.9", "1.6"),
    ("cluster-equal", "1.6", "1.6"),
    ("cluster-less", "1.7", "2.4"),
    ("cluster-greater", "0.5", "0.9"),
)

VARIABLES = [
    ("max", "min"),
    ("max_strict", "min_strict"),
    ("max_strict", "min"),
    ("max", "min_strict"),
]

TEMPLATE_SERVICE = """
-
    type: cluster
    name: ADH
    version: 1.6
    import:
       hadoop:
          versions:
             {0}: {2}
             {1}: {3}
       ADH:
          versions:
             min_strict: 0.1
             max_strict: 4.0

- type: service
  name: hadoop
  version: 2.2

  config:
     core-site:
        param1:
           type: string
           required: false
        param2:
           type: integer
           required: false
     quorum:
        type: integer
        default: 3
"""

TEMPLATE_CLUSTER = """
-
    type: cluster
    name: ADH
    version: 1.6
    import:
       hadoop:
          versions:
             min_strict: 1.5
             max_strict: 2.5
       ADH:
          versions:
             {0}: {2}
             {1}: {3}

- type: service
  name: hadoop
  version: 2.2

  config:
     core-site:
        param1:
           type: string
           required: false
        param2:
           type: integer
           required: false
     quorum:
        type: integer
        default: 3
"""

for t in SERVICE_VERSIONS:
    for variable in VARIABLES:
        d_name = "cluster_import_service_check_{}_{}/{}".format(
            variable[0], variable[1], t[0]
        )
        os.makedirs(d_name)
        with open("{}/config.yaml".format(d_name), "w+") as f:
            f.write(TEMPLATE_CLUSTER.format(variable[0], variable[1], t[1], t[2]))

for t in CLUSTER_VERSIONS:
    for variable in VARIABLES:
        d_name = "cluster_import_check_{}_{}/{}".format(variable[0], variable[1], t[0])
        os.makedirs(d_name)
        with open("{}/config.yaml".format(d_name), "w+") as f:
            f.write(TEMPLATE_CLUSTER.format(variable[0], variable[1], t[1], t[2]))
