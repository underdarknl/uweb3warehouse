def NotExistsErrorCatcher(f):
  """Decorator to return a 404 if a NotExistError exception was returned."""

  def wrapper(*args, **kwargs):
    try:
      return f(*args, **kwargs)
    except model.NotExistError as error:
      return args[0].RequestInvalidcommand(error=error)

  return wrapper
