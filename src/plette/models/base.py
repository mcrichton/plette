from dataclasses import dataclass
try:
    import cerberus
except ImportError:
    cerberus = None


class ValidationError(ValueError):
    pass

VALIDATORS = {}


def validate(cls, data):
    if not cerberus:  # Skip validation if Cerberus is not available.
        return
    schema = cls.__SCHEMA__
    key = id(schema)
    try:
        v = VALIDATORS[key]
    except KeyError:
        v = VALIDATORS[key] = cerberus.Validator(schema, allow_unknown=True)
    if v.validate(data, normalize=False):
        return
    raise ValidationError(data, v)


class NewModel:
    def __post_init__(self):
        """Run validation methods if declared.
        The validation method can be a simple check
        that raises ValueError or a transformation to
        the field value.
        The validation is performed by calling a function named:
            `validate_<field_name>(self, value, field) -> field.type`
        """
        for name, field in self.__dataclass_fields__.items():
            if (method := getattr(self, f"validate_{name}", None)):
                setattr(self, name, method(getattr(self, name), field=field))

@dataclass
class NewDataView(NewModel):
    
    _data: dict

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


class DataView(object):
    """A "view" to a data.

    Validates the input mapping on creation. A subclass is expected to
    provide a `__SCHEMA__` class attribute specifying a validator schema.
    """

    def __init__(self, data):
        self.validate(data)
        self._data = data

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

    @classmethod
    def validate(cls, data):
        return validate(cls, data)


class DataViewCollection(DataView):
    """A homogeneous collection of data views.

    Subclasses are expected to assign a class attribute `item_class` to specify
    the type of items it contains. This class will be used to coerce return
    values when accessed. The item class should conform to the `DataView`
    protocol.

    You should not instantiate an instance from this class, but from one of its
    subclasses instead.
    """

    item_class = None

    def __repr__(self):
        return "{0}({1!r})".format(type(self).__name__, self._data)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        return self.item_class(self._data[key])

    def __setitem__(self, key, value):
        if isinstance(value, DataView):
            value = value._data
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]


class DataViewMapping(DataViewCollection):
    """A mapping of data views.

    The keys are primitive values, while values are instances of `item_class`.
    """

    @classmethod
    def validate(cls, data):
        for d in data.values():
            cls.item_class.validate(d)

    def __iter__(self):
        return iter(self._data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return [self[k] for k in self._data]

    def items(self):
        return [(k, self[k]) for k in self._data]


class DataViewSequence(DataViewCollection):
    """A sequence of data views.

    Each entry is an instance of `item_class`.
    """

    @classmethod
    def validate(cls, data):
        for d in data:
            cls.item_class.validate(d)

    def __iter__(self):
        return (self.item_class(d) for d in self._data)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return type(self)(self._data[key])
        return super(DataViewSequence, self).__getitem__(key)

    def append(self, value):
        if isinstance(value, DataView):
            value = value._data
        self._data.append(value)
