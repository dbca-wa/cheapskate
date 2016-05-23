#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime as dt, timedelta
from jsonpath_rw import parse
import uwsgi
import pickle


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
    COSTTHRESHOLD = 20

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
        uwsgi.cache_del("raw_aws")

    @classmethod
    def objects(cls):
        if not uwsgi.cache_exists("raw_aws"):
            if hasattr(cls, "_objects"):
                del cls._objects
            uwsgi.cache_set("raw_aws", subprocess.check_output(["aws", "ec2", "describe-instances", "--no-paginate"]), 60*15)
        raw = json.loads(uwsgi.cache_get("raw_aws").decode("utf-8"))
        if hasattr(cls, "_objects"):
            return cls._objects
        objects = {}
        for data in raw["Reservations"]:
            for instance_data in data["Instances"]:
                instance = Instance(instance_data=instance_data)
                objects[instance.instance_id] = instance
        cls._objects = objects
        return objects

    @classmethod
    def objects_list(cls):
        return [i.__dict__() for i in cls.objects().values()]

    def __dict__(self):
        data = self.cheapskate
        data["name"] = self.name
        data["id"] = self.instance_id
        data["status"] = self.raw["State"]["Name"]
        data["type"] = self.raw["InstanceType"]
        data["launchtime"] = dt.strftime(dt.strptime(self.raw["LaunchTime"], Instance.DATEFORMAT + ":%S.%fZ"), Instance.DATEFORMAT)
        data["hourlycost"] = "%.3f"%float(self.price)
        data["product"] = self.product
        return data

    @classmethod
    def save_all(cls):
        for instanceid, instance in cls.objects().items():
            instance.save()

    @classmethod
    def shutdown_due(cls, hours=0):
        results = {}
        for instanceid, instance in cls.objects().items():
            try:
                if dt.strptime(instance.cheapskate["off"], Instance.DATEFORMAT) < dt.now() + timedelta(hours=hours):
                    results[instanceid] = instance
            except ValueError:
                pass
        return results

    def update(self, user, hours):
        self.cheapskate["user"] = user
        self.cheapskate["req"] = dt.strftime(dt.now() + timedelta(hours=hours), Instance.DATEFORMAT)
        if self.price * hours >= Instance.COSTTHRESHOLD:
            self.cheapskate["off"] = dt.strftime(dt.now() + timedelta(hours=(Instance.COSTTHRESHOLD/self.price)), Instance.DATEFORMAT)
            print (self.cheapskate["off"], self.cheapskate["req"])
        self.start()
        self.save()

    def start(self):
        return subprocess.check_output(["aws", "ec2", "start-instances", "--instance-ids", self.instance_id])
    
    def shutdown(self):
        if self.cheapskate["grp"] == 1:
            return 0
        elif self.cheapskate["grp"] == 2:
            #Check if outside business hours then shut down
            pass
        else:
            if dt.strptime(self.cheapskate["off"], Instance.DATEFORMAT) < dt.now():
                #subprocess.check_output(["aws", "ec2", "stop-instances", "--instance-ids", self.instance_id])
                pass

    def __str__(self):
        return "{} ({})".format(self.raw["InstanceId"], [a for a in self.raw["Tags"] if a["Key"] == "Name"][0]["Value"])

