
Easy work scheduling. We had two projects that needed attention every day.
Single page, single calendar → synchronized via CalDAV.
tui.calendar to CalDAV
no authorisation

Čertí služby csirtmaster@csirt.cz

cron

normalni dny
∀ vsedni den prijde mail tomu, komu zacina sichta, nebo pokud nikdo sichtu nema
x.py notify --project csirtmaster --notify-owner-if-start --notify-if-empty certi@nic.cz

jednou v pondeli za dva tydny
,doubleweek-project --project csirtmaster,root --notify-owner-if-start --notify-if-empty certi@nic.cz

x.py notify --project dayily-project,doubleweek-project --


Every second week

    0 6 * * Tue expr `date +\%W` \% 2 > /dev/null || x.py --notify-project


# Screenshots

# Deployment

Cron:
5 30 * * 1-5 python3.6 /opt/schedule-shift/scheduler.py notify all starting --send


Deprecated?

[Third project]
# "name" = True (person works for the project) OR start day, (end date, (weight)) OR list of (start date, end date OR None, coeficient). You may use multiline strings.
# optional whole_week
whole_week = yes
John Smith = True # John is working since ever
Peter = 2019-01-01
Laura = 2017-01-01, 2017-06-01 # Laura worked few months in 2017
    2019-01-01, None, 0.5 # Laura started again in 2019 on a half-shift
