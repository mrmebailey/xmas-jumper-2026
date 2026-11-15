"""Best score for each game, saved so they survive a restart."""
import json
import os

from . import config

_scores = None


def _load():
    global _scores
    if _scores is None:
        try:
            _scores = json.loads(config.SCORES_FILE.read_text())
        except (OSError, ValueError):
            _scores = {}
    return _scores


def best(game):
    return _load().get(game)


def record(game, score, lower_is_better=False):
    """Save score if it beats the best; returns True for a new best."""
    scores = _load()
    old = scores.get(game)
    if old is not None and (score >= old if lower_is_better else score <= old):
        return False
    scores[game] = score
    try:
        config.SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = config.SCORES_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(scores))
        os.replace(tmp, config.SCORES_FILE)
    except OSError:
        pass
    return True
