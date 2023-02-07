.. _3dRendererTutorial:

Online 3D Renderer Documentation
===============================================

Overview
---------------------------------------------
The online 3D renderer are a collection of functions created to generate 3D brain scene for electrode/targeting rendering. 
The method documentations may not be clear as to what is available in the Online 3D Renderer, primarily because not 
every capability is written into a function and organized into a Javascript Class like PlotlyWrapper. 

In this section, I will document the workflow of how the 3D renderer works. 

Step 1 - Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The 3D scene is made of background and lighting system. Most environmental components are added 
in the scene statically in Canvas component of the ImageVisualization Page. 

By default, 2 hemisphereLight were added at positive and negative Y position. 2 directional shadowLight 
are added at (-X,-Y,-Z) and (+X,+Y,+Z) position. Location, distance, and color of the light 
can be adjusted based on your need programmatically but not dynamically at the moment. 

The :js:func:`CameraController` is a wrapper for OrbitControls object. This is the most common 
control system for imaging related views. There are many other control available and you should choose 
what fit best for your use case (`examples <https://threejs.org/examples/?q=control>`_).

Step 2 - Available Models Retrival
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The 3D renderer's first step is to query available image models through :meth:`APIs.Queries.QueryImageModelDirectory` API.
The API will return a dictionary that defines the available models and pre-loaded models. An example of a typical 
return will looks like the following:

.. code-block:: json

  {
    "descriptor": {
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
        "entryPoint": [20,40,50]
      }
    },
    "availableModels": [
      {
        "file": "CL_L.pts",
        "type": "points",
        "mode": "single"
      },
      {
        "file": "CL_R.pts",
        "type": "points",
        "mode": "single"
      },
      {
        "file": "LEFT_CM_11.stl",
        "type": "stl",
        "mode": "single"
      },
      {
        "file": "RIGHT_CM_11.stl",
        "type": "stl",
        "mode": "single"
      },
      {
        "file": "lh_FLAIR_pial.stl",
        "type": "stl",
        "mode": "single"
      },
      {
        "file": "Medtronic_B33015",
        "type": "electrode",
        "mode": "multiple"
      }
    ]
  }

The ``descriptor`` dictionary define a list of image models that should be pre-loaded in the 3D brain scene initially. 
The ``availableModels`` list define a list of image models available in the patient imaging folder. 

Step 3 - Load Image Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To load image not pre-loaded, user may use :js:func:`retrieveModels` function from callbacks. 
This will initiate :meth:`APIs.Queries.QueryImageModel` API and retrieve the raw data from server. 

Once the raw data is retrieved, the frontend will attempt to turn the model into usable Three.js component using
combination of React-Three-Fiber wrapper and raw Three.js functions. Three.js is one of the most popular
javascript library for 3D computer graphics using WebGL. Checkout their library of demos to see what you can 
do with Three.js at `Example Page <https://threejs.org/examples/>`_. 

Our renderer tap into the Three.js functionality to generate 3D STL models as a simple `3D mesh <https://threejs.org/docs/index.html?q=mesh#api/en/objects/Mesh>`_ with 
`bufferGeometry <https://threejs.org/docs/index.html?q=bufferGeometry#api/en/core/BufferGeometry>`_ using the :js:func:`Model` function. 

Similarly, a tractography object is Three.js line object with connected points using `Line object <https://threejs.org/docs/index.html?q=line#api/en/objects/Line>`_ with 
`bufferGeometry <https://threejs.org/docs/index.html?q=bufferGeometry#api/en/core/BufferGeometry>`_ using the :js:func:`Tractography` function. 

Step 4 - Model Transformation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Patient specific models usually require 3D transformation to fit patient's brain space. 
Since STL object itself contain X-Y-Z coordinate of the vertices, these models doesn't 
require transformation at the renderer level. In addition, STL models don't usually changes 
as often, and if it did change it will more likely to be a nonlinear transformation. Such changes
are easier to be generated on the server side instead of on the renderer side. 

The only model that currently allow dynamic regeneration is "Electrode" model. 
The :js:func:`computeElectrodePlacement` function will take in a target point and an entry point 
to generate a linear affined 3D matrix to be applied to the electrode model to dynamically adjust 
display. This function is in place because users can attempt different targeting trajectory to observe 
electrode's position and relationship to other tracts or atlases. 

The math behind :js:func:`computeElectrodePlacement` is simple. We compute directional vector 
from target point to entry point, this is our K-vector. Then we compute a random point in space to form a temporary line,
cross product between temporary vector and K-vector will provide an orthogonal vector to K-vector, which is later 
named as I-vector. Cross product between I-vector and K-vector will produce 3rd orthogonal vector, the J-vector. 
Utilizing the I-J-K vector with origin, we can compute affine 3D transformation by performing inverse multiplication 
between I-J-K vector and original I-J-K vector from model. 

Methods
---------------------------------------------
.. js:autofunction:: retrieveModels

.. js:autofunction:: parseBinarySTL

.. js:autofunction:: identityMatrix

.. js:autofunction:: computeElectrodePlacement

.. js:autofunction:: rgbaToHex

Renderer Components
---------------------------------------------
.. js:autofunction:: Model

.. js:autofunction:: Tractography

.. js:autofunction:: CameraController