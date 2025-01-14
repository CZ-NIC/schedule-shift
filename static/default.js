'use strict';

/* eslint-disable require-jsdoc */
/* eslint-env jquery */
/* global moment, tui, chance */
/* global findCalendar, CalendarList, ScheduleList, generateSchedule */

projects = projects || {};
var changes = { "deleted": [], "created": [] };

// Count working days https://stackoverflow.com/a/48938331/2036148
function getNumWorkDays(startDate, endDate) {
    var numWorkDays = 0;
    var currentDate = new Date(startDate);
    while (currentDate <= endDate) {
        // Skips Sunday and Saturday
        if (currentDate.getDay() !== 0 && currentDate.getDay() !== 6) {
            numWorkDays++;
        }
        currentDate = currentDate.addDays(1);
    }
    return numWorkDays;
}

// Update Person's count (number of working days that they're in the lead)
function person_count(person, count) {
    let $counter = $(".lnb-calendars-item input[name=person][value='" + person + "'] + span + strong > .count");
    if ($counter) {
        const recounted = $counter.data("count") + count * $counter.data("coefficient")
        $counter.data("count", recounted)
        $counter.text(Math.round(recounted))
    }
}


// Initialize calendars
for (const project_id in projects) {
    let calendar = new CalendarInfo();
    calendar.id = calendar.name = project_id;
    console.log('Line 269 project_id, calendar.id(): ', project_id, calendar.id);
    addCalendar(calendar);
    console.log('Line 271 calendar(): ', calendar);

    // calendar = new CalendarInfo();
    // calendar.id = calendar.name = project_id + "2";
    // addCalendar(calendar);
    if (!CalendarList.checkedId) {
        CalendarList.checkedId = project_id;
    }
}


