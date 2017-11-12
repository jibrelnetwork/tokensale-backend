#
# Load local changes
#

from . import config

try:
    # noinspection PyUnresolvedReferences
    from . import config_changes as _config_changes

    for varName, varValue in _config_changes.__dict__.items():
        config.__dict__[varName] = varValue
        del varName, varValue
except ImportError:
    pass
