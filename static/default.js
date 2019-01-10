'use strict';

/* eslint-disable require-jsdoc */
/* eslint-env jquery */
/* global moment, tui, chance */
/* global findCalendar, CalendarList, ScheduleList, generateSchedule */


var stats = {"Root": {"Edvard": 3, "Petr": 2}, "Csirtmaster": {"Edvard": 1, "Petr": 4}};


(function (window, Calendar) {
    var cal, resizeThrottled;
    var useCreationPopup = true;
    var useDetailPopup = true;
    var datePicker, selectedCalendar;

    cal = new Calendar('#calendar', {
        defaultView: 'month',
        useCreationPopup: false, //useCreationPopup,
        useDetailPopup: useDetailPopup,
        calendars: CalendarList,
        month: {startDayOfWeek: 1}
    });


    Date.prototype.addDays = function (days) {
        var date = new Date(this.valueOf());
        date.setDate(date.getDate() + days);
        return date;
    }

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
        'beforeCreateSchedule': function (e) {
            console.log('beforeCreateSchedule', e);

            e.title = document.querySelector("#lnb-calendars input[name=person]:checked").value;
            e.calendarId = CalendarList.checkedId;
            if (CalendarList.checkedId === "Root") { // XX
                // Root
                e.start = e.start.toDate().addDays(1 - e.start.getDay()) // monday
                e.end = e.start.addDays(4);
            } else {

            }
            console.log('Line 62 e(): ', e);

            saveNewSchedule(e);
        },
        'beforeUpdateSchedule': function (e) {
            console.log('beforeUpdateSchedule', e);
            e.schedule.start = e.start;
            e.schedule.end = e.end;
            cal.updateSchedule(e.schedule.id, e.schedule.calendarId, e.schedule);
        },
        'beforeDeleteSchedule': function (e) {
            console.log('beforeDeleteSchedule', e);
            cal.deleteSchedule(e.schedule.id, e.schedule.calendarId);
        },
        'afterRenderSchedule': function (e) {
            var schedule = e.schedule;
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


    function onClickNavi(e) {
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
    }


    function onChangeNewScheduleCalendar(e) {
        var target = $(e.target).closest('a[role="menuitem"]')[0];
        var calendarId = getDataAction(target);
        var calendarNameElement = document.getElementById('calendarName');
        var calendar = findCalendar(calendarId);
        var html = [];

        html.push('<span class="calendar-bar" style="background-color: ' + calendar.bgColor + '; border-color:' + calendar.borderColor + ';"></span>');
        html.push('<span class="calendar-name">' + calendar.name + '</span>');

        calendarNameElement.innerHTML = html.join('');

        selectedCalendar = calendar;
    }


    function saveNewSchedule(scheduleData) {
        var calendar = scheduleData.calendar || findCalendar(scheduleData.calendarId);
        var schedule = {
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

        //refreshScheduleVisibility();
    }

    function buildPeopleNames() {
        console.log('Line 152 "Zde", stats(): ', "Zde", stats);
        var html = [];
        for (let project in stats) {
            console.log('Line 155 "ID"(): ', "ID", project,CalendarList.checkedId);
            if (project === CalendarList.checkedId) {
                for (let person in stats[project]) {
                    html.push(`<label>
                        <input name="person" type="radio" value="${person}" checked>
                        <span></span>
                        <strong>${person} ${stats[project][person]}</strong>
                    </label>
                    <br />`);
                }
                break;
            }
        }
        document.querySelector("#lnb-calendars > div > .lnb-calendars-item").innerHTML = html.join("\n");
    }

    function onChangeCalendars(e) {
        CalendarList.checkedId = e.target.value;
        var calendarElements = Array.prototype.slice.call(document.querySelectorAll('#calendarList input'));
        calendarElements.forEach(function (input) {
            if (input.value !== CalendarList.checkedId) {
                input.checked = false;
            }
        });
        buildPeopleNames();
        refreshScheduleVisibility();
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
        $('#menu-navi').on('click', onClickNavi);
        //$('.dropdown-menu a[role="menuitem"]').on('click', onClickMenu);
        $('#lnb-calendars #calendarList').on('change', onChangeCalendars);

        //$('#btn-save-schedule').on('click', onNewSchedule);
        //$('#btn-new-schedule').on('click', createNewSchedule);

        $('#dropdownMenu-calendars-list').on('click', onChangeNewScheduleCalendar);

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
        html.push('<div class="lnb-calendars-item"><label>' +
            `<input type="checkbox" class="tui-full-calendar-checkbox-round" value="${calendar.id}" ${calendar.id === CalendarList.checkedId ? "checked" : ""}>` +
            `<span style="border-color:${calendar.borderColor}; background-color: ${calendar.id === CalendarList.checkedId ? calendar.borderColor : "transparent"};"></span>` +
            '<span>' + calendar.name + '</span>' +
            '</label></div>'
        );
    });
    calendarList.innerHTML = html.join('\n');

})();
