'use strict';

/* eslint-disable require-jsdoc, no-unused-vars */

var CalendarList = [];

let colors = ['#9e5fff', '#00a9ff']
let color_i = 0;

function CalendarInfo() {
    this.id = null;
    this.name = null;
    this.checked = true;
    this.color = '#ffffff';
    this.dragBgColor = this.borderColor = this.bgColor = colors[color_i++];
}

function addCalendar(calendar) {
    CalendarList.push(calendar);
}

function findCalendar(id) {
    var found;

    CalendarList.forEach(function(calendar) {
        if (calendar.id === id) {
            found = calendar;
        }
    });

    return found;
}

function hexToRGBA(hex) {
    var radix = 16;
    var r = parseInt(hex.slice(1, 3), radix),
        g = parseInt(hex.slice(3, 5), radix),
        b = parseInt(hex.slice(5, 7), radix),
        a = parseInt(hex.slice(7, 9), radix) / 255 || 1;
    var rgba = 'rgba(' + r + ', ' + g + ', ' + b + ', ' + a + ')';

    return rgba;
}

CalendarList.checkedId = null;