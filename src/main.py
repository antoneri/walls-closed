#!/usr/bin/env python3
import re
from datetime import datetime
from urllib.request import urlopen
from bs4 import BeautifulSoup, SoupStrainer
from icalendar import Calendar, Event

def get_html(url):
    # TODO cache
    try:
        res = urlopen(URL)
    except URLError as e:
        raise

    return res.read()


def stripped_lines(html):
    constraint = SoupStrainer(id="post-35")
    soup = BeautifulSoup(html, "html.parser", parse_only=constraint)
    return soup.stripped_strings


def timestamp(year, month, day, time):
    format_str = "{} {} {} {}".format(year, month, day, time)
    try:
        return datetime.strptime(format_str, "%Y %m %d %H:%M").timestamp()
    except (ValueError, OverflowError) as e:
        raise


def month_num(month):
    months = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun',
              'jul', 'aug', 'sep', 'okt', 'nov', 'dec']
    order = {val: key for key, val in enumerate(months, start=1)}
    try:
        return order[month]
    except KeyError as e:
        print("Regex parser broke?")
        raise


class Data(dict):
    def append(self, year, month, day, start, stop, text):
        entry = {day: {'start': start, 'stop': stop, 'text': text}}
        self[year].setdefault(month, {}).update(entry)
        return self


def parse(html):
    year_pattern = re.compile(r"(20\d\d)")
    pattern = re.compile(r"""(?P<day>\d{1,2})
                         \s*
                         (?P<month>jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)
                         \s*
                         (?P<start>\d{1,2}:\d\d)
                         -
                         (?P<stop>\d{1,2}:\d\d)
                         \s*
                         (?P<text>.+)""", re.VERBOSE)

    data = Data()
    curr_year = None

    for line in stripped_lines(html):
        match = year_pattern.search(line)
        if match and not int(match.group(0)) in data:
            curr_year = int(match.group(0))
            data[curr_year] = {}
            continue

        match = pattern.search(line)
        if match and curr_year is not None and curr_year in data:
            day = match.group('day')
            month = month_num(match.group('month'))
            start = timestamp(curr_year, month, day, match.group('start'))
            stop = timestamp(curr_year, month, day, match.group('stop'))
            data.append(curr_year, month, int(day), start, stop, match.group('text'))

    return data


def to_ical(data):
    cal = Calendar()
    cal.add('prodid', '-//walls-closed//antoneri.github.io//')
    cal.add('version', '2.0')

    for y, yeardata in data.items():
        for m, monthdata in yeardata.items():
            for d, eventdata in monthdata.items():
                event = Event()
                event.add('dtstamp', datetime.fromtimestamp(eventdata['start']))
                event.add('dtstart', datetime.fromtimestamp(eventdata['start']))
                event.add('dtend', datetime.fromtimestamp(eventdata['stop']))
                event.add('summary', eventdata['text'])
                cal.add_component(event)

    return cal.to_ical()


if __name__ == "__main__":
    URL = "http://www.iksu.se/traning/traningsutbud/klattring/"
    html = get_html(URL)
    data = parse(html)

    if not data:
        raise StandardError("Page source changed?")

    with open("walls-closed.ics", "wb") as outfile:
        outfile.write(to_ical(data))
