#!/usr/bin/env python3
from bottle import route, run, template, request
import subprocess
import requests
import json
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
def home_page():
    page = template(main_template, inst=Instance.objects)

    return page

@route('/<index>')
def inst_page(index):
    page = template(inst_template, instance=Instance.objects[int(index)])

    return page

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

run(host='0.0.0.0', port=8001, reloader=True)
