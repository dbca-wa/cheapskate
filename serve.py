#!/usr/bin/env python2
from bottle import route, run, template, request
import subprocess
import requests
import json

def get_instance(name):
    instance = subprocess.check_output(["aws", "ec2", "describe-instances", "--filters", 
        "Name=tag:UserLaunchable,Values=true", "Name=tag:Name,Values="+name, 
        "--query", "Reservations[*].Instances[*].[InstanceId,State.Name]"])
    return json.loads(instance)[0][0]

form_template = '''
    <form action="/ec2/{0}" method="post">
        Username: <input name="username" type="text" />
        Password: <input name="password" type="password" />
        <input value="Launch" type="submit" />
    </form>
'''

@route('/ec2/<name>')
def ec2_instance(name):
    try:
        instance, state = get_instance(name)
    except:
        return template('<b>Instance {{name}} not found</b>', name=name)
    form = template('<b>Instance {{name}} is already running.', name=name)
    if state != "running":
        form = form_template.format(name)
    return form

@route('/ec2/<name>', method='POST')
def launch_ec2_instance(name):
    username = request.forms.get('username')
    password = request.forms.get('password')
    r = requests.get("https://webdav.dpaw.wa.gov.au/dfs/", auth=(username, password))
    if r.status_code != 200:
        return template('<b>Access Denied</b>')
    try:
        instance, state = get_instance(name)
    except:
        return template('<b>Instance {{name}} not found</b>', name=name)
    if state != "running":
        try: 
            status = subprocess.check_output(["aws", "ec2", "start-instances", "--instance-ids", instance])
        except Exception as e:
            return e
            #return template('<b>Instance {{name}} failed to start.</b>', name=name)
    return template('<b>{{name}} is running.</b>', name=name)

run(host='0.0.0.0', port=8000)
