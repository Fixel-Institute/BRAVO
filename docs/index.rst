.. UF BRAVO Platform documentation master file, created by
   sphinx-quickstart on Tue Dec  6 08:39:32 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to UF BRAVO Platform's documentation!
=============================================

University of Florida Brain Recording Analysis and Visualization Online (BRAVO) Platform
is a Python-based data analysis tool for processing and analyzing session data collected with 
sensing-enabled neurostimulators.

The University of Florida is solely responsible for the Bravo Platform. 
The Bravo Platform is for research use only. 
The Bravo Platform was created and is maintained without any involvement, evaluation, or endorsement by any third-party medical device company.
The BRAVO Platform may contain device name or electrode name trademarked by third party medical device company but only for the purpose of differentiating different devices.  

Please refer to `GitHub Repository <https://github.com/Fixel-Institute/BRAVO>`_ to submit feature requests.

Please refer to :ref:`bravoWearableApp` for tutorials regarding Mobile Companion App.

.. toctree::
   :maxdepth: 1
   :caption: Getting Started

   installation.rst
   usage.rst
   tutorials.rst 
   previous_builds.rst 

.. toctree::
   :maxdepth: 1
   :caption: Change Logs

   ChangeLogs/v2.2.0.rst
   ChangeLogs/v2.1.1.rst
   ChangeLogs/v2.1.0.rst
   ChangeLogs/v2.0.0.rst

Developer Documentation
=============================================
.. toctree::
   :maxdepth: 1
   :caption: Python

   PythonModules/PerceptDecoder.rst
   PythonModules/BackendAPIs.rst

   PythonModules/Therapy.rst
   PythonModules/AverageNeuralActivity.rst
   PythonModules/NeuralActivityStreaming.rst
   PythonModules/MultiChannelActivity.rst
   PythonModules/ChronicNeuralActivity.rst

   PythonModules/ImageDatabase.rst

.. toctree::
   :maxdepth: 1
   :caption: Javascript

   JavascriptModules/PlotlyWrapper.rst
   JavascriptModules/OnlineRenderer.rst
   JavascriptModules/Language.rst

