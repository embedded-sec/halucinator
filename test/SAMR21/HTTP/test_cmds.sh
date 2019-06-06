#! /bin/bash

## Need to run below command from repo root in seperate terminal, updating -i to network interface
# sudo ~/.virtualenvs/halucinator/bin/python -m halucinator.external_devices.host_ethernet -i=enx000acd302efe --id=ksz8851
##

wget 192.168.0.100
wget 192.168.0.100/index.html
wget 192.168.0.100/index.htm
wget 192.168.0.100/jquery.js
wget 192.168.0.100/style.css
wget http://192.168.0.100/favicon.ico
wget http://192.168.0.100/status?_=1547486274423
wget http://192.168.0.100/set_led?n=0\&set=0\&_=1547486272679
wget http://192.168.0.100/set_led?n=0\&set=1\&_=1547486273588

ping -c10 192.168.0.100
