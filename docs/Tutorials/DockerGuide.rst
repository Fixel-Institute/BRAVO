Docker Container Installation Guide (Beta)
===========================================

Overview
-----------------------------------------

The BRAVO Platform v2.1.1 introduce the Docker Container version of the platform to allow easier deployment of software for local use. 
In the future, every numbered release will have docker image updated. 

Docker Image and Repository
-------------------------------------------

Dockerfiles are created for BRAVO Client and Server folder. The Client Docker Image is a simple react-script starter, which means the Docker Image for 
BRAVO Client is somewhat slow due to compilation every time we need to start the Client. The BRAVO Server utilize additional Docker Image such as 
``mysql:8.0`` and ``redis:5`` for handling data storage and cache for WebSocket. By default, CRON is also started in BRAVO Server Container so the **ProcessingQueueJob**
is being run periodically (every minute) without user interaction. 

How to start Docker Container
-------------------------------------------

A ``docker-compose.yml`` file is placed in Docker folder. This file utilize the `Docker Compose <https://docs.docker.com/compose/>`_ function, naturally included
in the Docker Desktop. You may download Docker Desktop for Windows through their `docker tutorial for Windows <https://docs.docker.com/desktop/install/windows-install/>`_
or `docker tutorial for Mac <https://docs.docker.com/desktop/install/mac-install/>`_. I do not recommend using Docker Container for Linux. 

Once installed, you can use Powershell or Terminal to call the following code inside the Docker folder containing ``docker-compose.yml`` file.

.. code-block:: bash 

  docker compose up -d

After Docker Container is started, you can simply start/stop the docker container via Docker Desktop GUI. 

Where are Docker File stored
-------------------------------------------

The Docker Compose will create 2 volumes, one for SQL Database (docker_SQLDatabase) and one for BRAVO data (docker_BRAVOStorage). These 
volumes are usually mapped in the VM and accessible via Docker Interface. 

For Windows, they are usually in ``\\wsl.localhost\docker-desktop-data\data\docker\volumes``. 

Public Access for Docker Images
--------------------------------------------

By using Windows NETSH command, we can forward ports from Docker to public domain so your Windows Docker Image can serve as a public accessible server as well. 

By standard, Port 80 and Port 3001 are used by Docker (80 as Frontend and 3001 as Backend) to serve the BRAVO Platform. However, it is also important to edit 
`SERVER_ADDRESS` and `CLIENT_ADDRESS` to your actual IP address. To do so, you can edit the `docker-compose.yml` file you download.

.. code-block:: bash 

  netsh interface portproxy set v4tov4 listenport=80 listenaddress=0.0.0.0 connectport=80 connectaddress={WSL_IP_Address}
  netsh interface portproxy set v4tov4 listenport=3001 listenaddress=0.0.0.0 connectport=3001 connectaddress={WSL_IP_Address}