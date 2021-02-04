import os


VARIABLES = [("less-equal", "2.2", "3.0", 'max', 'min', "2.1"),
             ("less-equal", "2.2", "3.0", 'max', 'min_strict', "2.2"),
             ("greater-equal", "2.2", "3.0", 'max', 'min', "3.1"),
             ("greater-equal", "2.2", "3.0", 'max_strict', 'min', "3.0"),
             ("equal", "2.2", "3.0", 'max_strict', 'min_strict', "2.2"),
             ("equal", "2.2", "3.0", 'max_strict', 'min', "3.0"),
             ("less", "2.2", "3.0", 'max', 'min', "2.1"),
             ("less", "2.2", "3.0", 'max', 'min_strict', "2.2"),
             ("greater", "2.2", "3.0", 'max', 'min', "3.1"),
             ("greater", "2.2", "3.0", 'max_strict', 'min_strict', "3.0")
             ]


TEMPLATE_SERVICE = """
-
    type: cluster
    name: ADH
    version: 1.6
    import:
       hadoop:
          versions:
             {2}: {1}
             {3}: {0}
       ADH:
          versions:
             min_strict: 0.1
             max_strict: 4.0

- type: service
  name: hadoop
  version: {4}

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
    version: {4}
    import:
       hadoop:
          versions:
             min_strict: 1.5
             max_strict: 2.5
       ADH:
          versions:
             {2}: {1}
             {3}: {0}

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

for variable in VARIABLES:
    d_name = "service_import_check_negative/{}_{}_{}".format(
        variable[0], variable[3], variable[4]
    )
    os.makedirs(d_name)
    with open("{}/config.yaml".format(d_name), "w+") as f:
        f.write(TEMPLATE_SERVICE.format(variable[1], variable[2],
                                        variable[3], variable[4],
                                        variable[5]))

for variable in VARIABLES:
    d_name = "cluster_import_check_negative/{}_{}_{}".format(variable[0],
                                                             variable[3],
                                                             variable[4])
    os.makedirs(d_name)
    with open("{}/config.yaml".format(d_name), "w+") as f:
        f.write(TEMPLATE_CLUSTER.format(variable[1], variable[2],
                                        variable[3], variable[4],
                                        variable[5]))
