"""A text-based client for Pokémon Showdown"""


import html
import threading
import re
import queue
import sys
from typing import Union, Dict

import psclient # type: ignore
from prompt_toolkit import HTML, print_formatted_text as printf # type: ignore

import prefs
from interface import PSInterface

# Initialize queues
messageQueue: queue.Queue = queue.Queue()
inputQueue: queue.Queue = queue.Queue()

# Helper functions
def formatHTML(rawHTML: str) -> HTML:
    """Formats HTML recieved from PS! to a prompt_toolkit HTML object

    Args:
        rawHTML (str): the raw HTML

    Returns:
        HTML: the formatted object
    """
    replacements: Dict[str, str] = {
        r"<psicon[^>]*\/>": '', # <psicon> makes no sense outside of the main client
        r"\|(raw|html|uhtml)\|": '\n',
        #r"<br[^>]*\/>": '\n', # the HTML printer doesnt understand <br />
        r"<(img|font)[^>]*>|</(font|img)>": "", # <img>, <font> dont work
        r"&(nbsp|ThickSpace);": " "
    }
    for regex, substitution in replacements.items():
        rawHTML = re.sub(regex, substitution, rawHTML)
    return HTML(rawHTML)

def logError(error: Union[str, Exception]) -> None:
    """Handles error logging

    Args:
        error (Union[str, Exception]): the error
    """
    if isinstance(error, Exception): error = f"Error: {str(error)}"
    return printf(HTML(f"<ansired>{html.escape(error)}</ansired>"))

def messageListener(connection: psclient.PSConnection, message: psclient.Message) -> None:
    """Listens for incoming messages and puts them in the queue

    Args:
        message (psclient.Message): the Message object that was recieved
    """
    # pylint: disable=unused-argument
    # we're locked into this by the ps-client package
    return messageQueue.put(message)

def inputListener() -> None:
    """Listens for keyboard input
    """
    while True:
        if not interface.isBusy:
            try:
                x = interface.prompt.prompt()
            except KeyboardInterrupt:
                printf(f"Use {interface.commandChar}exit to exit.")
                continue
            inputQueue.put(x)
            interface.isBusy = True

def mainLoop(*args: psclient.PSConnection) -> None:
    """Gets run when we connect to PS!
    """
    if not args: return
    conn: psclient.PSConnection = args[0]
    hasAutojoined: bool = False
    while True:
        if conn.isLoggedIn and not hasAutojoined:
            autojoins = prefs.getPref("autojoins")
            if autojoins:
                for room in autojoins:
                    conn.roomList.add(psclient.Room(room, conn))
            hasAutojoined = True
            printf("Logged in!")

        command: Union[str, None] = None
        try:
            interface.handleMessage(messageQueue.get(block=False))
        except queue.Empty:
            pass
        try:
            command = inputQueue.get(block=False)
        except queue.Empty:
            interface.isBusy = False
        if not command: continue
        if command[:len(interface.commandChar)] == interface.commandChar:
            split = command[len(interface.commandChar):].split(' ', 1)
            if split[0].lower() in interface.commands.keys():
                interface.commands[split[0].lower()](split[1] if len(split) > 1 else '') # invoke the command
                continue
            printf(f"Unknown command '{interface.commandChar}{split[0]}'")
            continue
        interface.send(command)
        interface.isBusy = False

if __name__ == '__main__':
    showdownConnection: psclient.PSConnection = psclient.PSConnection(
        prefs.getPref("username"),
        prefs.getPref("password"),
        onParsedMessage=messageListener,
        onOpenThread=mainLoop
    )
    client: psclient.PSClient = psclient.PSClient(showdownConnection)
    interface: PSInterface = PSInterface(showdownConnection)
    if len(sys.argv) > 1 and sys.argv[1] in ['--config', '--configure']:
        interface.configure("advanced" if len(sys.argv) > 2 and sys.argv[2] == '--advanced' else "")
        sys.exit()
    inputThread = threading.Thread(target=inputListener)
    inputThread.start()
    client.connect()
