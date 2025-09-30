from collections import defaultdict
import configparser
from datetime import date, datetime, time
import os
from dataclasses import dataclass, field
from os import path
from typing import TypedDict

import caldav
import dateutil
from caldav import Calendar
from mininterface import run

Name = str
Mail = str

@dataclass
class ProjectDict:
    members: list[Name]
    balance_bonus: dict[Name, int] = field(default_factory=dict)
    balance_delta: int = 0
    coefficient: dict[Name, int] = field(default_factory=dict)

@dataclass
class Env:
    smtp_server: str
    email_from: Mail
    calendar_url: str
    calendar_username: str
    calendar_password: str
    application_url: str
    start_date: date
    team: dict[Name, Mail]
    projects: dict[str, dict]

    def get_projects(self):
        # NOTE if tyro supported `projects: dict[str, ProjectDict]`, this method could vanish
        projects = defaultdict(dict)
        for project, val in self.projects.items():
            pd = ProjectDict(*val.values())
            for member in pd.members:
                projects[project][member] = Member(pd.balance_bonus.get(member, 0), pd.coefficient.get(member, 1))
        return projects




@dataclass
class Member:
    score: float = 0  # how many days the worker is in the advantage
    coefficient: float = 0  # 1 = full-time, < 1 part-time, > 1 longer work load job
    balance: float = 0  # personal balance, how many days more/less should the worker do


class Config:
    verbose = False

    def __init__(self):
        m = run(Env, args=[], config_file="scheduler.yaml")
        self.env = m.env

    @property
    def projects(self)-> dict[str, dict[str, Member]]:
        # {"project": {"member1": 0, ...}, ... }
        return self.env.get_projects()

    def calendar(self):
        e = self.env
        client = caldav.DAVClient(e.calendar_url, username=e.calendar_username, password=e.calendar_password)
        return Calendar(client, e.calendar_url)

    def get_events(self):
        calendar = self.calendar()
        date = self.env.start_date
        if date:
            return calendar.date_search(date)
        return calendar.events()

    def get_mail(self, name):
        return self.env.team.get(name, None)

    def get_member_mails(self, project):
        for member in self.projects[project]:
            yield self.get_mail(member)