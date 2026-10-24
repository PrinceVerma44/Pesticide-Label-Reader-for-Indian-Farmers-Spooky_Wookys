import pytest

from kisanlabel.jsonparse import parse_json


def test_plain():
    assert parse_json('{"a": 1}') == {"a": 1}


def test_fenced_with_chatter():
    assert parse_json('Sure!\n```json\n{"a": [1, 2]}\n```\nDone.') == {"a": [1, 2]}


def test_no_json():
    with pytest.raises(ValueError):
        parse_json("sorry, cannot read")