(function (window, Calendar) {
    let cal, resizeThrottled;
    let useDetailPopup = true;
    let selectedCalendar;

    cal = new Calendar('#calendar', {
        defaultView: 'month',
        useCreationPopup: false, //useCreationPopup,
        useDetailPopup: useDetailPopup,
        calendars: CalendarList,
        month: {
            startDayOfWeek: 1,
            workweek: true
        }
    });

    Date.prototype.addDays = function (days) {
        let date = new Date(this.valueOf());
        date.setDate(date.getDate() + days);
        return date;
    };


    // event handlers
    cal.on({
        'clickMore': function (e) {
            console.log('clickMore', e);
        },
        'clickSchedule': function (e) {
            console.log('clickSchedule', e);
        },
        'clickDayname': function (date) {
            console.log('clickDayname', date);
        },
        'beforeCreateSchedule': function (scheduleData) {
            console.log('beforeCreateSchedule', scheduleData);

            scheduleData.title = document.querySelector("#lnb-calendars input[name=person]:checked").value;
            scheduleData.calendarId = CalendarList.checkedId;
            // XX whole week only events possibility
            // if (CalendarList.checkedId === "") { //
            //     scheduleData.start = scheduleData.start.toDate().addDays(1 - scheduleData.start.getDay()); // monday
            //     scheduleData.end = scheduleData.start.addDays(4);
            // }
            let calendar = scheduleData.calendar || findCalendar(scheduleData.calendarId);
            let schedule = {
                id: String(chance.guid()),
                title: scheduleData.title,
                start: scheduleData.start,
                end: scheduleData.end,
                category: 'allday'
            };
            if (calendar) {
                schedule.calendarId = calendar.id;
            }

            cal.createSchedules([schedule]);
            // schedule = Object.assign({}, schedule);
            // schedule.start = schedule.start.getTime();
            // schedule.end = schedule.end.getTime();
            changes["created"].push(schedule);
            person_count(schedule.title, getNumWorkDays(schedule.start, schedule.end));
            savable();
        },
        'beforeUpdateSchedule': function (e) {
            console.log('beforeUpdateSchedule', e);
            if (e.start && e.end) {
                person_count(e.schedule.title, getNumWorkDays(e.start, e.end) - getNumWorkDays(e.schedule.start, e.schedule.end));
                e.schedule.start = e.start;
                e.schedule.end = e.end;
                console.log('Line 101 e.start(): ', e);
                cal.updateSchedule(e.schedule.id, e.schedule.calendarId, e.schedule);
                changes["created"].push(e.schedule);
                for (let schedule of ScheduleList) {
                    // we have to manually replace event in ScheduleList
                    // – otherwise when we change month, the schedule would have been displayed with old parameters
                    if (schedule.id === e.schedule.id) {
                        schedule.start = e.schedule.start;
                        schedule.end = e.schedule.end;
                    }
                }
            }
            savable();
        },
        'beforeDeleteSchedule': function (e) {
            // cancel updates of this schedule (so that it's not recreated when immediately deleted)
            changes["created"] = changes["created"].filter(change => change.id !== e.schedule.id);
            ScheduleList = ScheduleList.filter(schedule => schedule.id != e.schedule.id);
            changes["deleted"].push(e.schedule.id);
            console.log('beforeDeleteSchedule', e);
            cal.deleteSchedule(e.schedule.id, e.schedule.calendarId);
            person_count(e.schedule.title, -getNumWorkDays(e.schedule.start, e.schedule.end));// recount days
            savable();
        },
        'afterRenderSchedule': function (e) {
            let schedule = e.schedule;
            // var element = cal.getElement(schedule.id, schedule.calendarId);
            // console.log('afterRenderSchedule', element);
        },
        'clickTimezonesCollapseBtn': function (timezonesCollapsed) {
            console.log('timezonesCollapsed', timezonesCollapsed);

            if (timezonesCollapsed) {
                cal.setTheme({
                    'week.daygridLeft.width': '77px',
                    'week.timegridLeft.width': '77px'
                });
            } else {
                cal.setTheme({
                    'week.daygridLeft.width': '60px',
                    'week.timegridLeft.width': '60px'
                });
            }

            return true;
        }
    });

    let dirty = false;
    $(".save-button").click(function () {
        $(".save-button").prop("disabled", true);

        // assure ICS date – my UTC server got 22:00 instead of 00:00, stripped the time and shifted the schedule date
        for (let change of changes["created"]) {
            // for(let pos of ["start", "end"]) {
            //     let d = change[pos].toDate();
            //     change[pos+"-ics"] = d.getFullYear() + ('0' + (d.getMonth() + 1)).slice(-2) + ('0' + d.getDate()).slice(-2);
            // }
            //change["end-ics"] += "2359"
            let date2ics = (d) => {
                return d.getFullYear() + ('0' + (d.getMonth() + 1)).slice(-2) + ('0' + d.getDate()).slice(-2);
            };

            // Different DTEND formats: days 2019-03-02 and 2019-03-03 in SoGo 2019-03-02 – 04, in Tui.Calendar 2019-03-02 – 03
            change["start-ics"] = date2ics(change.start._date);
            change["end-ics"] = date2ics(change.end._date.addDays(1));
        }
        $.ajax({
            "url": "/change",
            "method": "post",
            "data": JSON.stringify(changes),
            "contentType": "application/json",
            "success": (data) => {
                dirty = false;
                //X$("#menu-navi [data-action!=save]").prop("disabled", false)
                changes = { "deleted": [], "created": [] }; // reset changelog
                alert(data);
            }
        });
    });

    function savable() {
        //X$("#menu-navi [data-action!=save]").prop("disabled", true); // XX we have to save before changing a single month :(
        $(".save-button").prop("disabled", false);
        dirty = true;
    }

    window.onbeforeunload = function () {
        if (dirty) {
            return "Unsaved changes. Are you sure?";
        }
    }


    function buildPeopleNames() {
        var html = [];
        for (let [project_id, project] of Object.entries(projects)) {
            if (project_id === CalendarList.checkedId) {
                const minimal_score = Math.min(...Object.values(project).map(({ score }) => score))
                console.log("Schedule-shift log", minimal_score, Object.values(project), Object.values(project).map(({ score }) => score))
                for (const [name, person] of Object.entries(project)) {
                    const score = Math.round(person.score)

                    const style = score > 0 ? "" : " class=suggested";
                    const bal = Math.round(person.balance)

                    html.push(`<label${style}>
                        <input name="person" type="radio" value="${name}" ${style ? "checked" : ""}>
                        <span></span>
                        <strong title="relative count: +${score} days ahead of the last one">
                            ${name} <span class="count" data-count="${bal}" data-coefficient="${person.coefficient}">${bal}</span>
                        </strong>
                    </label>
                    <br />`);
                }
                break;
            }
        }
        document.querySelector("#lnb-calendars > div > .lnb-calendars-item").innerHTML = html.join("\n");
    }

    function refreshScheduleVisibility() {
        var calendarElements = Array.prototype.slice.call(document.querySelectorAll('#calendarList input'));

        CalendarList.forEach(function (calendar) {
            cal.toggleSchedules(calendar.id, !calendar.checked, false);
        });

        cal.render(true);

        calendarElements.forEach(function (input) {
            var span = input.nextElementSibling;
            span.style.backgroundColor = input.checked ? span.style.borderColor : 'transparent';
        });
    }


    function setRenderRangeText() {
        var renderRange = document.getElementById('renderRange');
        var options = cal.getOptions();
        var viewName = cal.getViewName();
        var html = [];
        if (viewName === 'day') {
            html.push(moment(cal.getDate().getTime()).format('YYYY.MM.DD'));
        } else if (viewName === 'month' &&
            (!options.month.visibleWeeksCount || options.month.visibleWeeksCount > 4)) {
            html.push(moment(cal.getDate().getTime()).format('YYYY.MM'));
        } else {
            html.push(moment(cal.getDateRangeStart().getTime()).format('YYYY.MM.DD'));
            html.push(' ~ ');
            html.push(moment(cal.getDateRangeEnd().getTime()).format(' MM.DD'));
        }
        renderRange.innerHTML = html.join('');
    }

    function setSchedules() {
        cal.clear();
        //generateSchedule(cal.getViewName(), cal.getDateRangeStart(), cal.getDateRangeEnd());
        cal.createSchedules(ScheduleList);
        refreshScheduleVisibility();
    }

    function setEventListener() {
        $('#menu-navi').on('click', function (e) {
            var action = getDataAction(e.target);
            switch (action) {
                case 'move-prev':
                    cal.prev();
                    break;
                case 'move-next':
                    cal.next();
                    break;
                case 'move-today':
                    cal.today();
                    break;
                default:
                    return;
            }
            setRenderRangeText();
            setSchedules();
        });
        //$('.dropdown-menu a[role="menuitem"]').on('click', onClickMenu);
        $('#lnb-calendars #calendarList').on('change', function (e) {
            CalendarList.checkedId = e.target.value;
            let calendarElements = Array.prototype.slice.call(document.querySelectorAll('#calendarList input'));
            calendarElements.forEach(function (input) {
                if (input.value !== CalendarList.checkedId) {
                    input.checked = false;
                }
            });
            buildPeopleNames();
            refreshScheduleVisibility();
        });

        $('#dropdownMenu-calendars-list').on('click', function (e) {
            var target = $(e.target).closest('a[role="menuitem"]')[0];
            var calendarId = getDataAction(target);
            var calendarNameElement = document.getElementById('calendarName');
            var calendar = findCalendar(calendarId);
            var html = [];

            html.push('<span class="calendar-bar" style="background-color: ' + calendar.bgColor + '; border-color:' + calendar.borderColor + ';"></span>');
            html.push('<span class="calendar-name">' + calendar.name + '</span>');

            calendarNameElement.innerHTML = html.join('');

            selectedCalendar = calendar;
        });

        window.addEventListener('resize', resizeThrottled);
    }

    function getDataAction(target) {
        return target.dataset ? target.dataset.action : target.getAttribute('data-action');
    }

    resizeThrottled = tui.util.throttle(function () {
        cal.render();
    }, 50);

    window.cal = cal;


    buildPeopleNames();


    //setDropdownCalendarType();
    setRenderRangeText();
    setSchedules();
    setEventListener();
})(window, tui.Calendar);

// set calendars
(function () {

    var calendarList = document.getElementById('calendarList');
    var html = [];

    CalendarList.forEach(function (calendar) {
        console.log('Line 298 CalendarList.checkedId(): ', CalendarList.checkedId === calendar.id);

        html.push('<div class="lnb-calendars-item"><label>' +
            `<input type="checkbox" class="tui-full-calendar-checkbox-round" value="${calendar.id}" ${calendar.id === CalendarList.checkedId ? "checked" : ""}>` +
            `<span style="border-color:${calendar.borderColor}; background-color: ${calendar.id === CalendarList.checkedId ? calendar.borderColor : "transparent"};"></span>` +
            '<span>' + calendar.name + '</span>' +
            '</label></div>'
        );
    });
    calendarList.innerHTML = html.join('\n');
})();
