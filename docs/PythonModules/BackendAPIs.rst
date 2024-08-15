Backend API Requests Documentation
=============================================

Overview
---------------------------------------------
The backend APIs are a series of available REST API endpoints that developer may interface with for data queries.
The knowledge about these endpoints are not required by average users, since all the request and communications are hidden from users.
However, these will likely come in handy for people who want to modify the backend or develope their own frontend pipelines.

There are many modules among the backend APIs, which can be divided based on functionalities. 


1. `Authentication Module`_ for User (Research/Admin/Mobile) related actions.
2. `Queries Module`_ for requesting data from database.
3. `SQL Database Update Module`_ for changing patient/device information in database.
4. `Upload Module`_ for handling file uploads from user.
5. `Survey Module`_ for handling online-survey related changes. This is non-neurostimulator specific module. 

Authentication Module
---------------------------------------------
The Authentication Module file contain all routes that handles account creation and authentication.
Most functions are wrapper around the `Django REST Knox <https://james1345.github.io/django-rest-knox/>`_ library that 
performs Authentication Token management.

.. automodule:: APIs.Auth
    :members: 

Queries Module
---------------------------------------------
The Queries Module file contain all routes called by React Frontend to request data for display.
These functions are mostly top-level wrappers that call low-level computation and processing scripts outlined in other documentation.

All Queries require UserAuthentication in request, indicating that if a request is made without Authentication Token will be automatically rejected. 
Therefore, ``NotAuthenticated`` error will not be discussed in each function but implied. 

All Queries will be subjected to a simple "Access Verification" function that determine what data the user has access to. 
Currently only 3 tier of access control is added: 

1. Tier 0 = Not Accessible 
2. Tier 1 = Owner Access (You uploaded the data or that you are Admin/Clinician account)
3. Tier 2 = Permissible Access (You didn't upload the data but an Admin has granted you access through Admin Panel).

.. automodule:: APIs.Queries
    :members: 

SQL Database Update Module
---------------------------------------------

.. warning:: 

  Hidden - Under Revision

Upload Module
---------------------------------------------

.. warning:: 

  Hidden - Under Revision

Survey Module
---------------------------------------------

.. warning:: 

  Hidden - Under Revision
