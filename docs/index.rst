.. UF BRAVO Platform documentation master file, created by
   sphinx-quickstart on Tue Dec  6 08:39:32 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to UF BRAVO Platform's documentation!
=============================================

University of Florida Brain Recording Analysis and Visualization Online (BRAVO) Platform
is a Python-based data analysis tool for processing and analyzing session data collected with 
sensing-enabled neurostimulators such as Medtronic Percept neurostimulator.

.. note::

  This is a Sphinx Documentation with Readthedocs Template hosted by Cloudflare to avoid advertisement showing up on the page.
  
  This documentation will be updated slowly because the BRAVO Platform currently is still a side-project started on my free time at work
  and I am not funded for this project. 

.. toctree::
   :maxdepth: 1
   :caption: Getting Started

   installation.rst
   tutorials.rst 
   usage.rst

.. toctree::
   :maxdepth: 1
   :caption: Change Logs

   ChangeLogs/v2.0.0.rst

Developer Documentation
=============================================
.. toctree::
   :maxdepth: 1
   :caption: Javascript

   JavascriptModules/PlotlyWrapper.rst

.. toctree::
   :maxdepth: 1
   :caption: Python

   PythonModules/PerceptDecoder.rst
   PythonModules/BackendAPIs.rst
