# Package Scientific.TkWidgets

from Utility import FilenameEntry, FloatEntry, IntEntry, ButtonBar, StatusBar
from Utility import ModalDialog

import sys
if sys.modules.has_key('pythondoc'):
    FilenameEntry.__module__ = 'Scientific.TkWidgets'
    FloatEntry.__module__ = 'Scientific.TkWidgets'
    IntEntry.__module__ = 'Scientific.TkWidgets'
    ButtonBar.__module__ = 'Scientific.TkWidgets'
    StatusBar.__module__ = 'Scientific.TkWidgets'
    ModalDialog.__module__ = 'Scientific.TkWidgets'
del sys
