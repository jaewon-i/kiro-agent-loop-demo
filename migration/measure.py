#!/usr/bin/env python3
"""Sensor: measures how many source files still use the legacy date/time API.

Legacy = java.util.Date, Calendar, GregorianCalendar, TimeZone, java.text.SimpleDateFormat/DateFormat,
java.sql.Date/Timestamp. Comments and string literals are ignored so a mention in a comment does not count.
Prints a human-readable report, or JSON with --json. Exit code is always 0 (this only measures).
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / 'src'
LEGACY = re.compile(r'\b(Date|Calendar|GregorianCalendar|TimeZone|SimpleDateFormat|DateFormat|Timestamp)\b')
NOISE = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])\'', re.S)


def legacy_hits(path):
    code = NOISE.sub(' ', path.read_text())
    return sorted(set(LEGACY.findall(code)))


def measure():
    files = {p.name: legacy_hits(p) for p in sorted(SRC.glob('*.java'))}
    remaining = [name for name, hits in files.items() if hits]
    return {'total': len(files), 'remaining': remaining, 'detail': files}


if __name__ == '__main__':
    m = measure()
    if '--json' in sys.argv:
        print(json.dumps(m, indent=2))
    else:
        print(f"legacy date API: {len(m['remaining'])}/{m['total']} files remaining")
        for name in m['remaining']:
            print(f"  - {name}: {', '.join(m['detail'][name])}")
