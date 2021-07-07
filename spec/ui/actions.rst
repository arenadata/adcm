Use Cases
#########

Login
=====

There is a number of scenarios related to login forms of ADCM.

.. note::
   Upgrade of ADCM and related events is out of scope for this use case.

User/password login
-------------------

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
------------

.. note::
   TODO: Add later as separate story.

