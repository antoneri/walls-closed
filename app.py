#!/usr/bin/env python3
import re
import sys
import time
from datetime import datetime
from urllib.request import urlopen
from bs4 import BeautifulSoup, SoupStrainer
from icalendar import Calendar, Event


def get_html(url):
    # TODO cache
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


if __name__ == "__main__":
    URL = "http://www.iksu.se/traning/traningsutbud/klattring/"
    OUTPUT = "walls-closed.ics"

    try:
        print("Fetching data...")
        html = get_html(URL)
        print("Parsing html...")
        data = parse(html)

        if data:
            print("Generating ICS...")
            with open(OUTPUT, "wb") as outfile:
                outfile.write(to_ical(data))
        else:
            raise Exception("could not parse data")

    except Exception as e:
        sys.exit("Error: {}".format(e))

