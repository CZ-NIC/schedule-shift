
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
