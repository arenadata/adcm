Actions on Cluster's Host
#########################

This spec is part of changes introduced in story ADCM-1508.

Main Use Case
=============

Iteraction with :term:`Product` in ADCM by :term:`End User` according to specification provided by :term:`Bundle Developer`.


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
* :term:`End User` know how to operate with :term:`Product`

Post-Conditions
---------------

* :term:`End User` was able to run some action provided by :term:`Bundle Developer` on one host included in cluster


“Used” Use Cases
----------------


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

User Interface
--------------

OnHost actions should be seen on the same UI elements as it was for regular actions.

.. warning:: TBD
   
Scenarios
---------

Component Action on Host
^^^^^^^^^^^^^^^^^^^^^^^^

1. :term:`Bundle Developer` adds action to a component like follows

.. code-block:: yaml

   - type: service
     name: My Supper Service
     version: "1.0"
     components:
        mycomponent:
          constraint: [0,+]
          actions:
            restart: 
                display_name: "Restart mycomponent"
                type: job
                script_type: ansible
                script: restart.yaml
                host_action: true
                states:
                    available: somestate

2. :term:`End User` installs cluster from this :term:`Bundle`
3. :term:`End User` adds service
4. :term:`End User` adds hosts
5. :term:`End User` places "mycomponnet" on a host
6. :term:`End User` sees the action "Restart mycomponent" on the host
7. :term:`End User` runs the action

Exceptions
~~~~~~~~~~

5. :term:`End User` chooses a host without mycomponent installed on it

   a. :term:`End User` sees no action "Restart mycomonent"
   b. The End

6. Component "mycomponent" is not in state "somestate"

   a. :term:`End User` sees no action "Restart mycomonent"
   b. The End

.. warning:: We need to be sure, there is no troubles with mixing states. It should react on component state only.


Service Action on Host
^^^^^^^^^^^^^^^^^^^^^^

1. :term:`Bundle Developer` adds action to a component like follows

.. code-block:: yaml

   - type: service
     name: My Supper Service
     version: "1.0"
     actions:
        restart: 
            display_name: "Restart service"
            type: job
            script_type: ansible
            script: restart.yaml
            host_action: true
            states:
                available: somestate
     components:
        mycomponent:
          constraint: [0,+]
     components:
        mycomponent2:
          constraint: [0,+]

2. :term:`End User` installs cluster from this :term:`Bundle`
3. :term:`End User` adds service
4. :term:`End User` adds hosts
5. :term:`End User` places "mycomponnet" or "mycomponent2" or both of them on a host
6. :term:`End User` sees the action "Restart service" on the host
7. :term:`End User` runs the action

Exceptions
~~~~~~~~~~

5. :term:`End User` chooses a host without "mycomponent" or "mycomponent2" installed on it.

   a. :term:`End User` sees no action "Restart service"
   b. The End

6. Service "My Supper Service" is not in state "somestate"

   a. :term:`End User` sees no action "Restart service"
   b. The End

.. warning:: We need to be sure, there is no troubles with mixing states. It should react on service state only.

Cluster Action on Host
^^^^^^^^^^^^^^^^^^^^^^

1. :term:`Bundle Developer` adds action to a component like follows

.. code-block:: yaml

   - type: cluster
     name: My Supper Cluster
     version: "1.0"
     actions:
        restart: 
            display_name: "Restart Application"
            type: job
            script_type: ansible
            script: restart.yaml
            host_action: true
            states:
                available: somestate
   - type: service
     name: My Supper Service
     version: "1.0"
     components:
        mycomponent:
          constraint: [0,+]
     components:
        mycomponent2:
          constraint: [0,+]

2. :term:`End User` installs cluster from this :term:`Bundle`
3. :term:`End User` adds service
4. :term:`End User` adds hosts
5. :term:`End User` sees the action "Restart Application" on the host
6. :term:`End User` runs the action

Exceptions
~~~~~~~~~~

5. Cluster "My Supper Cluster" is not in state "somestate"

   a. :term:`End User` sees no action "Restart Application"
   b. The End

.. warning:: We need to be sure, there is no troubles with mixing states. It should react on cluster state only.
