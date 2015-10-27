import re

from .response import Works
from .noworks import NoWorks

# helpers ----------
def converter(x):
  if(x.__class__.__name__ == 'str'):
      return [x]
  else:
      return x

def sub_str(x, n = 3):
  if(x.__class__.__name__ == 'NoneType'):
    pass
  else:
    return str(x[:n]) + '***'

def switch_classes(x, path, works):
  if works or re.sub("/", "", path) == "works" and re.sub("/", "", path) != "licenses":
  	return Works(result = x)
  else:
  	return NoWorks(result = x)