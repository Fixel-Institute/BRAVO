#/bin/bash!

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

sudo apt-get update
sudo apt-get install python3-pip libjpeg-dev libjpeg8-dev libpng-dev apache2 libapache2-mod-wsgi-py3 python3-virtualenv libmysqlclient-dev mysql-server

virtualenv $SCRIPT_DIR/venv
$SCRIPT_DIR/venv/bin/pip3 install django djangorestframework numpy scipy pandas spectrum mysqlclient requests websocket-client scikit-learn cryptography nibabel
