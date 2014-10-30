#!/usr/bin/env python3
import re
import sys
import time
from datetime import datetime
from urllib.request import urlopen
from bs4 import BeautifulSoup, SoupStrainer
from icalendar import Calendar, Event
from flask import Flask, Response
from werkzeug.contrib.cache import SimpleCache

URL = "http://www.iksu.se/traning/traningsutbud/klattring/"
app = Flask(__name__)
cache = SimpleCache()


def get_html(url):
    res = urlopen(URL)
    return res.read()


def stripped_lines(html):
    constraint = SoupStrainer(id="post-35")
    soup = BeautifulSoup(html, "html.parser", parse_only=constraint)
    return soup.stripped_strings


def dt_obj(year, month, day, time):
    date = " ".join(map(str, [year, month, day, time]))
    return datetime.strptime(date, "%Y %m %d %H:%M")


def month_num(month):
    months = ["jan", "feb", "mar", "apr", "maj", "jun",
              "jul", "aug", "sep", "okt", "nov", "dec"]
    order = {val: key for key, val in enumerate(months, start=1)}
    return order[month]


def parse(html):
    year_pattern = re.compile(r"(20\d\d)")
    pattern = re.compile(r"""(?P<day>\d{1,2})
        \s*(?P<month>jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)
        \s*(?P<start>\d{1,2}:\d\d)-(?P<end>\d{1,2}:\d\d)
        \s*(?P<summary>.+)""", re.VERBOSE)

    data = []
    year = None

    for line in stripped_lines(html):
        match = year_pattern.search(line)
        if match:
            year = match.group(0)
            continue

        match = pattern.search(line)
        if match and year is not None:
            (day, month, start, end, summary) = match.groups()
            month = month_num(month)
            start = dt_obj(year, month, day, start)
            end = dt_obj(year, month, day, end)
            data.append({ "start": start, "end": end, "summary": summary })

    return data


def to_ical(data):
    cal = Calendar()
    cal.add("prodid", "-//walls-closed//antoneri.github.io//")
    cal.add("version", "2.0")

    for d in data:
        event = Event()
        event.add("summary", d["summary"])
        event.add("dtstamp", d["start"])
        event.add("dtstart", d["start"])
        event.add("dtend", d["end"])
        cal.add_component(event)

    return cal.to_ical()


class cached(object):
    def __init__(self, fun):
        self.fun = fun

    def __call__(self):
        ret = cache.get("ical")
        if ret is None:
            ret = self.fun()
            cache.set("ical", ret, timeout=5 * 60)
        return ret


@cached
def get_ical():
    try:
        print("Fetching data...")
        html = get_html(URL)
        print("Parsing html...")
        data = parse(html)

        if not data:
            raise Exception("could not parse data")

        print("Generating ICS...")
        return to_ical(data).decode()

    except Exception as e:
        print("Error: {}".format(e))

    return None


@app.route("/")
def walls_closed():
    return Response(response=get_ical(), mimetype="text/calendar")
