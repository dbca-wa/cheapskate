#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime as dt, timedelta
from jsonpath_rw import parse


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
    CHEAPSKATE = { "grp": "1", "user": "", "off": "", "req": "" }
    PRODUCTS = json.load(open("ec2prices.json"))

    def __init__(self, instance_data):
        self.instance_id = instance_data["InstanceId"]
        self.raw = instance_data
        self.cheapskate = Instance.CHEAPSKATE.copy()
        self.name = ""
        if "cheapskate" in [a["Key"] for a in self.raw["Tags"]]:
            cheapskate_raw = [a for a in self.raw["Tags"] if a["Key"] == "cheapskate"][0]["Value"].strip()
            self.cheapskate.update(dict([a.split("=") for a in cheapskate_raw.split("/")]))
        if "Name" in [a["Key"] for a in self.raw["Tags"]]:
            self.name = [a for a in self.raw["Tags"] if a["Key"] == "Name"][0]["Value"].strip()
        product_key = self.raw["InstanceType"] + "." + self.raw.get("Platform", "linux").title()
        self.product = Instance.PRODUCTS[product_key]
        pricedims = parse("terms.*.priceDimensions.*").find(self.product)
        if not pricedims:
            pricedims = parse("terms").find(self.product)
        pricedims = pricedims[0].value
        self.price = pricedims["pricePerUnit"]["USD"]
        self.product["terms"] = pricedims

    def save(self):
        cheapskate_raw = "/".join([key + "=" + value for key, value in self.cheapskate.items() if key in Instance.CHEAPSKATE.keys()])
        subprocess.check_output(["aws", "ec2", "create-tags", "--resources", self.instance_id, "--tags", 'Key=cheapskate,Value="{}"'.format(cheapskate_raw)])

    @classmethod
    def objects(cls):
        if not hasattr(cls, "_objects") or dt.now() - cls._updated > timedelta(minutes=15):
            raw = json.loads(subprocess.check_output(["aws", "ec2", "describe-instances", "--no-paginate"]).decode("utf-8"))
            objects = {}
            for data in raw["Reservations"]:
                for instance_data in data["Instances"]:
                    instance = Instance(instance_data=instance_data)
                    objects[instance.instance_id] = instance
            cls._objects = objects
            cls._updated = dt.now()
        return cls._objects

    @classmethod
    def objects_list(cls):
        return [i.__dict__() for i in cls.objects().values()]

    def __dict__(self):
        data = self.cheapskate
        data["name"] = self.name
        data["id"] = self.instance_id
        data["status"] = self.raw["State"]["Name"]
        data["type"] = self.raw["InstanceType"]
        data["launchtime"] = self.raw["LaunchTime"]
        data["hourlycost"] = self.price
        data["product"] = self.product
        return data

    @classmethod
    def save_all(cls):
        for instance in cls.objects():
            instance.save()

    @classmethod
    def shutdown_due(cls, hours=0):
        results = []
        for instance in cls.objects():
            try:
                if dt.strptime(instance.cheapskate["off"], Instance.DATEFORMAT) < dt.now():
                    results.append(instance)
            except ValueError:
                pass
        return results

    def update(self, user, hours):
        self.cheapskate["user"] = user
        self.cheapskate["req"] = dt.strftime(dt.now() + timedelta(hours=hours), Instance.DATEFORMAT)
        # TODO: check hours/req meets approval
        self.start()
        self.save()

    def start(self):
        return subprocess.check_output(["aws", "ec2", "start-instances", "--instance-ids", self.instance_id])
    
    def shutdown(self):
        if self.cheapskate["grp"] != 1:
            pass
            #subprocess.check_output(["aws", "ec2", "stop-instance", "--instance-id", self.instance_id])

    def __str__(self):
        return "{} ({})".format(self.raw["InstanceId"], [a for a in self.raw["Tags"] if a["Key"] == "Name"][0]["Value"])

