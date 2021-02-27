.. _action_onhost:

Actions on Cluster's Host
#########################

.. toctree::
   :maxdepth: 0
   :caption: Contents:
   :hidden:

   onhost/cluster_on_host.rst
   onhost/service_on_host.rst
   onhost/component_on_host.rst

This spec is part of changes introduced in story :issue:`ADCM-1620`.

Main idea of this case is execution of some actions defined in cluster bundle on one particular host. 


“Used” Use Cases
----------------

List of child cases which is a detalisation of this one:

* :ref:`action_onhost_cluster`
* :ref:`action_onhost_service`
* :ref:`action_onhost_component`


Actors
------

* :term:`End User`
* :term:`Bundle Developer`

User Value
----------

This functionality allow :term:`End User` to make operation with :term:`Product` on one particular host. For example:

* Start component
* Stop component
* Check application

Pre-Conditions
--------------

* :term:`End User` has ADCM with a :term:`Product` installed on some cluster

Post-Conditions
---------------

* :term:`End User` was able to run some action provided by :term:`Bundle Developer` on one host included in cluster


Flow of Events
--------------

#. :term:`Bundle Developer` adds an action to :term:`Product` with special mark parameter "host_action: true"
#. :term:`End User` goes to installed Cluster "Hosts" page
#. :term:`End User` see actions available for a host
#. :term:`End User` choose action provided by :term:`Bundle Developer`
#. Action executes:

   #. ADCM creates inventory with right context execution context (cluster/service/component)
   #. ADCM adds "target" group to inventory with the host choosed by :term:`End User`

.. note:: Take a note, that ADCM doesn't restrict :term:`Bundle Developer` with operation on one the host chossed by :term:`End User` only.
          ADCM just merely pass the ask to playbook over special group in inventory. It is :term:`Bundle Developer` responsibility to care about locality.
