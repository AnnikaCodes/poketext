"""Tests the prefs module"""

import sys
import pathlib
sys.path.append('./')
import prefs # pylint: disable=wrong-import-position

def testPrefs() -> None:
    """Tests preferences
    """
    prefs.PREFS_PATH = pathlib.Path('prefs.json').resolve()
    prefs.setPref("test", 1)
    assert prefs.getPref("test") == 1
    prefs.setPref("test2", ["hIIII", '3 21', 2])
    assert prefs.getPref("test") == 1
    assert prefs.getPref("test2") == ["hIIII", '3 21', 2]
