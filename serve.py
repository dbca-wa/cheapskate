#!/usr/bin/env python3
from bottle import route, run, template, request, default_app, HTTPError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import subprocess
import requests
import json
import os
import smtplib
from operator import itemgetter
from cheapskate import Instance

ALLOWED_IPS = ["127.0.0.1"]
DEBUG = False 

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


def check_cli_ip(route=""):
    if DEBUG:
        return
    client_ip = request.environ.get('REMOTE_ADDR')
    if client_ip not in ALLOWED_IPS:
        raise HTTPError(404, "Not found: '{}'".format(route))

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
    return Instance.objects()[instance_id].as_dict()

@route('/api/ec2_instance/<instance_id>', method='POST')
def ec2_instance_update(instance_id):
    instance = Instance.objects()[instance_id]
    hours = request.forms.get("hours")
    user = request.headers.get("Remote-User")
    instance.update(user=user, hours=int(hours))
    return json.dumps(instance.as_dict())

@route('/api/cli/shutdown_check')
def cli_shutdown_check():
    check_cli_ip("/api/cli/shutdown_check")

    with open("shutdown_due.json","w") as shut:
        output = []
        for instanceid, instance in Instance.shutdown_due(hours=3).items():
            inst = instance.as_dict()
            inst.pop("product", None)
            output.append(inst)
        shut.write(json.dumps(output, sort_keys=True, indent=4, separators=(',',': ')))
    return "Shutdown file contains {} servers".format(len(output)) 

@route('/api/cli/email_report')
def cli_email_report():
    check_cli_ip("/api/cli/email_report")

    FROM = "cheapskate@dpaw.wa.gov.au"
    TO = "asi@dpaw.wa.gov.au"
    msg = MIMEMultipart('mixed')

    msg['Subject'] = "Cheapskate shutdown report"
    msg['From'] = FROM
    msg['To'] = TO
    body = "Instances to be turned off in the next 3 hours:\n"
    body = body + "\nInstance ID\tShutdown Group\tShutdown time\t\tRequested time\t\tInstance Name\n"

    instances = json.load(open("shutdown_due.json"))
    if len(instances) == 0:
        return "No shutdowns due"

    instances = sorted(instances, key=itemgetter('off'))
    for instance in instances:
        body = body + "{}\t{}\t\t{}\t{}\t{}\n".format(instance["id"], Instance.GROUPS[instance["grp"]], instance["off"], instance["req"], instance["name"])
    msg.attach(MIMEText(body))

    s = smtplib.SMTP('smtp.corporateict.domain')
    s.sendmail(FROM, TO, msg.as_string())
    s.quit()

    return "Email sent"

@route('/api/cli/shutdown')
def cli_shutdown():
    check_cli_ip("/api/cli/shutdown")
    result = {}

    instances = json.load(open("shutdown_due.json"))
    if len(instances) == 0:
        return "No shutdowns required"

    for instance in instances:
        result[instance["id"]] = Instance.objects()[instance["id"]].shutdown()

    return result

@route('/api/cli/start_business_hours')
def cli_start_business_hours():
    check_cli_ip("/api/cli/shutdown")

    result = Instance.start_business_hours()
    if result:
        return result
    else:
        return "No instances meet criteria"

@route('/api/cli/reset')
def cli_reset():
    check_cli_ip("/api/cli/reset")
    return None

    for instanceid, instance in Instance.objects().items():
        instance.cheapskate["grp"] = "1"

    Instance.save_all()

    return "Instances reset"

application = default_app()
