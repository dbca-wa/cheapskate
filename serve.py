#!/usr/bin/env python3
from bottle import route, run, template, request
import subprocess
import requests
import json
import os
from cheapskate import Instance

form_template = '''
    <form action="/ec2/{0}" method="post">
        Username: <input name="username" type="text" />
        Password: <input name="password" type="password" />
        <input value="Launch" type="submit" />
    </form>
'''

main_template = '''
    <h3>List of Instances and their status</h3>
    </ hr>
    <table>
        <tr>
            <th>Instance ID</th>
            <th>Off Date</th>
            <th>User</th>
            <th>Requested Off Date</th>
            <th>Group</th>
        <tr>
    %index = 0
    %for instance in inst:
        <tr>
            <td><a href="/{{ index }}">{{ instance.instance_id }}</a></td>
            <td>{{ instance.cheapskate["off"] }}</td>
            <td>{{ instance.cheapskate["user"] }}</td>
            <td>{{ instance.cheapskate["req"] }}</td>
            <td>{{ instance.GROUPS[instance.cheapskate["grp"]] }}</td>
        </tr>
        %index += 1
    %end
    </table>
'''

inst_template = '''
    <table>
        <tr>
            <th>Instance ID</th>
            <th>Off Date</th>
            <th>User</th>
            <th>Requested Off Date</th>
            <th>Group</th>
        <tr>
        <tr>
            <td>{{ instance.instance_id }}</td>
            <td>{{ instance.cheapskate["off"] }}</td>
            <td>{{ instance.cheapskate["user"] }}</td>
            <td>{{ instance.cheapskate["req"] }}</td>
            <td>{{ instance.GROUPS[instance.cheapskate["grp"]] }}</td>
        </tr>
    </table>
'''

@route('/')
def home():
    return """
<html><body>
<p>GET <a href="/api/ec2_instance">/api/ec2_instance</a> - EC2 instances as json</p>
<p>GET /api/ec2_instance/<instance_id> - Single EC2 instance as json</p>
<p>POST /api/ec2_instance/<instance_id> - Update Single EC2 instance json</p>
</body></html>
"""

@route('/api/ec2_instance')
def ec2_instances():
    return json.dumps(Instance.objects_dict())

@route('/api/ec2_instance/<instance_id>')
def ec2_instance(instance_id):
    return json.dumps(Instance.objects_dict()[instance_id])

@route('/api/ec2_instance/<instance_id>', method='POST')
def ec2_instance_update(instance_id):
    instance = Instance.objects()[instance_id]
    instance.cheapskate["req"] = request.json["req"]
    instance.cheapskate["user"] = request.headers["REMOTE_USER"]
    instance.save()
    return json.dumps(instance.__dict__())



# @route('/ec2/<name>')
# def ec2_instance(name):
#     try:
#         instance, state = get_instance(name)
#     except:
#         return template('<b>Instance {{name}} not found</b>', name=name)
#     form = template('<b>Instance {{name}} is already running.', name=name)
#     if state != "running":
#         form = form_template.format(name)
#     return form
#
# @route('/ec2/<name>', method='POST')
# def launch_ec2_instance(name):
#     username = request.forms.get('username')
#     password = request.forms.get('password')
#     r = requests.get("https://webdav.dpaw.wa.gov.au/dfs/", auth=(username, password))
#     if r.status_code != 200:
#         return template('<b>Access Denied</b>')
#     try:
#         instance, state = get_instance(name)
#     except:
#         return template('<b>Instance {{name}} not found</b>', name=name)
#     if state != "running":
#         try: 
#             status = subprocess.check_output(["aws", "ec2", "start-instances", "--instance-ids", instance])
#         except Exception as e:
#             return e
#             #return template('<b>Instance {{name}} failed to start.</b>', name=name)
#     return template('<b>{{name}} is running.</b>', name=name)

if True or not os.path.exists("ec2prices.json"):
    ec2pricedata = json.load(open("ec2prices2.json"))
    with open("ec2prices.json", "w") as ec2:
        #priceurl = "https://pricing.us-east-1.amazonaws.com"
        #offers = requests.get(priceurl + "/offers/v1.0/aws/index.json").content.decode("utf-8")
        #ec2priceurl = priceurl + json.loads(offers)["offers"]["AmazonEC2"]["currentVersionUrl"]
        #ec2pricedata = requests.get(ec2priceurl).content.decode("utf-8")
        region_prices = [product for key, product in ec2pricedata['products'].items() if product["attributes"].get("location") == "Asia Pacific (Sydney)"]
        for product in region_prices:
            product["attributes"]["terms"] = ec2pricedata["terms"]["OnDemand"][product["sku"]]
        ec2.write(json.dumps(region_prices))

run(host='0.0.0.0', port=8001, reloader=True)
