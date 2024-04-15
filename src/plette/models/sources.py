import os

from .base import DataView


class DataValidationError(ValueError):
    pass


class Source:
    """Information on a "simple" Python package index.

    This could be PyPI, or a self-hosted index server, etc. The server
    specified by the `url` attribute is expected to provide the "simple"
    package API.
    """
    __SCHEMA__ = {
        "name": str,
        "url": str,
        "verify_ssl": bool,
    }

    def __init__(self, _data: dict):

        self.validate(_data)
        self._data = _data

    @classmethod
    def validate(self, data):
        for k, v in self.__SCHEMA__.items():
            if k not in data:
                raise DataValidationError(f"Missing required field: {k}")
            if not isinstance(data[k], v):
                raise DataValidationError(f"Invalid type for field {k}: {type(data[k])}")

    def __repr__(self):
        return "{0}({1!r})".format(type(self).__name__, self._data)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                "cannot compare {0!r} with {1!r}".format(
                    type(self).__name__, type(other).__name__
                )
            )
        return self._data == other._data

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    @property
    def name(self):
        return self._data["name"]

    @name.setter
    def name(self, value):
        self._data["name"] = value

    @property
    def url(self):
        return self._data["url"]

    @url.setter
    def url(self, value):
        self._data["url"] = value

    @property
    def verify_ssl(self):
        return self._data["verify_ssl"]

    @verify_ssl.setter
    def verify_ssl(self, value):
        self._data["verify_ssl"] = value

    @property
    def url_expanded(self):
        return os.path.expandvars(self._data["url"])
