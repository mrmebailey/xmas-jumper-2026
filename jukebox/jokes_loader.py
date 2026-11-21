import hashlib
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


def split_joke(joke):
    """("Why did...?", "Because...") at the first question mark; the whole
    joke and no punch line if there isn't one."""
    question, mark, answer = joke.partition("?")
    if not mark or not answer.strip():
        return joke, ""
    return question + "?", answer.strip()


def recorded_speech(directory, text, kind):
    """Where a pre-recorded line is kept (whether or not it exists): named
    from the words themselves, so editing a joke just means recording it again.
    kind is "q" (question), "p" (punch line) or "laugh"."""
    digest = hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:12]
    return directory / f"{kind}-{digest}.ogg"
