FROM ubuntu/nginx:1.18-20.04_beta

ENV DATASERVER_PATH=/usr/src/BRAVO/BRAVOStorage/
ENV PYTHONPATH=/usr/src/BRAVO/modules/python-scripts

WORKDIR /usr/src/BRAVO
COPY ./Client/build /usr/share/nginx/html
COPY ./Server/bravo_nginx.conf /etc/nginx/sites-enabled/default

COPY ./Server .

RUN mkdir -p BRAVOStorage && \ 
    apt-get update && \
    apt-get install cron python3 python3-pip libjpeg-dev libjpeg8-dev libpng-dev libmysqlclient-dev -y && \
    pip3 install -r requirements.txt

COPY ./Server/cron-job /etc/cron.d/cron-job

RUN chmod 0644 /etc/cron.d/cron-job && \
    crontab /etc/cron.d/cron-job

EXPOSE 443
EXPOSE 3001

CMD ["bash"]
