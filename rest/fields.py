from builtins import str
from past.builtins import basestring
from builtins import object
from datetime import datetime
from decimal import Decimal
from locale import atof
from locale import atoi

from rest.validators import email
from rest.validators import url


class Field(object):
  """
  A field is a pointer to a value. It may coerce and validate values. The values
  of a field can either be a raw value (ie: str, int, list), or another `Field`.
  This distincation is made reflectivly by checking for `get` and `set` methods
  on the passed value.
  """
  def __init__(self, value=None, validators=[], default=None):
    self.serialize = True
    self._validators = validators
    self._value = value
    self._default = default

    self._has_get = hasattr(value, 'get')
    self._has_set = hasattr(value, 'set')
    self._has_reset = hasattr(value, 'reset')

  def validate(self):
    value = self.get()
    errors = []

    for validator in self._validators:
      error = validator(value)
      if error:
        errors += error
    return errors

  def default(self):
    value = self.get()
    if self._default is None:
      return

    if value is None:
      self.set(self._default)

  def get(self):
    if self._has_get:
      return self._value.get()
    else:
      return self._value

  def get_simplified(self):
    return self.simplify(self.get())

  def set(self, value):
    if value is None:
      return
    return self._set(value)

  def _set(self, value):
    try:
      coerced = self.coerce(value)
      if self._has_set:
        self._value.set(coerced)
      else:
        self._value = coerced
    except ValueError as v:
      return v.args
    except:
      return ['Invalid data']

  def coerce(self, value):
    return value

  def simplify(self, value):
    return value

  def reset(self):
    if self._has_reset:
      return self._value.reset()

    if self._has_set:
      self._value.set(None)
    else:
      self._value = None

class ReadOnly(Field):
  def __init__(self, *args, **kwargs):
    self.quiet = kwargs.pop('quiet', False)
    super(ReadOnly, self).__init__(*args, **kwargs)

  def set(self, value):
    current_value = self.get()
    if value != current_value and not self.quiet:
      raise ValueError('read-only field')

  def reset(self):
    pass

class WriteOnly(Field):
  def __init__(self, *args, **kwargs):
    super(WriteOnly, self).__init__(*args, **kwargs)
    self.quiet = kwargs.pop('quiet', False)
    self.serialize = False

  def get(self):
    if not self.quiet:
      raise Exception('write-only field')

class WriteOnce(Field):
  def __init__(self, *args, **kwargs):
    super(WriteOnce, self).__init__(*args, **kwargs)

    self.quiet = kwargs.pop('quiet', False)

  def set(self, value):
    current_value = self.get()
    if value and value != current_value and not self.quiet:
      raise ValueError('Cannot Change')


class String(Field):
  def __init__(self, *args, **kwargs):
    self.trim_to = kwargs.pop('trim_to', None)
    super(String, self).__init__(*args, **kwargs)

  def coerce(self, value):
    if self.trim_to:
      return str(value)[:self.trim_to]
    return str(value)


class NoneString(String):
  """
  This is a field that should have a value of None when passed an empty string
  """
  def coerce(self, value):
    if value:
      return super(NoneString, self).coerce(value)
    else:
      return None

  def set(self, value):
    return self._set(value)


class Bool(Field):
  def coerce(self, value):
    return True if value else False


class StringBool(Field):
  def coerce(self, value):
    str_value = str(value).lower()
    if str_value == 'true':
      return True
    if str_value == 'false':
      return False

    raise ValueError("Value must be 'true' or 'false'")


class Int(Field):
  def coerce(self, value):
    if value == '':
      value = '0'
    try:
      if isinstance(value, basestring):
        return atoi(value)
      else:
        return int(value)
    except:
      raise ValueError("Invalid integer")


class NoneInt(Field):
  def coerce(self, value):
    if value == '' or value is None:
      return None
    try:
      if isinstance(value, basestring):
        return atoi(value)
      else:
        return int(value)
    except:
      raise ValueError("Invalid integer")

  def set(self, value):
    return self._set(value)


class Float(Field):
  def coerce(self, value):
    if value == '':
      value = '0.0'
    try:
      if isinstance(value, basestring):
        return atof(value)
      else:
        return float(value)
    except:
      raise ValueError("Invalid float")

  def get(self):
    val = super(Float, self).get()
    if val is not None: return float(val)


class Dollars(Field):
  def coerce(self, value):
    if value == '':
      value = '0'
    try:
      return Decimal(str(value))
    except:
      raise ValueError("Invalid decimal")

  def simplify(self, value):
    return str(value.quantize(Decimal('0.01')))


class List(Field):
  def __init__(self, value=None, validators=[], default=None, options=[]):
    self.options = options
    super(List, self).__init__(value, validators, default)

  def coerce(self, value):
    items = list(value)
    if self.options:
      for item in items:
        if item not in self.options:
          raise ValueError('Invalid selection %s' % item)
    return items


class TruthyOnlyList(Field):
  def coerce(self, value):
    return [v for v in value if v]


class Dict(Field):
  def coerce(self, value):
    return dict(value)


class DateTime(Field):
  def coerce(self, value):

    if not value.endswith('Z'):
      raise ValueError("Date must be in UTC")

    time_str = value[:-1].split('.')[0]

    try:
      return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
    except:
      raise ValueError("Date must be in the following format: YYYY-MM-DDThh:mm:ssZ")

  def simplify(self, value):
    if value:
      return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class URL(Field):
  def __init__(self, value=None, validators=[], default=None):
    if url not in validators:
      validators.append(url)
    super(URL, self).__init__(value, validators, default)

  def coerce(self, value):
    if value:
      return URL.sanitize(str(value))
    else:
      return None

  @classmethod
  def sanitize(self, url):
    return url.replace('|', '%7C')\
              .replace(';', '%3B')


class Email(String):
  def __init__(self, value=None, validators=[], default=None):
    if email not in validators:
      validators.append(email)
    super(Email, self).__init__(value, validators, default)
