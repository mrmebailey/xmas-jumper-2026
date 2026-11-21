"""What Santa says for a Naughty or Nice verdict. Kept apart from the screen
(and pygame) so tools/make_santa_voice.py can record every line of it."""

# verdict -> (how often it comes up, things to say)
VERDICT_LINES = {
    "NICE!": (45, [
        "Santa's sleigh will definitely be stopping at yours.",
        "The elves give you a big thumbs up!",
        "Mince pies all round!",
        "Keep it up and there might be an extra present.",
    ]),
    "VERY NICE!": (25, [
        "Top of Santa's list this year!",
        "Rudolph wants your autograph!",
        "The elves are building something special for you.",
    ]),
    "NAUGHTY!": (30, [
        "Uh oh... it's looking like a lump of coal.",
        "The elves saw what you did...",
        "Better be extra good from now until Christmas!",
        "Santa is going to have a word with you.",
    ]),
}

# How naughty each verdict can be, as a percentage on the Naughty-o-meter.
NAUGHTINESS = {"VERY NICE!": (1, 19), "NICE!": (20, 59), "NAUGHTY!": (60, 100)}

TOP_OF_LIST = "You are top of the naughty list!"


# How Santa announces each verdict. A whole sentence, because the voice
# drags a single word like "Nice!" out to several seconds.
_SPOKEN_VERDICTS = {
    "NICE!": "You're on the nice list!",
    "VERY NICE!": "Very nice indeed! You're on the nice list!",
    "NAUGHTY!": "Oh dear. You're on the naughty list!",
}


def spoken_verdict(word):
    return _SPOKEN_VERDICTS.get(word, word.capitalize())


def spoken_naughtiness(percent):
    return f"{percent} percent naughty."


def all_naughtiness_lines():
    low = min(lo for lo, _ in NAUGHTINESS.values())
    high = max(hi for _, hi in NAUGHTINESS.values())
    return [spoken_naughtiness(n) for n in range(low, high + 1)]
