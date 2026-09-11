"""Evaluate this site's literal-prefix robots policy using most-specific rules."""

from urllib.robotparser import RobotFileParser


def parse_policy(text):
    # RobotFileParser otherwise uses the first matching rule, not the longest.
    # Fail closed if future wildcard rules need a fuller REP implementation.
    for line in text.splitlines():
        field, separator, value = line.partition(':')
        if separator and field.strip().lower() in ('allow', 'disallow'):
            value = value.split('#', 1)[0].strip()
            if '*' in value or '$' in value:
                raise ValueError('Wildcard robots rules require a full REP parser')
    parser = RobotFileParser()
    parser.parse(text.splitlines())
    entries = list(parser.entries)
    if parser.default_entry:
        entries.append(parser.default_entry)
    for entry in entries:
        entry.rulelines.sort(key=lambda rule: (len(rule.path), rule.allowance), reverse=True)
    parser.entries.sort(key=lambda entry: max(map(len, entry.useragents)), reverse=True)
    return parser
