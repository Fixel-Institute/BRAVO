# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath('../Server/'))
sys.path.insert(0, os.path.abspath('../Server/Backend'))
sys.path.insert(0, os.path.abspath('../Server/modules'))
sys.path.insert(0, os.path.abspath('../Server/modules/python-scripts'))

jsdoc_config_path = './conf.json'

# Django Setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BRAVO.settings')
from BRAVO import asgi

# -- Project information -----------------------------------------------------

project = 'UF BRAVO Platform'
copyright = '2022, Jackson Cagle'
author = 'Jackson Cagle'

# The full version, including alpha/beta/rc tags
version = '2.0.0'
release = 'beta'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
  'sphinx_rtd_theme',
  'sphinx.ext.autodoc',
  'sphinx.ext.napoleon',
  'sphinx_js'
]
autodoc_member_order = 'bysource'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
#html_theme = 'alabaster'
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']