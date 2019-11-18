
from builtins import str
from builtins import object
class Schema(object):
  @classmethod
  def combined_errors(self, *args):
    errors = []
    for schema in args:
      errors.extend(list(schema._errors.items()))
    return dict(errors)

  def __init__(self, **kwargs):
    self._fields = self._get_fields()
    self._errors = {}

    for name, field in list(self._fields.items()):
      if name in kwargs:
        field.set(kwargs.pop(name))
      else:
        field.reset()

  def get_namespace(self):
    if hasattr(self, '__namespace__'):
      return self.__namespace__
    return self.__class__.__name__.replace('Schema', '')

  def __call__(self, data=None):
    if data is None:
      data = {}
    errors = {}

    def add_errors(name, errs):
      if errs:
        field_errors = errors.get(name, [])
        field_errors += errs
        errors[name] = field_errors

    # First, set the values on the field. If anything goes wrong, it'll return
    # a list of errors
    for name, value in list(data.items()):
      if name not in self._fields:
        continue
      try:
        errs = self._fields[name].set(value)
      except ValueError as err:
        errs = [err.message]
      add_errors(name, errs)

    # Check to see if we need to default to defalut values
    for name, field in list(self._fields.items()):
      if not field.serialize:
        continue
      field.default()

    # Then, now the everything's been set, run all the field validators.
    for name, field in list(self._fields.items()):
      if not field.serialize:
        continue
      errs = field.validate()
      add_errors(name, errs)

      validator = 'validate_%s' % name
      if hasattr(self, validator):
        try:
          getattr(self, validator)(field.get())
        except ValueError as v:
          add_errors(name, v.args)

    self._errors = errors
    return not bool(errors)

  def __repr__(self):
    return str(self._get())

  def _get(self):
    rep = {}
    for name, field in list(self._fields.items()):
      if field.serialize:
        name = getattr(field, 'name', name)
        rep[name] = field.get_simplified()
    rep['__namespace__'] = self.get_namespace()
    return rep

  def dict(self):
    return self._get()

  def _get_fields(self):
    fields = {}
    for field_name in dir(self):
      if not field_name.startswith('_'):
        field = getattr(self, field_name)
        if not hasattr(field, '__call__'):
          fields[field_name] = field
    return fields
