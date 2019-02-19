import configparser

import caldav
from caldav import Calendar

config = configparser.ConfigParser()
config.optionxform = str  # dont lowercase
config.read("config.ini")


class Config:
    # read projects
    projects = {}  # {"project": {"member1": 0, ...}, ... }
    for project, members in config.items("projects"):
        projects[project] = {k.strip(): 0 for k in members.split(",")}

    verbose = False
    config = config

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
