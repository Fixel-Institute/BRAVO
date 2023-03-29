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

# Setup Script 
python3 manage.py SetupBRAVO
python3 manage.py makemigrations Backend
python3 manage.py migrate

# Beaware, if you run install.sh as root, this will show up as root crontab and not user-crontab. This will lead to permission error in the future
(crontab -l ; echo "* * * * * bash $SCRIPT_DIR/ProcessingQueueJob.sh >> $SCRIPT_DIR/ProcessingQueueLog.txt")| crontab -
(crontab -l ; echo "* * * * * bash $SCRIPT_DIR/JWTTokenBlacklistCleanup.sh")| crontab -

# Start Cron-Task
sudo systemctl start cron
sudo systemctl enable cron 