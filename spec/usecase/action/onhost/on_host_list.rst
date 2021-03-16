.. _action_onhost_api_host_only:

API Listing Details
###################

For any :term:`On Host Action` no matter which of type (cluster/service/component) action is not shown in cluster/service/component's action list but shown host's action list. 

There is no proper way to get information of host from API call if it was done on cluster/service/component endpoint. And there is no story about running :term:`On Host Action` as a regular action.

“Used” Use Cases
----------------

The information provided in this case is in the cases below, but this case detalises this explicity to be sure it will be tested.

* :ref:`action_onhost_cluster`
* :ref:`action_onhost_service`
* :ref:`action_onhost_component`
* :ref:`action_onhost_target`

User Value
----------

No user value at all. It is a stab use case which prevent us from error.

Actors
------

* :term:`End User`
* :term:`Bundle Developer`

Pre-Condition
-------------

* :term:`End User` has ADCM with a :term:`Product` installed on some cluster

Flow of Events
--------------

#. :term:`Bundle Developer` adds an action to :term:`Product` with special mark parameter "host_action: true" on cluster/service/component
#. :term:`End User` goes to installed Cluster "Hosts" page
#. :term:`End User` see the actions marked by :term:`Bundle Developer` as an :term:`On Host Action`
#. :term:`End User` goes to action list of cluster/service/component
#. :term:`End User` see no actions marked by :term:`Bundle Developer` as an :term:`On Host Action`

