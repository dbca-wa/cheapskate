#!/usr/bin/env python3
import requests
from datetime import datetime as dt

url = 'http://localhost:8001'


with open("/srv/cheapskate/log/cronlog.log", "a") as log:
    log.write(dt.now().strftime("%Y-%m-%dT%H:%M:%S") + "\n")
    log.write(requests.get(url+'/api/cli/shutdown_check').text + "\n")
    log.write(requests.get(url+'/api/cli/start_business_hours').text + "\n")
    log.write(requests.get(url+'/api/cli/email_report').text + "\n")
    log.write(requests.get(url+'/api/cli/shutdown').text + "\n\n")

    log.close()
