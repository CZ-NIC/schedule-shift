
__help__ = """
shift owner: nobody (no shift today) | starting (new owner) | running (any owner) | ending (last day of the owner) 
mail recipient: owner (send e-mail only to them) | all (everybody in the project) | e-mail address (string)
"""

def generate_stats():
    team = []
    person_available = {}  # {person: True OR [(date range, weight)], } # {available days: weight, }
    for project in config:
        if project == "general":
            pass
        elif project == "team":
            team = list(config["team"])
        else:
            for person in config[project]:
                if person == "whole_week":
                    continue
                val = config[project].get(person)
                for range in val.split("\n"):  # [(start_date, end_date, weight), ]
                    if range in ("True", "true", "yes"):
                        person_available[project][person] = True  # works for the project every day
                        break
                    else:
                        start_date, end_date, weight = islice(chain(range, repeat(None)), 3)
                        if not end_date:
                            end_date = pd.datetime.today()
                        if not weight:
                            weight = 1
                        person_available[project][person].append(pd.date_range(start=start_date, end=end_date), weight)

    # XXX
    # config["project number 1"].getboolean("whole_week")
    # a = dict(config["project number 1"])
    # if "whole_week" in
    #     del a["as"]

    # loop events to determine who has got the advantage
    sogo_events = []  # XXX
    stats = defaultdict(dict)
    for _ in sogo_events:
        project = "Root"
        event_person = "Edvard"  # XX
        event_day_count = 2  # XX
        for person in stats[project]:
            if event_person == person:
                continue
            # if Person(project, person)
            if person_available[project][person] is not True:
                for range in person_available[project][person]:
                    if event_day in range:
                        break  # they was there
                else:
                    continue
            stats[project][event_person] += event_day_count * weight
    stats[project] = sorted(stats[project], reverse=True)
    min_ = next(iter(stats[project]))
    for person in stats[project]:
        stats[project][person] = abs(stats[project][person] - min_)

    team
    json.dump(stats)  # {"project": {"john": 3,}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__help__)
    parser.add_argument('--notify', action='append', help='<project name> <shift owner> <mail recipient> (<shift owner> <mail recipient> ...)',
                        nargs='+')
    args = parser.parse_args()


    if args.notify:
        # Semantics of notify
        # project all(default)|name
        #   anytime(default) = nobody→all,anybody→e-mail
        #   if nobody → all(default)|e-mail
        #   if anybody → running(default)|starting|ending owner(default)|all|e-mail
        #   comma , → repetition, another project ahead

        for arg in sys.argv:
            if arg


    if len(args.notify[0]) % 2 == 0:
            print("Wrong notify parameters count.")
            quit()
        #project = args.notify[0].pop(0)
        it = iter(args.notify[0])
        for case, recipient in zip(it, it):
            print(case, recipient)

        #sogo_calendar = get_sogo_calendar
        #todays_event_name

    #generate_stats()