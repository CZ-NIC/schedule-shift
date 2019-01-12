#!/usr/bin/env python3
import configparser
import json
from collections import defaultdict

import caldav
from caldav import Calendar
from dateutil.parser import parse
from datetime import datetime, timedelta
from flask import Flask, render_template, request
from icalendar import Calendar as iCalendar, Event as iEvent

# from itertools import chain, islice, repeat
# import pandas as pd
from requests.exceptions import InvalidSchema

app = Flask("shift-schedule")

config = configparser.ConfigParser()
config.optionxform = str  # dont lowercase
config.read("config.ini")


class Controller:

    @staticmethod
    def get_calendar():
        url = config.get("general", "calendar_url")
        username = config.get("general", "calendar_username")
        password = config.get("general", "calendar_password")
        client = caldav.DAVClient(url, username=username, password=password)
        calendar = Calendar(client, url)
        return calendar

    @app.route("/")
    def homepage():
        calendar = Controller.get_calendar()
        schedules = []
        #stats = defaultdict(lambda: defaultdict(int)) # XX
        stats = {"Csirtmaster": defaultdict(int)}
        members = config.get("projects", "csirtmaster").split(",")  # XX
        try:
            date_search = calendar.date_search(parse("2019-01-01"), parse("2019-02-20"))  # XXX
        except InvalidSchema:
            return f"Can't date_search the calendar."

        for event in date_search:
            for ev in iEvent.from_ical(event.data).subcomponents:
                if ev.name == "VEVENT":
                    print(ev["uid"])
                    try:
                        project, name = ev["summary"].split(" ", 1)
                        project = "Csirtmaster"  # XX
                        stats[project][name] += 1  # XX split by workdays, not by events
                    except:
                        project = 'Root' # XX
                        name = ev["summary"]
                    schedules.append({
                        "id": str(ev["uid"]),
                        "calendarId": project,
                        "isAllDay": 1,
                        "title": str(name),
                        "category": 'time',
                        "start": str(ev["dtstart"].dt),
                        "end": str(ev["dtend"].dt - timedelta(1))  # XX multidays
                    })

        #import ipdb; ipdb.set_trace()
        return render_template('calendar.html', stats=json.loads(json.dumps(stats)), schedules=schedules, members=members)

    @app.route("/change", methods=['POST'])
    def change():
        calendar = Controller.get_calendar()
        changes = request.get_json()
        for uid in changes["deleted"]:
            pass # XX


        for schedule in changes["created"]:
            c = iCalendar()
            c.add('prodid', '-//Schedule shift//csirt.cz//')
            c.add('version', '2.0')
            event = iEvent()
            event.add('uid', schedule["id"])
            event.add('summary', schedule["calendarId"] + " " + schedule["title"])
            event.add('dtstart', parse(schedule["start"]["_date"]).astimezone().date())
            event.add('dtend', parse(schedule["end"]["_date"]).astimezone().date() + timedelta(1))
            c.add_component(event)
            calendar.add_event(c.to_ical().decode("utf-8"))

        return "Saved"
