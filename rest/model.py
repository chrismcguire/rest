from builtins import object
from copy import copy


class Model(object):
  """
  A proxy to a model object which can have arbitrary fields get and set.
  """
  def __init__(self, cls):
    self.serialize = False
    self._class  = cls
    self._fields = {}
    self._model  = None
    self._inital = None

  def set(self, model):
    self._initial = copy(model)
    self._model = model

  def get(self):
    return self._model

  def get_initial(self):
    return self._initial

  def __getattr__(self, name):
    if name.startswith('_'):
      raise AttributeError()

    if name in self._fields:
      field = self._fields[name]
    else:
      field = self._get_field(name)
      self._fields[name] = field

    return field

  def _get_field(self, name):
    return ModelValue(self, name)

class ModelValue(object):
  def __init__(self, model, field_name):
    self._model = model
    self._field_name = field_name
    self._initial = None

  def get(self):
    return getattr(self._model.get(), self._field_name)

  def set(self, value):
    return setattr(self._model.get(), self._field_name, value)

  def reset(self):
    pass
