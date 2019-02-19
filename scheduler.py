#!/usr/bin/env python3
import argparse
import json
import logging
import re
import sys
from datetime import timedelta, datetime

import caldav
from dateutil import rrule
from dateutil.parser import parse
from flask import Flask, render_template, request
from icalendar import Calendar as iCalendar, Event as iEvent
from requests.exceptions import InvalidSchema

from lib.config import Config
from lib.notification import Notification

__help__ = """[project_name] [shift state] [whom to write] [fallback e-mail], ...
project_name:
    'all' (default) to match all of the defined project.
    
shift state:        
    any - (default) Any state, doesn't matter whether it's starting, ending or if nobody has it.
    starting - When this is the first day of a new shift.
    proceeding - When we are in the middle of a shift.
    ending - When this is the last day of a shift.
    none - Send the notification only when nobody's got the shift planned.         
    
whom to write:
    owner - (default) Send the notification to the shift owner only if set or to all members if nobody's got the shift.        
    all - All members of a project.
    e-mail - Use this custom e-mail to notify.
    
fallback e-mail:
    Can be set to an e-mail that gets notified when nobody's got their shift planned.
    If not set, we notify the e-mail specified in 'who' parameter or all project members (if 'who' is set to 'owner' or 'all').
    If set to 'mute', nobody'll be notified.
    
If notify keyword is preceded by --debug flag, no e-mail is sent and the info is printed.  

Examples – send the notification: 
     to all members of project my_project:        
        ./scheduler.py notify my_project any all
    to all members of project my_project and of another_project when anybody shift's ending:
        ./scheduler.py notify my_project ending all, another_project ending all
    to the shift owner if the shift is starting but don't send info if no shift is taken    
        ./scheduler.py notify my_project starting owner mute
    to an e-mail when that is the last day of a shift on any project    
        ./scheduler.py notify all ending example@example.com
         
"""

app = Flask("shift-schedule")
e_mail_regex = re.compile('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$')


def caldav2events(caldav_events):
    """ Takes calendar.events() or calendar.date_search() results and generates events in a user friendlier form."""
    for event in caldav_events:
        for ev in iEvent.from_ical(event.data).subcomponents:
            if ev.name == "VEVENT":
                yield ev


# monkey patch method

def project_and_name(event):
    try:
        project, name = event["summary"].split(" ", 1)
        if project in Config.projects:
            return project, name
    except ValueError:
        pass
    return None, event["summary"]  # this event is not part of any here-defined project


iEvent.project_and_name = project_and_name


@app.route("/")
def homepage():
    calendar = Config.calendar()
    schedules = []
    projects = Config.projects

    for event in caldav2events(calendar.events()):
        project, name = event.project_and_name()  # parse out the member name
        if project:
            # count number of working days
            dates = rrule.rruleset()
            dates.rrule(rrule.rrule(rrule.DAILY, dtstart=event["dtstart"].dt, until=(event["dtend"].dt - timedelta(1))))
            dates.exrule(rrule.rrule(rrule.DAILY, byweekday=(rrule.SA, rrule.SU), dtstart=event["dtstart"].dt))
            projects[project][name] += dates.count()

            schedules.append({
                "id": str(event["uid"]),
                "calendarId": project,
                "isAllDay": 1,
                "title": str(name),
                "category": 'time',
                "start": str(event["dtstart"].dt),
                "end": str(event["dtend"].dt - timedelta(1))
            })

    # modify projects so that we see relative number of worked out days (to see who should take the shift)
    for project in projects.values():
        m = project[min(project, key=project.get)]
        for member in project:
            project[member] -= m

    return render_template('calendar.html', projects=json.loads(json.dumps(projects)), schedules=schedules)


@app.route("/change", methods=['POST'])
def change():
    calendar = Config.calendar()
    changes = request.get_json()
    for uid in changes["deleted"]:
        try:
            calendar.event_by_uid(uid).delete()
        except caldav.lib.error.NotFoundError:
            # the event haven't been in the calendar, maybe was just created and deleted
            pass

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Schedule shift via nice GUI to a SOGO calendar", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-v', '--verbose', action='store_true', help="Print out the mail contents.")
    parser.add_argument('--debug', action='store_true', help="No mails will be sent (and turns on verbose flag).")
    parser.add_argument('notify',  help=__help__, nargs='+')
    args = parser.parse_args()

    if args.debug:
        args.verbose = True
    Config.verbose = args.verbose

    if sys.argv[1] == "notify":
        today = datetime.today().date()
        try:
            events = list(caldav2events(Config.calendar().date_search(today, today)))
        except InvalidSchema:
            logging.error(f"Invalid schema: {today}")
            exit(1)

        defaults = ["all", "any", "owner", None]  # default instructions values - all projects, any state, inform owner, no fallback
        instructions = []
        # we expand 'all' projects to the real project names
        for p in " ".join(args.notify[1:]).split(","):
            pp = p.strip().split(" ")
            i = pp + defaults[len(pp):]
            print(i)
            if i[0] in ["all", ""]:
                for pr in Config.projects:
                    instructions.append((pr, *i[1:]))
            else:
                instructions.append(i)

        for project, state, who, fallback in instructions:
            # argument checks
            if project not in Config.projects:
                logging.error(f"Invalid project name {project}: {project} {state} {who}")
                continue
            if who not in ['owner', 'all'] and not e_mail_regex.match(who):
                logging.error(f"Invalid who parameter {who}: {project} {state} {who}")
                continue
            if state not in ["any", "starting", "proceeding", "ending", "none"]:
                logging.error(f"Invalid state parameter {state}: {project} {state} {who}")
                continue

            # searching for an event related to this project
            found = False
            for event in events:
                project_e, name = event.project_and_name()
                if project == project_e:
                    found = True
                    if state in ["any", "starting"] and today == event["dtstart"].dt:
                        status = "starting"
                    elif state in ["any", "ending"] and today == event["dtend"].dt:
                        status = "ending"
                    elif state in ["any", "proceeding"] and today not in [event["dtstart"].dt, event["dtend"].dt]:
                        status = "proceeding"
                    else:
                        continue

                    highlight = None
                    if who == "owner":
                        mail = Config.get_mail(name)
                        highlight = project
                    elif who == "all":
                        mail = Config.get_member_mails(project)
                    else:
                        mail = who
                        if mail == Config.get_mail(name):  # this is the owner
                            highlight = project

                    text = f"{project} – {name} – {status}"
                    Notification.add(mail, text, highlight)

            if not found and fallback != 'mute':
                if not fallback:
                    fallback = "all" if who in ["owner", "all"] else who
                if fallback == "all":
                    fallback = Config.get_member_mails(project)
                Notification.add(fallback, f"{project} has no registered shift!", highlight=project)
        Notification.send(not args.debug)
    else:
        print(__help__)
