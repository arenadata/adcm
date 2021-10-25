Objects
=======

.. _object-config:

Config
~~~~~~

ObjectConfig is an object that contains the ID of the current and previous config

Endpoint: */config*

=================== ======= ======= ======== ================ ================== ================== ===========
Name                Type    Default Nullable :term:`Required` :term:`POSTable`   :term:`Changeable` Description
=================== ======= ======= ======== ================ ================== ================== ===========
id                  integer auto    False    False            False              False              Object id.
current             FK      null    False    False            False              False              FK on `ConfigLog` object
previous            FK      null    False    False            False              False              FK on `ConfigLog` object
history             link    null    False    False            False              False              Link on list `ConfigLog` object for this object
url                 link    null    False    False            False              False              Reference to this object
=================== ======= ======= ======== ================ ================== ================== ===========

API Calls Allowed
^^^^^^^^^^^^^^^^^

============= =======
Operation     Allowed
============= =======
GET           True
LIST          True
POST          False
PUT           False
PATCH         False
DELETE        False
============= =======

.. _object-config-log:

Config Log
~~~~~~~~~~

ObjectLog is an object that contains object configurations

Endpoint: */config-log*

=================== ======= ======= ======== ================ ================== ================== ===========
Name                Type    Default Nullable :term:`Required` :term:`POSTable`   :term:`Changeable` Description
=================== ======= ======= ======== ================ ================== ================== ===========
id                  integer auto    False    False            False              False              Object id.
date                date    auto    False    False            False              False              Object creation date
obj_ref             FK      null    False    True             True               False              FK on `ObjectConfig` object
description         text    ''      False    False            True               False              Description
config              json    {}      False    True             True               False              Configuration
attr                json    {}      False    False            True               False              Additional attributes
url                 link    null    False    False            False              False              Reference to this object
=================== ======= ======= ======== ================ ================== ================== ===========

API Calls Allowed
^^^^^^^^^^^^^^^^^

============= =======
Operation     Allowed
============= =======
GET           True
LIST          True
POST          True
PUT           False
PATCH         False
DELETE        False
============= =======

.. _object-group-config:

Group Config
~~~~~~~~~~~~

Group is an entity wich is capable to hold some number of host in it and connect it to some objects. Besides the group allow to pin a subset of object config and provide a way to change the config.

Endpoint: */group-config*

=================== ======= ======= ======== ================ ================== ================== ===========
Name                Type    Default Nullable :term:`Required` :term:`POSTable`   :term:`Changeable` Description
=================== ======= ======= ======== ================ ================== ================== ===========
id                  integer auto    False    False            False              False              Object id.
object_id           integer null    False    True             True               False              Object id for object
object_type         string  null    False    True             True               False              Object type (`cluster`, `service`, `component`, `provider`)
name                string  null    False    True             True               True               Name of object.
description         text    null    False    False            True               True               Extended information provided by user.
hosts               link    null    False    False            False              False              Reference to list `Host` objects.
host_candidate      link    null    False    False            False              False              Reference to list host candidate for adding to a group
config              link    null    True     False            False              False              Reference to `ObjectConfig` object
config_id           integer null    False    False            False              False              Additional information about config. Read Only.
url                 link    null    False    False            False              False              Reference to this object
=================== ======= ======= ======== ================ ================== ================== ===========


API Calls Allowed
^^^^^^^^^^^^^^^^^

============= =======
Operation     Allowed
============= =======
GET           True
LIST          True
POST          True
PUT           True
PATCH         True
DELETE        True
============= =======

.. _object-group-config-hosts:

Group Config Hosts
~~~~~~~~~~~~

Endpoint: */group-config/<id>/host/*

=================== ======= ======= ======== ================ ================== ================== ===========
Name                Type    Default Nullable :term:`Required` :term:`POSTable`   :term:`Changeable` Description
=================== ======= ======= ======== ================ ================== ================== ===========
id                  integer auto    False    True             True               False              Object ID.
cluster_id          integer null    False    False            False              False              Cluster object ID
prototype_id        integer null    False    False            False              False              Prototype object ID
provider_id         integer null    False    False            False              False              Provider object ID
fqdn                string  null    False    False            False              False              FQDN host
description         text    null    False    False            False              False              Host description
state               string  null    False    False            False              False              Host state
url                 link    null    False    False            False              False              Reference to this object
=================== ======= ======= ======== ================ ================== ================== ===========

.. note::
    POST - Creating relation a host with a group
    DELETE - Deleting relation a host with a group


API Calls Allowed
^^^^^^^^^^^^^^^^^

============= =======
Operation     Allowed
============= =======
GET           True
LIST          True
POST          True
PUT           False
PATCH         False
DELETE        True
============= =======

.. _object-group-config-host-candidate:

Group Config Host Candidate
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Endpoint: */group-config/<id>/host-candidate/*

=================== ======= ======= ======== ================ ================== ================== ===========
Name                Type    Default Nullable :term:`Required` :term:`POSTable`   :term:`Changeable` Description
=================== ======= ======= ======== ================ ================== ================== ===========
id                  integer auto    False    True             True               False              Object ID.
cluster_id          integer null    False    False            False              False              Cluster object ID
prototype_id        integer null    False    False            False              False              Prototype object ID
provider_id         integer null    False    False            False              False              Provider object ID
fqdn                string  null    False    False            False              False              FQDN host
description         text    null    False    False            False              False              Host description
state               string  null    False    False            False              False              Host state
url                 link    null    False    False            False              False              Reference to this object
=================== ======= ======= ======== ================ ================== ================== ===========

API Calls Allowed
^^^^^^^^^^^^^^^^^

============= =======
Operation     Allowed
============= =======
GET           True
LIST          True
POST          False
PUT           False
PATCH         False
DELETE        False
============= =======
