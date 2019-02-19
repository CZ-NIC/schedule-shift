import configparser
import os
from os import path

import caldav
from caldav import Calendar

config = configparser.ConfigParser()
config.optionxform = str  # dont lowercase

os.chdir(path.join(path.dirname(path.realpath(__file__)), ".."))
config.read("config.ini")


class Config:
    verbose = False
    config = config

    # read projects
    projects = {}  # {"project": {"member1": 0, ...}, ... }

    @classmethod
    def reset_projects(cls):
        for project, members in config.items("projects"):
            cls.projects[project] = {k.strip(): 0 for k in members.split(",")}

    @staticmethod
    def calendar():
        url = config.get("general", "calendar_url")
        username = config.get("general", "calendar_username")
        password = config.get("general", "calendar_password")
        client = caldav.DAVClient(url, username=username, password=password)
        return Calendar(client, url)

    @classmethod
    def get_mail(cls, name):
        try:
            return config.get("team", name)
        except KeyError:
            return None

    @classmethod
    def get_member_mails(cls, project):
        for member in cls.projects[project]:
            yield cls.get_mail(member)


Config.reset_projects()