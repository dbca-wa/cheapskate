#!/usr/bin/env python3
from bottle import route, run, template, request, default_app
import subprocess
import requests
import json
import os

if not os.path.exists("ec2prices_raw.json"):
    priceurl = "https://pricing.us-east-1.amazonaws.com"
    offers = requests.get(priceurl + "/offers/v1.0/aws/index.json").content.decode("utf-8")
    ec2priceurl = priceurl + json.loads(offers)["offers"]["AmazonEC2"]["currentVersionUrl"]
    ec2pricedata = requests.get(ec2priceurl).content.decode("utf-8")
    with open("ec2prices_raw.json", "w") as raw:
        raw.write(ec2pricedata)

if not os.path.exists("ec2prices.json"):
    ec2pricedata = json.load(open("ec2prices_raw.json"))
    with open("ec2prices.json", "w") as ec2:
        region_prices = []
        for key, product in ec2pricedata['products'].items():
            if not product.get("productFamily") == "Compute Instance": continue
            if not product["attributes"]["location"] == "Asia Pacific (Sydney)": continue
            if not product["attributes"]["tenancy"] == "Shared": continue
            if not product["attributes"]["preInstalledSw"] == "NA": continue
            if product["attributes"]["licenseModel"] == "Bring your own license": continue
            region_prices.append(product)
        output = {}
        for product in region_prices:
            product["attributes"]["terms"] = ec2pricedata["terms"]["OnDemand"][product["sku"]]
            product_key = product["attributes"]["instanceType"] + "." + product["attributes"]["operatingSystem"]
            if product_key in output:
                raise Exception("Duplicate product key {}".format(product_key))
            output[product_key] = product["attributes"]
        ec2.write(json.dumps(output))

from cheapskate import Instance

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
    return {"objects": Instance.objects_list()}

@route('/api/ec2_instance/<instance_id>')
def ec2_instance(instance_id):
    return Instance.objects()[instance_id].__dict__()

@route('/api/ec2_instance/<instance_id>', method='POST')
def ec2_instance_update(instance_id):
    instance = Instance.objects()[instance_id]
    hours = request.forms.get("hours")
    user = request.headers.get("Remote-User")
    instance.update(user=user, hours=int(hours))
    return json.dumps(instance.__dict__())

application = default_app()
