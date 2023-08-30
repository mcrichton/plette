
import hashlib

import pytest

from plette.models.sources import NewSource

def test_source_from_data():
    s = NewSource(
        **{
            "name": "devpi",
            "url": "https://$USER:$PASS@mydevpi.localhost",
            "verify_ssl": False,
          }
    )
    assert s.name == "devpi"
    assert s.url == "https://$USER:$PASS@mydevpi.localhost"
    assert s.verify_ssl is False


def test_source_as_data_expanded(monkeypatch):
    monkeypatch.setattr("os.environ", {"USER": "user", "PASS": "pa55"})
    s = NewSource(
        **{
            "name": "devpi",
            "url": "https://$USER:$PASS@mydevpi.localhost",
            "verify_ssl": False,
        }
    )
    assert s.url_expanded == "https://user:pa55@mydevpi.localhost"


def test_source_as_data_expanded_partial(monkeypatch):
    monkeypatch.setattr("os.environ", {"USER": "user"})
    s = NewSource(
        **{
            "name": "devpi",
            "url": "https://$USER:$PASS@mydevpi.localhost",
            "verify_ssl": False,
        }
    )
    assert s.url_expanded == "https://user:$PASS@mydevpi.localhost"
