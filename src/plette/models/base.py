try:
    import cerberus
except ImportError:
    cerberus = None


class ValidationError(ValueError):
    def __init__(self, value, validator):
        super(ValidationError, self).__init__(value)
        self.validator = validator


VALIDATORS = {}


def validate(cls, data):
    if not cerberus:    # Skip validation if Cerberus is not available.
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


class DataView(object):
    """A "view" to a data.

    Validates the input mapping on creation. A subclass is expected to
    provide a `__SCHEMA__` class attribute specifying a validator schema,
    or a concrete Cerberus validator object.
    """
    def __init__(self, data):
        self.validate(data)
        self._data = data

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("cannot compare {0!r} with {1!r}".format(
                type(self).__name__, type(other).__name__,
            ))
        return self._data == other._data

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    @classmethod
    def validate(cls, data):
        return validate(cls, data)


class DataViewCollection(DataView):
    """A collection of dataview.

    Subclasses are expected to assign a class attribute `item_class` to specify
    how items should be coerced when accessed. The item class should conform to
    the `DataView` protocol.
    """
    item_class = None

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        return self.item_class(self._data[key])

    def __setitem__(self, key, value):
        if isinstance(value, self.item_class):
            value = value._data
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]


class DataViewMapping(DataViewCollection):
    """A mapping of dataview.

    The keys are primitive values, while values are instances of `item_class`.
    """
    @classmethod
    def validate(cls, data):
        for d in data.values():
            cls.item_class.validate(d)

    def __iter__(self):
        return iter(self._data)


class DataViewSequence(DataViewCollection):
    """A sequence of dataview.

    Each entry is an instance of `item_class`.
    """
    @classmethod
    def validate(cls, data):
        for d in data:
            cls.item_class.validate(d)

    def __iter__(self):
        return (self.item_class(d) for d in self._data)