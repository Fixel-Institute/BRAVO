Installation Procedures
=============================================

The UF BRAVO P1latform consist of 2 main components: *Python Server* and *React Frontend*. 
These two components can communicate through both Websocket and REST APIs, 
supported by Django Channels [1]_ and Django REST Framework [2]_. 

The documentation will walk through installation of both components; 
however, users may choose to use only one components without the other based on their need and customization.
A common example would be to use *Python Server ONLY* to process and organize session files but without a web interface. 
The users then can perform custom analysis pipeline using Python, MATLAB, or R on the structured Percept object. 

.. [1] Django Channels (https://channels.readthedocs.io/en/stable/)
.. [2] Django REST Framework (https://www.django-rest-framework.org/)

Dependencies
-----------------------------------------------

Software Packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Python** 3.70 or above 
2. **MySQL** Databse 
3. **Node Package Manager** 8 or above 

React Frontend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

React Frontend dependencies will be listed in ``package.json`` in Client folder for simplified installation. 
Only the main packages will be shown below.

1. **React** (^18.2.0)
2. **React Router DOM** (^6.2.1)
3. **Plotly.js** (^2.14.0)
4. **Axios** (^0.27.2)
5. **Material User Interface Design** (^5.10.8)
6. **Math.js** (^11.2.1)
7. **React Three Fiber** (^8.8.8)

Python Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python Server dependencies will be listed in ``requirement.txt`` in Server folder for simplify installation.
Only the main packages will be shown below.

1. **Django** (Django==4.0.6)
2. **Django Channels** (channels==4.0.0)
3. **Django REST Framework** (djangorestframework==3.14.0)
4. **MySQL Client** (mysqlclient==2.1.1)
5. **Daphne** (daphne==3.0.2)
6. **Matplotlib** (matplotlib==3.5.2)
7. **Cryptography** (cryptography==37.0.4)
8. **NiBabel** (nibabel==4.0.2)
9. **Numpy** (numpy==1.23.1)
10. **Scipy** (scipy==1.9.0)
11. **Scikit Learning** (scikit_learn==1.1.3)
12. **Spectrum** (spectrum==0.8.1)
13. **Pandas** (pandas==1.4.3)
14. **Date Utilities** (python_dateutil==2.8.2 && pytz==2022.1)
15. **HTTP Requests** (requests==2.28.1)
16. **Twilio SMS Service SDK** (twilio==7.15.2)
   
.. note::
   The packages listed above contain developmental features and may not be 100% neccessary for the basic usage. 
   A trimmed version may be created in the future if some packages are not used anymore.

Python Server Installation Guide (Linux)
------------------------------------------------

The procedure described here are tested on Ubuntu 20.04 LTS with source file directly clone through GitHub. 
The procedure here are describing for both HTTP deployment (internal use only) and HTTPS deployment (public release). 

If you intend to deploy this software for public, I highly recommend using Linux deployment procedure for HTTPS. 
This tutorial will also cover for procedure to setup Amazon Web Service Elastic Cloud Compute (EC2) 
platform to work with Django Project. 

Step 0: Environment Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install dependencies packages using ``apt-get`` is the simpliest way to start. 
We will install MySQL and Python3 Virtual Environment to setup the conditions for server. 

It is also noted that the default Python distribution on Ubuntu 18.04 is Python 3.6, therefore not satisfying the requirement. 
You need to either manually update the Python distribution so that ``python3 --version`` is up-to-date or use Ubuntu 20.04 LTS, 
which comes with Python 3.8.

All procedure assume that your working directory is the main directory of the cloned Git folder (i.e.: ``/home/ubuntu/BRAVO/Server``).

.. code-block:: bash
  
  # Set our current working directory as the SCRIPT_DIR
  SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

  # Install Dependencies with Apt
  sudo apt-get update
  sudo apt-get install python3-pip libjpeg-dev libjpeg8-dev libpng-dev nginx python3-virtualenv libmysqlclient-dev mysql-server docker.io
  
  # Setup Redis Server on Docker for Django Channels
  sudo docker run -p 6379:6379 -d redis:5

  # Create Virutal Environment for Python called "venv"
  virtualenv $SCRIPT_DIR/venv
  source $SCRIPT_DIR/venv/bin/activate

  pip3 install -r requirements.txt

Step 1: SQL Databse Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SQL Database will be used to store account information, patient entries, device entries, 
and various recording information. Due to the data size, neural recordings are not directly stored in database, 
but instead stored locally in binary format at the DataStorage folder. A data pointer that associate local files 
with patient recording will be stored in database for ease-of-access.

SQL Database will require manual creation prior to main server installation unless an existing database is used. 
You can access MySQL Database (the default database used for the installation script, but other database can be used.) 

.. code-block:: bash

  sudo mysql -u root
  # this would prompt you to enter admin password here for superuser privilege.

  # Following commands are within mysql command-line-interface
  # Create database named "BRAVOServer"
  mysql> CREATE DATABASE BRAVOServer;

  # Create a user that can access the database called "BRAVOAdmin" with an admin password called "AdminPassword"
  # Change these values to what you see fit.
  mysql> CREATE USER 'BRAVOAdmin'@'localhost' IDENTIFIED WITH mysql_native_password BY 'AdminPassword';
  mysql> GRANT ALL PRIVILEGES ON PerceptServer.* TO 'BRAVOAdmin'@'localhost';
  mysql> FLUSH PRIVILEGES;

  # exit MySQL Interface 
  mysql> exit

Once the account is set-up and database is created. You can edit the ``Server/mysql.config`` file to 
reflect actual accses credential for your database. 

Step 2: Server Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Environment variable for Python server is saved as a JSON file named ``.env``. Python will load in the file content during load time.
An example environment file looks like the following. 

.. code-block:: json

  {
    "DATASERVER_PATH": "/home/ubuntu/DataStorage/",
    "PYTHON_UTILITY": "/home/ubuntu/BRAVO/Server/modules/python-scripts",
    "ENCRYPTION_KEY": "4LLHi6IJ0PRdneDJo48kCcBf3tHTLRXQ_tyKfttDIm0=",
    "SERVER_ADDRESS": "bravo-server.jcagle.solutions",
    "CLIENT_ADDRESS": "bravo-client.jcagle.solutions",
    "MODE": "DEBUG"
  }

.. topic:: DATASERVER_PATH

  Absolute path to the folder storing all non-SQL data (TimeSeries and others).
  You should have read/write or owner permission on the folder. 
  The folder should contain 3 subfolders for organization: ``cache``, ``sessions``, and ``recordings``.

.. topic:: PYTHON_UTILITY
  
  Absolute path to the folder containing Python Utility files. 
  This is a submodule path in Server folder, and it is also where you can put your custom Python scripts.

.. topic:: ENCRYPTION_KEY

  Fernet Cryptography, it is recommended to generate this string in Python using the following code.

.. code-block:: python
  
  from cryptography import fernet

  fernet.Fernet.generate_key().decode("utf-8")
  # Output: 'uCskkPv8pVyF9r0tSXQs2hvD7YYs-eS8nP7pkwz0vps='

.. topic:: SECRET_KEY

  This is a web-server specific key for cryptographic signing for session cookies.
  DO NOT let others get your key, otherwise they can modify cookies sent by our server.

.. topic:: SERVER_ADDRESS and CLIENT_ADDRESS

  The server address to access the Python Server. 
  This can be the same as your React Frontend address (CLIENT_ADDRESS) if you setup Proxy for it.
  If not, configure both string to the correct path.

.. topic:: MODE

  The Django operating mode. DEBUG allow more error log in case if an error is shown. 
  During development, you may keep it as ``DEBUG`` but set to ``PRODUCTION`` when done. 

Step 3: Django - MySQL Database Initialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Initial migration is required to setup the Database to the required structure of Django Server. 
This only need to be run once, unless a change is made to ``Server/Backend/models.py`` file. 

.. code-block:: bash

  python3 $SCRIPT_DIR/manage.py makemigrations Backend
  python3 $SCRIPT_DIR/manage.py migrate
  python3 $SCRIPT_DIR/manage.py collectstatic

.. warning:: 
  
  The new BRAVO Server Database has significant difference when compared to the original BRAVO platform v0.1 released in 2021.
  The database are not convertable at the moment, but a migration script is in development to help as much migration as possible. 

Step 4: SSL (HTTPS) Certificate (Optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This step is not neccessary for local deployment. However, for people who want additional security to deploy with HTTPS, 
we will provide guidance for obtaining simple certificates for SSH. 

The most common tool for free SSL certificate is through `CertBot <https://certbot.eff.org/>`_. 
Refer to CertBot site to install tool on your server computer. 
First, you can configure your DNS record to have your server address (``$YOUR_SERVER_ADDRESS``) point to your server IP. 
Then run the following script to obtain your SSL certificate. 
The output certificates should be saved in a directory at ``/etc/letsencrypt/live/$YOUR_SERVER_ADDRESS/``.

.. code-block:: bash 
  
  sudo certbot certonly --standalone --preferred-challenges http -d $YOUR_SERVER_ADDRESS

A bare-minimum sample nginx configuration file ``deployment.conf`` is in Server directory as a reference to create a working reverse proxy server to direct SSL traffic to your server.
This configuration file should be saved in ``/etc/nginx/sites-enabled/`` directory and you should reload your nginx service whenever a change is made to the configuration.

Step 5: Deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Due to the use of Websocket for real-time analysis, the default operating condition is through 
Asynchronized Server Gateway Interface (ASGI) as opposed to the default Web Server Gateway Interface (WSGI) for Python. 
To use ASGI, we use ``daphne`` to start our server. A standard startup script ``startServer.sh`` is available in Server folder for reference.

.. code-block:: bash 

  #/bin/bash
  SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

  # To start with WSGI - Django Channels Disabled
  $SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/manage.py runserver 0:3001
  
  # To start with ASGI - Django Channels Enabled. 
  $SCRIPT_DIR/venv/bin/daphne -p 3001 -b 0.0.0.0 BRAVO.asgi:application

.. warning:: 

  Due to how daphne is looking for Python modules, the working directory must be in "Server" folder for the command to work. 