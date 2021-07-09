#########
Use Cases
#########

.. _ui_usecases_login:

*****
Login
*****

There is a number of scenarios related to login forms of ADCM.

.. note::
   Upgrade of ADCM and related events is out of scope for this use case.

User/password login
===================

Just a simple use case of auth for user with username and password.

**Goal**: successful login

1. Go to ADCM
2. Fill *Login* on :ref:`ui_elements_forms_login`
3. Fill *Password* on :ref:`ui_elements_forms_login`
4. Press button *Login* on :ref:`ui_elements_forms_login`

Exceptions:

2. User already logged to ADCM
    a. There is no :ref:`ui_elements_forms_login`

2. User does not fill *Login* on :ref:`ui_elements_forms_login`
    a. Button *Login* on :ref:`ui_elements_forms_login` is inactive (no way to click it)


2. User does not fill *Password* on :ref:`ui_elements_forms_login`
    a. Button *Login* on :ref:`ui_elements_forms_login` is inactive (no way to click it)


GAuth2 login
============

.. note::
   TODO: Add later as separate story.

.. _ui_usecases_cluster_list_view:

*******
Cluster
*******

Cluster list view
=================

Use case in which the user can view the list of added clusters and information on them.

Actors
------

* :term:`End User`

User Value
----------

This use case will allow the :term:`End User` to view the list of added clusters.

Pre-Conditions
--------------

:term:`End User` has ADCM and completed the use case :ref:`ui_usecases_login`.

Post-Conditions
---------------

:term:`End User` was able to view the list of clusters and information on them.

“Used” Use Cases
----------------

* :ref:`ui_usecases_cluster_service_list_view`

Flow of Events
--------------

1. :term:`End User` goes to the "Cluster" tab of the main menu of the :ref:`ui_templates_common` template.
2. :term:`End User` sees a list of clusters and information on them.

User Interface
--------------

The description of the UI is available by clicking :ref:`ui_templates_clusters`.

.. _ui_usecases_cluster_service_list_view:

Cluster service list view
=========================

Use case in which the user can view the list of added clusters and information on them.

Actors
------

* :term:`End User`

User Value
----------

This use case will allow the :term:`End User` view the list of services included to cluster.

Pre-Conditions
--------------

:term:`End User` has ADCM and completed the following use cases:

* :ref:`ui_usecases_login`
* :ref:`ui_usecases_cluster_list_view`

Post-Conditions
---------------

:term:`End User` was able to view the list of cluster services and information on them.

“Used” Use Cases
----------------

Flow of Events
--------------

1. :term:`End User` selects the required cluster by clicking on it in the list of clusters.
2. :term:`End User` goes to the "Services" section in the left menu.
3. :term:`End User` sees a list of cluster services and information on them.

User Interface
--------------

The description of the UI is available by clicking :ref:`ui_templates_cluster-services`.
