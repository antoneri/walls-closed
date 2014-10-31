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
    res = urlopen(url)
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


def get_entries(html):
    year_pattern = re.compile(r"(20\d\d)")
    pattern = re.compile(r"""(?P<day>\d{1,2})
        \s*(?P<month>jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)
        \s*(?P<start>\d{1,2}:\d\d)-(?P<end>\d{1,2}:\d\d)
        \s*(?P<summary>.+)""", re.VERBOSE)

    entries = []
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
            entries.append({ "start": start, "end": end, "summary": summary })

    return entries


def to_ical(entries):
    cal = Calendar()
    cal.add("prodid", "-//walls-closed//antoneri.github.io//")
    cal.add("version", "2.0")

    for entry in entries:
        event = Event()
        event.add("summary", entry["summary"])
        event.add("dtstamp", entry["start"])
        event.add("dtstart", entry["start"])
        event.add("dtend", entry["end"])
        cal.add_component(event)

    return cal.to_ical().decode()


class cached(object):
    def __init__(self, fun):
        self.fun = fun

    def __call__(self):
        data = cache.get("ical")

        if data is None:
            data = self.fun()
            cache.set("ical", data, timeout=5 * 60)

        return data


@cached
def get_ical():
    try:
        print("Fetching html...")
        html = get_html(URL)
        print("Parsing html...")
        entries = get_entries(html)

        if not entries:
            raise Exception("could not parse html")

        print("Generating iCalendar...")
        return to_ical(entries)

    except Exception as e:
        print("Error: {}".format(e))

    return None


@app.route("/")
def index():
    return Response(response=get_ical(), mimetype="text/calendar")

if __name__ == "__main__":
    app.run()
