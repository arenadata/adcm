import os

SERVICE_VERSIONS = (("service-less-equal", "2.1", "3.0"),
                    ("service-greater-equal", "1.5", "2.1"),
                    ("service-equal", "2.1", '2.1'),
                    ('service-less', '2.2', '2.4'),
                    ("service-greater", '1', '2'))

CLUSTER_VERSIONS = (("cluster-less-equal", "1.0", "2.0"),
                    ("cluster-greater-equal", "0.9", "1.0"),
                    ("cluster-equal", "1.0", '1.0'),
                    ('cluster-less', '1.1', '2.4'),
                    ("cluster-greater", '0.5', '0.9'))
TEMPLATE_SERVICE = """
-
    type: cluster
    name: ADH
    version: 1.6
    upgrade:
      - versions:
          min: 0.4
          max: 1.5
        name: upgrade to 1.6
        description: New cool upgrade
        states:
          available: any
          on_success: upgradable
      - versions:
          min: 1.0
          max: 1.8
        description: Super new upgrade
        name: upgrade 2
        states:
          available: [created, installed, upgradable]
          on_success: upgradated
    import:
       hadoop:
          versions:
             min_strict: {0}
             max_strict: {1}
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
    upgrade:
      - versions:
          min: 0.4
          max: 1.5
        name: upgrade to 1.6
        description: New cool upgrade
        states:
          available: any
          on_success: upgradable
      - versions:
          min: 1.0
          max: 1.8
        description: Super new upgrade
        name: upgrade 2
        states:
          available: [created, installed, upgradable]
          on_success: upgradated
    import:
       hadoop:
          versions:
             min_strict: 1.5
             max_strict: 2.5
       ADH:
          versions:
             min_strict: {0}
             max_strict: {1}

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
    d_name = "upgradable_cluster_with_strict_incorrect_version/{}".format(t[0])
    os.makedirs(d_name)
    with open("{}/config.yaml".format(d_name), "w+") as f:
        f.write(TEMPLATE_SERVICE.format(t[1], t[2]))

for t in CLUSTER_VERSIONS:
    d_name = "upgradable_cluster_with_strict_incorrect_version/{}".format(t[0])
    os.makedirs(d_name)
    with open("{}/config.yaml".format(d_name), "w+") as f:
        f.write(TEMPLATE_CLUSTER.format(t[1], t[2]))
