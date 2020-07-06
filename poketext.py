"""A text-based client for Pokémon Showdown"""

from datetime import datetime
from typing import Union, Dict, Any

import html
import threading
import re
import queue

import psclient # type: ignore
from prompt_toolkit import HTML, PromptSession, print_formatted_text as printf

import prefs

messageQueue: queue.Queue = queue.Queue()
inputQueue: queue.Queue = queue.Queue()

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

class PSInterface():
    """Provides a text-based interface to PS!

    Args:
        connection (psclient.PSConnection): the connection
    """
    def __init__(self, connection: psclient.PSConnection) -> None:
        self.connection: psclient.PSConnection = connection
        self.roomContext: str = '' # is an ID
        self.promptString: str = prefs.getPref("prompt") or "{room}> "
        self.prompt: PromptSession = PromptSession(self.getPrompt())
        self.commandChar: str = prefs.getPref("commandchar")
        self.commands: Dict[str, Any] = {"room": self.switchRoomContext, "eval": self.eval}
        self.isBusy: bool = False

    def send(self, message: str) -> None:
        """Sends a message to the current room context

        Args:
            message (str): the message to send
        """
        self.connection.send(f"{self.roomContext}|{message}")

    def handleMessage(self, message: psclient.Message) -> None:
        """Handles incoming messages from the server

        Args:
            message (psclient.Message): the Message object to handle
        """
        if message.type in prefs.getPref('blacklistedTypes'): return
        formatted: Union[str, HTML] = message.raw
        if message.type == 'chat' and message.senderName and message.body and message.room:
            time: str = f"[{str(datetime.utcfromtimestamp(int(message.time)).time())}] " if message.time else ""
            formatted = f"({message.room.id}) {time}{message.senderName.strip()}: {message.body}"
        if message.type == 'pm' and message.senderName:
            if message.sender and message.sender.id != message.connection.this.id:
                formatted = f"(PM from {message.senderName.strip()}) {message.body}"
        if message.type in ['join', 'leave'] and message.room and message.senderName:
            if prefs.getPref("showjoins"):
                formatted = f"{message.senderName.strip()} {'joined' if message.type == 'join' else 'left'} {message.room.id}"
        if message.type in ['raw', 'html', 'uhtml'] and message.raw:
            index = 3 if message.type == 'uhtml' else 2
            split = message.raw.split('|', index)
            formatted = formatHTML(f"{(split[index - 1] + ': ') if message.type == 'uhtml' else ''}{split[index]}")
        printf(formatted)

    def switchRoomContext(self, room: str) -> None:
        """Changes the room context

        Args:
            room (str): the name/ID of the room to change the context to
        """
        if not self.connection.getRoom(room):
            self.connection.roomList.add(psclient.Room(room, self.connection))
        self.roomContext = psclient.toID(room)
        self.prompt.message = self.getPrompt()

    def eval(self, code: str) -> None:
        """Evaluates code and prints the result

        Args:
            code (str): the code
        """
        try:
            printf(eval(code)) # pylint: disable=eval-used
        except Exception as err:
            printf(HTML(f"<ansired>Error: {html.escape(str(err))}</ansired>"))

    def getPrompt(self) -> str:
        """Gets the prompt for sending messages

        Returns:
            str: the prompt
        """
        return self.promptString.format(
            room=self.roomContext
        )


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
            x = interface.prompt.prompt()
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
            autojoins = prefs.getPref("autojoin")
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
            if split[0] in interface.commands.keys():
                interface.commands[split[0]](split[1] if len(split) > 1 else '')
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
    inputThread = threading.Thread(target=inputListener)
    inputThread.start()
    client.connect()
