import re

_JOKE_LINE = re.compile(r"^\d+\.\s*(.+)$")


def parse_jokes(path):
    jokes = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            match = _JOKE_LINE.match(line.strip())
            if match:
                jokes.append(match.group(1))
    return jokes
