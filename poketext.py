"""A text-based client for Pokémon Showdown"""

from datetime import datetime
from typing import Union, Dict, Any

import html
import importlib
import threading
import os
import re
import queue
import sys
import pathlib

import psclient # type: ignore
from prompt_toolkit import HTML, PromptSession, print_formatted_text as printf # type: ignore
from prompt_toolkit.shortcuts import input_dialog as inputDialog, yes_no_dialog as yesNoDialog # type: ignore

import prefs

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
        self.commands: Dict[str, Any] = {
            "room": self.switchRoomContext, "eval": self.eval, "loadplugin": self.loadPlugin, "load": self.loadPlugin,
            "unload": self.unloadPlugin, "unloadplugin": self.unloadPlugin, "exit": self.exit, "bye": self.exit,
            "configure": self.configure
        }
        self.loadedPlugins: set = set()

        plugins: list = prefs.getPref("plugins")
        if plugins and isinstance(plugins, list):
            for plugin in plugins:
                self.loadPlugin(plugin)
        self.isBusy: bool = False

    def send(self, message: str) -> None:
        """Sends a message to the current room context

        Args:
            message (str): the message to send
        """
        self.connection.send(f"{self.roomContext}|{message}")

    def getPrompt(self) -> str:
        """Gets the prompt for sending messages

        Returns:
            str: the prompt
        """
        return self.promptString.format(
            room=self.roomContext
        )

    def handleMessage(self, message: psclient.Message):
        """Handles incoming messages from the server

        Args:
            message (psclient.Message): the Message object to handle
        """
        if message.type in prefs.getPref('blacklistedTypes'): return
        formatted: Union[str, HTML] = message.raw
        if message.type == 'chat' and message.senderName and message.body and message.room:
            time: str = f"[{str(datetime.utcfromtimestamp(int(message.time)).time())}] " if message.time else ""
            toPrint = [f"({message.room.id}) {time}{message.senderName.strip()}: {message.body}"]
            if '|raw|' in message.body:
                split = message.body.split('|raw|')
                toPrint[0] = toPrint[0].replace(message.body, split[0])
                for item in split[1:]:
                    toPrint.append(formatHTML(item))
            return [printf(item) for item in toPrint]
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
            logError(err)

    def exit(self, lolWeGetPassedAMessageFixThisUselessVariable: str) -> None:
        """Exits the client
        """
        # pylint: disable=unused-argument, protected-access
        # TODO: make that unnecessary ^^
        os._exit(0)

    def loadPlugin(self, plugin: str) -> None:
        """Loads a plugin

        Args:
            plugin (str): the name of the plugin to load
        """
        plugin = plugin.lower().replace(' ', '')
        if not plugin: return logError("You must specify a plugin.")
        if plugin in self.loadedPlugins: return logError("That plugin is already loaded.")
        pluginsPath: str = str(pathlib.Path('plugins').resolve())
        if pluginsPath not in sys.path: sys.path.append(pluginsPath)

        try:
            self.commands.update(importlib.import_module(plugin).commands) # type: ignore
            self.loadedPlugins.add(plugin)
        except ModuleNotFoundError:
            return logError(f"No plugin named {plugin} was found.")
        except AttributeError:
            return logError("The plugin file is invalid." + \
                f"Check that you have the latest version and that the file 'plugins/{plugin}.py' is correctly formatted")
        except Exception as err:
            return logError(err)

        pluginSettings: list = prefs.getPref("plugins")
        if not pluginSettings: pluginSettings = []
        if plugin not in pluginSettings:
            pluginSettings.append(plugin)
            prefs.setPref("plugins", pluginSettings)
        return printf(f"Plugin {plugin} loaded!")

    def unloadPlugin(self, plugin: str) -> None:
        """Unloads a plugin

        Args:
            plugin (str): the name of the plugin to unload
        """
        plugin = plugin.lower().replace(' ', '')
        if not plugin: return logError("You must specify a plugin.")
        if plugin not in self.loadedPlugins: return logError("That plugin isn't loaded!")

        try:
            commands = importlib.import_module(plugin).commands # type: ignore
            for command in commands:
                if command in self.commands: del self.commands[command]
            self.loadedPlugins.remove(plugin)
        except ModuleNotFoundError:
            return logError(f"No plugin named {plugin} was found.")
        except Exception as err:
            return logError(err)

        pluginSettings: list = prefs.getPref("plugins")
        if pluginSettings and plugin in pluginSettings:
            pluginSettings.remove(plugin)
            prefs.setPref("plugins", pluginSettings)
        return printf(f"Plugin {plugin} unloaded!")

    def configure(self, isAdvanced: str) -> None:
        """Configures preferences

        Args:
            isAdvanced (str): 'advanced' means we show advanced settings
        """
        # pylint: disable=unused-argument
        preferences: dict = {
            "username": "Your Pokémon Showdown username",
            "password": "Your Pokémon Showdown password",
            "autojoins": "The rooms you want to automatically join upon logging in"
        }
        advancedPreferences: dict = {
            "commandchar": "The character to use before commands ('%' is recommended)",
            "prompt": "The prompt to use. If you don't know what you're doing, it's best to set this to '{room}> '"
        }

        loopDict = preferences if isAdvanced != 'advanced' else dict(preferences, **advancedPreferences)
        for pref in loopDict:
            isPassword: bool = pref == "password"
            currentValue: str = "******" if prefs.getPref(pref) and isPassword else str(prefs.getPref(pref))
            value: Any = inputDialog(
                title=f"Configure {pref}",
                text=f"{loopDict[pref]} (currently: {currentValue})",
                password=isPassword
            ).run()
            if not value: continue
            if pref == "autojoins": value = [psclient.toID(room) for room in value.split(',')]
            prefs.setPref(pref, value)

        prefs.setPref("showjoins", yesNoDialog(title="Configure showjoins", text="Display join/leave messages?").run())

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
