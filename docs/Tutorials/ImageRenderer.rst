3D Image Visualization Toolkit
=========================================

Overview
-----------------------------------------

The BRAVO Platform v2.0.0-alpha introduce the preliminary image visualization pipeline. 
The image visualization pipeline is built based on a side project that intend to create an openly accessible 
3D image renderer on a browser. The original project and complete standalone application can be found at 
`ImageVisualization3D Github Repo <https://github.com/Fixel-Institute/ImageVisualization3D>`_. The detail demo 
and description can be found at README.md in the repository. 

.. admonition:: Roadmap

  The capability is expected to be more mature by v2.1.0 as it is one of the main capabilities to be worked on for v2.1.0

Data Structure
-------------------------------------------

The Imaging database for UF BRAVO Platform follows the same trend as time-domain recordings from Percept. However,
instead of dividing the data by neurostimulator deidentifier, the imaging folder is divided by patient deidentifier. 
All data should be stored in ``$DATASERVER_PATH/imaging`` directory, where $DATASERVER_PATH is the environment variable that 
define the storage path for UF BRAVO Platform in Django Server. 

The ``$DATASERVER_PATH/imaging`` directory should contain an "Electrodes" folder, which contain subfolders of electrode-specific STL models. 
For example, the Medtronic SenSight 1.5mm Segmented Lead can have three STL that made up its primary body: `contacts.stl`, `shaft.stl`, and `marker.stl`.
They should be placed on a path as ``$DATASERVER_PATH/imaging/Electrodes/Medtronic_B33015/*.stl`` etc. 

Other patient-specific STLs should be stored in ``$DATASERVER_PATH/$PATIENT_ID/*.stl``. A specific ``renderer.json`` file 
can be created manually to allow website to automatically preload STLs when viewed. 

renderer.json 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The **renderer.json** has the following structure: 

The file is of dictionary type, where the key of the dictionary is the STL file to be pre-loaded. 
The value for each STL key is another dictionary that describe pre-load conditions such as surface colors. 

Electrode can also be pre-loaded by supplying electrode name (subfolder in Electrodes directory) as a key. 
For electrodes, 2 keys are required to properly adjust the electrode: ``targetPoint`` and ``entryPoint``. 
The targetPoint is the coordinate at which the tip of the electrode should go, and entryPoint can be anywhere along 
the path of the electrode, as the software will only use it to compute directional vector for transformation. 

.. code-block:: json

   {
      "LEFT_CM_11.stl": {
        "color": "#FFFF00"
      },
      "RIGHT_CM_11.stl": {
        "color": "#FF0000"
      },
      "lh_FLAIR_pial.stl": {
        "color": "#FFFFFF"
      },
      "Medtronic_B33015": {
        "color": "#0000FF",
        "targetPoint": [0,20,0],
        "entryPoint": [0,40,50]
      }
  }

.. admonition:: TODO

  Currently, the electrode does not offer proper rotation using simply 2 points. A rotational parameter will be added in
  the future. 

Supported Format
-------------------------------------------

There are only a few supporting formats at the moment, but more will be added in the future if requested. 

Binary STL (.stl)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The most common model currently used is a binary STL data type. A simple Binary STL parser is written in Javascript to extract
faces and vertices. You may extract STL from patient-specific atlases. 

Tractography (.tck, .pts and .edge)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The tractography data can be rendered as line objects. Currently, the Python backend can process MRTRIX's TCK file format
and SCIRun's Point/Edge file format. If other format is desired, the easiest way is to write customized loader. 

Volumetric NifTi (.nii or .nii.gz)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

NifTi format file can also be rendered as 3-axis slices. Currently it support standard NifTi for T1 or T2, as long as the 3D 
matrix is ordered as X-Y-Z and higher index correlate with more positive position. 

.. admonition:: TODO

  There are still much to be desired of the NifTi loader, mainly because how the 3D matrix is being handled and cached. 
  The loading process is lazy and essentially keep all data in the browser. This increase data rate and potentially making 
  individual computer slower. 

  Second, the Three.js volumetric rendering is based on simple slice geometry, which means that NifTi isn't the only format supported.
  The goal is to create different "loaders" in Python backend and process different file type into the same structure to be rendered. 
