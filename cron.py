#!/usr/bin/env python3
import requests

url = 'http://localhost:8001'

print(requests.get(url+'/api/cli/shutdown_check').text)
print(requests.get(url+'/api/cli/start_business_hours').text)
print(requests.get(url+'/api/cli/email_report').text)
print(requests.get(url+'/api/cli/shutdown').text)

