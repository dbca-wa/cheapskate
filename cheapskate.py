#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime as dt

class classproperty(object):
    def __init__(self, f):
        self.f = f
    def __get__(self, obj, owner):
        return self.f(owner)


class Instance:
    """
        Represents an ec2 instance with some helper functions
        to use a cheapskate tag to turn instances on and off.
    """
    GROUPS = {
        "0": "Default Off",
        "1": "Default On",
        "2": "Business Hours"
    }

    DATEFORMAT = '%Y-%m-%dT%H:%M'

    def __init__(self, instance_id=None, instance_data=None):
        if "InstanceId" in instance_data:
            self.instance_id = instance_data["InstanceId"]
            self.raw = instance_data
        else:
            self.instance_id = instance_id
            self.raw = json.loads(subprocess.check_output(["aws", "ec2", "describe-instances", "--instance-id", instance_id]).decode("utf-8"))["Reservations"][0]["Instances"][0]
        self.cheapskate = {
            "grp": "1",
            "user": "",
            "off": "",
            "req": ""
        }
        if "cheapskate" in [a["Key"] for a in self.raw["Tags"]]:
            cheapskate_raw = [a for a in self.raw["Tags"] if a["Key"] == "cheapskate"][0]["Value"].strip()
            self.cheapskate.update(dict([a.split("=") for a in cheapskate_raw.split("/")]))

    def save(self):
        cheapskate_raw = "/".join([key + "=" + value for key, value in self.cheapskate.items()])
        print(subprocess.check_output(["aws", "ec2", "create-tags", "--resources", self.instance_id, "--tags", 'Key=cheapskate,Value="{}"'.format(cheapskate_raw)]))

    @classproperty
    def objects(cls):
        if not hasattr(cls, "_objects"):
            raw = json.loads(subprocess.check_output(["aws", "ec2", "describe-instances"]).decode("utf-8"))
            objects = []
            for data in raw["Reservations"]:
                objects.append(Instance(instance_data=data["Instances"][0]))
            cls._objects = objects
        return cls._objects

    @classmethod
    def save_all(cls):
        for instance in cls.objects:
            instance.save()

    @classmethod
    def shutdown_due(cls, hours=0):
        results = []
        for instance in cls.objects:
            try:
                if dt.strptime(instance.cheapskate["off"], Instance.DATEFORMAT) < dt.now():
                    results.append(instance)
            except ValueError:
                pass
        return results

    def update(self, user=None, off=None, req=None, grp=None):
        if grp:
            self.cheapskate["grp"] = grp
        if user:
            self.cheapskate["user"] = user
        if off:
            self.cheapskate["off"] = off
        if req:
            self.cheapskate["req"] = req
        self.save()

    def shutdown(self):
        if self.cheapskate["grp"] != 1:
            pass
            #subprocess.check_output(["aws", "ec2", "stop-instance", "--instance-id", self.instance_id])

    def __str__(self):
        return "{} ({})".format(self.raw["InstanceId"], [a for a in self.raw["Tags"] if a["Key"] == "Name"][0]["Value"])

