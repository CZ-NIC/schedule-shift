import configparser
import os
from dataclasses import dataclass
from os import path

import caldav
import dateutil
from caldav import Calendar

config = configparser.ConfigParser()
config.optionxform = str  # dont lowercase

os.chdir(path.join(path.dirname(path.realpath(__file__)), ".."))
config.read("config.ini")


@dataclass
class Member:
    score: float = 0  # how many days the worker is in the advantage
    coefficient: float = 0  # 1 = full-time, < 1 part-time, > 1 longer work load job
    balance: float = 0  # personal balance, how many days more/less should the worker do


class Config:
    verbose = False
    config = config

    # read projects
    projects : dict[str, dict[str, Member]] = {}  # {"project": {"member1": 0, ...}, ... }

    @classmethod
    def reset_projects(cls):
        for project, members in config.items("projects"):
            cls.projects[project] = {}
            members = [k.strip() for k in members.split(",")]
            for member in members:
                try:
                    bonus, coefficient = (float(x) for x in Config.config.get(f"projects.{project}", member).split(","))
                except configparser.Error:
                    bonus, coefficient = 0, 1

                cls.projects[project][member] = Member(bonus, coefficient)

    @staticmethod
    def calendar():
        url = config.get("general", "calendar_url")
        username = config.get("general", "calendar_username")
        password = config.get("general", "calendar_password")
        client = caldav.DAVClient(url, username=username, password=password)
        return Calendar(client, url)

    @classmethod
    def get_events(cls):
        calendar = cls.calendar()
        date = cls.config.get("general", "start_date")
        if date:
            return calendar.date_search(dateutil.parser.parse(date))
        return calendar.events()

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
