#!/usr/bin/env python3
import argparse
import json
import logging
import re
import sys
from datetime import timedelta, datetime
from sys import exit

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

If --send flag is not present, no e-mails are sent.

Examples – send the notification:
     to all members of project my_project:
        ./scheduler.py notify my_project any all
    to all members of project my_project and of another_project when anybody shift's ending:
        ./scheduler.py notify my_project ending all, another_project ending all
    to the shift owner if the shift is starting but don't send info if no shift is taken
        ./scheduler.py notify my_project starting owner mute
    to an e-mail when this is the last day of a shift on any project
        ./scheduler.py notify all ending example@example.com

"""

app = Flask("shift-schedule")
e_mail_regex = re.compile(
    r'^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$')
config = Config()

def today():
    return datetime.today().date()


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
        if project in config.projects:
            return project, name
    except ValueError:
        pass
    # this event is not part of any here-defined project
    return None, event["summary"]


def info():
    schedules = []
    projects = config.projects

    for event in caldav2events(config.get_events()):
        project, name = project_and_name(event)  # parse out the member name

        if project:
            # count number of working days
            # Different DTEND formats: We have to shorten the end date:
            # Ex: days 2019-03-02 and 2019-03-03 in SoGo 2019-03-02 – 04, in Tui.Calendar 2019-03-02 – 03
            dates = rrule.rruleset()
            dates.rrule(rrule.rrule(rrule.DAILY, dtstart=event["dtstart"].dt, until=(
                event["dtend"].dt - timedelta(1))))
            dates.exrule(rrule.rrule(rrule.DAILY, byweekday=(
                rrule.SA, rrule.SU), dtstart=event["dtstart"].dt))
            projects[project][name].score += dates.count() * \
                projects[project][name].coefficient

            # print(str(event["uid"]), str(event["dtstart"].dt), str(event["dtend"].dt))

            schedules.append({
                "id": str(event["uid"]),
                "calendarId": project,
                "isAllDay": 1,
                "title": str(name),
                "category": 'time',
                "start": str(event["dtstart"].dt),
                # see above: different DTEND formats
                "end": str(event["dtend"].dt - timedelta(1))
            })

    # modify projects so that we see relative number of worked out days (to see who should take the shift)
    for pr_name, project in projects.items():
        members = project.values()
        m = min(x.score for x in members)
        balance = sum(x.score for x in members) / len(members)
        balance = balance - config.env.projects[pr_name].get("balance_delta",0)
        for member in members:
            member.balance = member.score - balance
            member.score -= m
    return projects, schedules


@app.route("/")
def homepage():
    projects, schedules = info()
    return render_template('calendar.html',
                           projects=json.loads(json.dumps(
                               projects, default=lambda x: x.__dict__)),
                           schedules=schedules)

@app.route("/api/")
def api_help():
    return '<a href="today">today</a> – JSON {project: today\'s name}'

@app.route("/api/today")
def api_today():
    return {p_n[0]: p_n[1] for event in get_events()
            if (p_n := project_and_name(event))}

@app.route("/change", methods=['POST'])
def change():
    """ Change (create) or delete an event by POST request """
    calendar = config.calendar()
    changes = request.get_json()
    for uid in changes["deleted"]:
        try:
            calendar.event_by_uid(uid).delete()
            print("Deleted:", uid)
        except caldav.lib.error.NotFoundError:
            # as of 2022-03-23 I was unable to use event_by_uid due to an AuthorizationError.
            # But searching whole calendar for the event still works.
            # This painful piece of code compares events data for UID
            # and then uses its original reference to be deleted.
            # In the future, calendar.event_by_uid might start working again
            # (see the logs for "Deleted" keyword) and this can be trashed.
            events = config.get_events()
            for ref, ev in zip(events, caldav2events(events)):
                if ev["uid"] == uid:
                    ref.delete()
                    print("Deleted the hard way:", uid)
                    break
            # the event haven't been in the calendar, maybe was just created and deleted

    for schedule in changes["created"]:
        c = iCalendar()
        c.add('prodid', '-//Schedule shift//csirt.cz//')
        c.add('version', '2.0')
        event = iEvent()
        event.add('uid', schedule["id"])
        event.add('summary', schedule["calendarId"] + " " + schedule["title"])
        # event.add('dtstart', parse(schedule["start"]["_date"]).astimezone().date()+timedelta(1))

        # print(schedule)
        # import ipdb; ipdb.set_trace()

        event.add('dtstart', parse(schedule["start-ics"]))
        event.add('dtend', parse(schedule["end-ics"]))
        # event.add('dtstart', parse(schedule["start"]["_date"]))
        # event.add('dtend', parse(schedule["end"]["_date"]))
        c.add_component(event)
        calendar.add_event(c.to_ical().decode("utf-8"))

    return "Saved"


def get_events():
    try:
        events = list(caldav2events(
            Config().calendar().date_search(today(), today())))
    except InvalidSchema:
        logging.error(f"Invalid schema: {today()}")
        exit(1)
    return events


def cli():
    parser = argparse.ArgumentParser(description="Schedule shift via nice GUI to a SOGO calendar",
                                     formatter_class=argparse.RawTextHelpFormatter)
    # parser.add_argument('-v', '--verbose', action='store_true', help="Print out the mail contents.")
    parser.add_argument('--send', action='store_true',
                        help="Send e-mails. (By default, no mails are sent.)")
    parser.add_argument('notify', help=__help__, nargs='+')
    args = parser.parse_args()

    Config().verbose = True  # args.verbose

    if sys.argv[1] == "notify":
        events = get_events()

        # default instructions values - all projects, any state, inform owner, no fallback
        defaults = ["all", "any", "owner", None]
        instructions = []
        # we expand 'all' projects to the real project names
        for p in " ".join(args.notify[1:]).split(","):
            pp = p.strip().split(" ")
            i = pp + defaults[len(pp):]
            if i[0] in ["all", ""]:
                for pr in config.projects:
                    instructions.append((pr, *i[1:]))
            else:
                instructions.append(i)

        for project, state, who, fallback in instructions:
            # argument checks
            if project not in config.projects:
                logging.error(
                    f"Invalid project name {project}: {project} {state} {who}")
                continue
            if who not in ['owner', 'all'] and not e_mail_regex.match(who):
                logging.error(
                    f"Invalid who parameter {who}: {project} {state} {who}")
                continue
            if state not in ["any", "starting", "proceeding", "ending", "none"]:
                logging.error(
                    f"Invalid state parameter {state}: {project} {state} {who}")
                continue

            # searching for an event related to this project
            found = False
            for event in events:
                project_e, name = project_and_name(event)
                if project == project_e:
                    found = True
                    starting = event["dtstart"].dt
                    ending = (event['dtend'].dt - timedelta(1))

                    # the event may be created in SoGo, in Tui or otherwise, there might be datetime or date – we need compare date
                    if type(starting) is datetime:
                        starting = starting.date()
                    if type(ending) is datetime:
                        ending = ending.date()

                    if state in ["any", "starting"] and today() == starting:
                        status = f"starting (ending on {ending.isoformat()})"
                    elif state in ["any", "ending"] and today() == ending:
                        status = "ending"
                    elif state in ["any", "proceeding"] and today() not in [starting, ending]:
                        status = f"proceeding (ending on {ending.isoformat()})"
                    else:
                        continue

                    highlight = None
                    if who == "owner":
                        mail = config.get_mail(name)
                        highlight = project
                    elif who == "all":
                        mail = config.get_member_mails(project)
                    else:
                        mail = who
                        if mail == config.get_mail(name):  # this is the owner
                            highlight = project

                    text = f"{project} – {name} – {status}"
                    Notification.add(mail, text, highlight)

            if not found and fallback != 'mute':
                if not fallback:
                    fallback = "all" if who in ["owner", "all"] else who
                if fallback == "all":
                    fallback = config.get_member_mails(project)
                Notification.add(
                    fallback, f"{project} has no registered shift!", highlight=project)
        Notification.send(args.send)
    else:
        print(__help__)


if __name__ == "__main__":
    cli()
