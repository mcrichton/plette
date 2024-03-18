# pylint: disable=missing-module-docstring,missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=no-member

import dataclasses
import json
import numbers

import collections.abc as collections_abc

from dataclasses import dataclass, field, asdict
from typing import Optional

from .models import BaseModel, Meta, PackageCollection, Package, remove_empty_values

PIPFILE_SPEC_CURRENT = 6


def flatten_versions(d):
    copy = {}
    # Iterate over a copy of the dictionary
    for key, value in d.items():
        # If the key is "version", replace the key with the value
        copy[key] = value["version"]
    return copy


def packages_to_dict(packages):
    packages_as_dict = {}
    for name, package in packages.items():
        values = {k: v for k, v in package.items() if v}
        values.pop("name")
        packages_as_dict[name] = values

    return packages_as_dict


class DCJSONEncoder(json.JSONEncoder):

    def default(self, o):
        if dataclasses.is_dataclass(o):
            o = dataclasses.asdict(o)
            if "_meta" in o:
                o["_meta"]["pipfile-spec"] = o["_meta"].pop("pipfile_spec")
                o["_meta"]["hash"] = {o["_meta"]["hash"]["name"]: o["_meta"]["hash"]["value"]}
                o["_meta"]["sources"] = o["_meta"]["sources"].pop("sources")

            remove_empty_values(o)

            if "default" in o:
                o["default"] = packages_to_dict(o["default"]["packages"])
            if "develop" in o:
                o["develop"] = packages_to_dict(o["develop"]["packages"])
            # add silly default values
            if "develop" not in o:
                o["develop"] = {}
            if "requires" not in o["_meta"]:
                o["_meta"]["requires"] = {}
            return o
        return super().default(o)


def _copy_jsonsafe(value):
    """Deep-copy a value into JSON-safe types.
    """
    if isinstance(value, (str, numbers.Number)):
        return value
    if isinstance(value, collections_abc.Mapping):
        return {str(k): _copy_jsonsafe(v) for k, v in value.items()}
    if isinstance(value, collections_abc.Iterable):
        return [_copy_jsonsafe(v) for v in value]
    if value is None:   # This doesn't happen often for us.
        return None
    return str(value)


@dataclass
class Lockfile(BaseModel):
    """Representation of a Pipfile.lock."""

    _meta: Optional[Meta]
    default: Optional = field(init=True,)
    develop: Optional = field(init=True,)

    def __post_init__(self):
        """Run validation methods if declared.
        The validation method can be a simple check
        that raises ValueError or a transformation to
        the field value.
        The validation is performed by calling a function named:
            `validate_<field_name>(self, value) -> field.type`
        """
        super().__post_init__()
        self.meta = self._meta

    def validate__meta(self, value):
        return self.validate_meta(value)

    def validate_meta(self, value):
        if "_meta" in value:
            value = value["_meta"]
        if 'pipfile-spec' in value:
            value['pipfile_spec'] = value.pop('pipfile-spec')
        return Meta(**value)

    def validate_default(self, value):
        if value is None:
            return PackageCollection(packages={})
        packages = {}
        for name, spec in value.items():
            if isinstance(spec, str):
                spec = {"version": spec}
            packages[name]=Package(name=name, **spec)
        return PackageCollection(packages=packages)

    def validate_develop(self, value):
        if value is None:
            return PackageCollection(packages={})
        packages = {}
        for name, spec in value.items():
            if isinstance(spec, str):
                spec = {"version": spec}
            packages[name]=Package(name=name, **spec)
        return PackageCollection(packages=packages)

    @classmethod
    def load(cls, fh, encoding=None):
        if encoding is None:
            data = json.load(fh)
        else:
            data = json.loads(fh.read().decode(encoding))
        return cls(**data)

    @classmethod
    def with_meta_from(cls, pipfile, categories=None):
        data = {
            "_meta": {
                "hash": pipfile.get_hash().__dict__,
                "pipfile-spec": PIPFILE_SPEC_CURRENT,
                "requires": _copy_jsonsafe(getattr(pipfile, "requires", {})),
            },
        }

        data["_meta"].update(asdict(pipfile.sources))

        if categories is None:
            data["default"] = _copy_jsonsafe(getattr(pipfile, "packages", {}))
            data["develop"] = _copy_jsonsafe(getattr(pipfile, "dev-packages", {}))
        else:
            for category in categories:
                if category in ["default", "packages"]:
                    data["default"] = _copy_jsonsafe(getattr(pipfile,"packages", {}))
                elif category in ["develop", "dev-packages"]:
                    data["develop"] = _copy_jsonsafe(
                            getattr(pipfile,"dev-packages", {}))
                else:
                    data[category] = _copy_jsonsafe(getattr(pipfile, category, {}))
        if "default" not in data:
            data["default"] = {}
        if "develop" not in data:
            data["develop"] = {}
        return cls(**data)

    def __getitem__(self, key):
        value = self.__dict__[key]
        if key == "_meta":
            return Meta(**value)
        return value

    def is_up_to_date(self, pipfile):
        return self.meta.hash == pipfile.get_hash()

    def dump(self, fh):
        self.meta = self._meta
        return json.dump(self, fh, cls=DCJSONEncoder, indent=4)

    @property
    def meta(self):
        return self._meta

    @meta.setter
    def meta(self, value):
        self._meta = value


    @property
    def dev_packages(self):
        return self.develop
