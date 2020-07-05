"""Loads and saves preferences"""

import pathlib
import json
from typing import Any, Dict

PREFS_PATH: pathlib.Path = pathlib.Path('prefs.json').resolve()

def getPref(preference: str) -> Any:
    """Gets a preference from prefs.json

    Args:
        preference (str): the preference to get

    Returns:
        Any: the preference; None on failure
    """
    prefsData: Dict[str, Any] = _loadJSON()
    if preference in prefsData.keys(): return prefsData[preference]
    return None

def setPref(preference: str, value: Any) -> None:
    """Sets a preference to a value in prefs.json

    Args:
        preference (str): the preference's name
        value (any): the value to store
    """
    prefsData: Dict[str, Any] = _loadJSON()
    prefsData[preference] = value
    PREFS_PATH.write_text(json.dumps(prefsData))

def _loadJSON() -> Dict[str, Any]:
    """Gets the preference data from PREFS_PATH

    Returns:
        dict: the preference data
    """
    if not PREFS_PATH.exists():
        PREFS_PATH.touch()
        return {}
    if not PREFS_PATH.is_file():
        print(f"poketext: error: {str(PREFS_PATH)} is not a file")
        return {}
    return json.loads(PREFS_PATH.read_text())
