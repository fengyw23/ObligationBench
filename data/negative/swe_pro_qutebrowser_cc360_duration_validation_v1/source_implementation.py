from pathlib import Path
p = Path('/app/qutebrowser/utils/utils.py')
s = p.read_text()
s = s.replace('import datetime\n', 'import datetime\nimport decimal\n', 1)
a = s.index('def parse_duration(duration: str) -> int:')
# This production function is the last definition in this image.
assert s[a:].strip().endswith('* 1000')
s = s[:a] + """def parse_duration(duration: str) -> int:
    \"\"\"Parse nonnegative milliseconds or h/m/s components into milliseconds.\"\"\"
    duration = duration.strip()
    if re.fullmatch(r'[0-9]+', duration):
        return int(duration)

    number = r'(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+)'
    if not re.fullmatch(r'(?:' + number + r'[hms]\\s*)+', duration):
        raise ValueError('Invalid duration: ' + repr(duration))
    factors = {'h': 3600000, 'm': 60000, 's': 1000}
    seen = set()
    total = decimal.Decimal(0)
    for value, unit in re.findall('(' + number + r')([hms])', duration):
        if unit in seen:
            raise ValueError('Repeated duration unit: ' + unit)
        seen.add(unit)
        total += decimal.Decimal(value) * factors[unit]
    return int(total)
"""
p.write_text(s)
p = Path('/app/qutebrowser/misc/utilcmds.py')
s = p.read_text()
s = s.replace('Duration to wait in format XhYmZs or number for seconds.', 'Duration to wait in format XhYmZs or number for milliseconds.')
old = '    ms = utils.parse_duration(duration)\n    if ms < 0:\n'
new = '    try:\n        ms = utils.parse_duration(duration)\n    except ValueError:\n'
assert s.count(old) == 1
p.write_text(s.replace(old, new))
p = Path('/app/tests/unit/utils/test_utils.py')
s = p.read_text()
for line in ['    ("-1s", -1),  # No sense to wait for negative seconds\n', '    ("-1", -1),\n', '    ("34ss", -1),\n']:
    assert s.count(line) == 1
    s = s.replace(line, '')
s = s.replace('("60", 60000)', '("60", 60)')
s = s.replace('("60.4s", -1),  # Only accept integer values', '("60.4s", 60400),')
p.write_text(s)
print('Updated duration validation, milliseconds parsing and command error handling.')
