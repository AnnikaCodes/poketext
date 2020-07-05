"""A text-based client for Pokémon Showdown"""

from datetime import datetime
import psclient # type: ignore
import prefs

class PSInterface():
    """Provides a text-based interface to PS!

    Args:
        connection (psclient.PSConnection): the connection
    """
    def __init__(self, connection: psclient.PSConnection) -> None:
        self.connection: psclient.PSConnection = connection
        self.roomContext: str = '' # is an ID

    def switchRoomContext(self, room: str) -> None:
        """Changes the room context

        Args:
            room (str): the name/ID of the room to change the context to
        """
        if not self.connection.getRoom(room):
            self.connection.roomList.add(psclient.Room(room, self.connection))
        self.roomContext = psclient.toID(room)

    def send(self, message: str) -> None:
        """Sends a message to the current room context

        Args:
            message (str): the message to send
        """
        self.connection.send(f"{self.roomContext}|{message}")

def onMessage(connection: psclient.PSConnection, message: psclient.Message) -> None:
    """Handles incoming messages

    Args:
        message (psclient.Message): the Message object that was recieved
    """
    if message.type in ['N']: return
    if message.type == 'chat' and message.senderName and message.body and message.room:
        time: str = f"[{str(datetime.utcfromtimestamp(int(message.time)).time())}] " if message.time else ""
        return print(f"({message.room.id}) {time}{message.senderName.strip()}: {message.body}")
    if message.type == 'pm' and message.senderName:
        if message.sender and message.sender.id != connection.this.id:
            return print(f"(PM from {message.senderName.strip()}) {message.body}")
        return
    if message.type in ['join', 'leave'] and message.room and message.senderName:
        if prefs.getPref("showjoins"):
            return print(f"{message.senderName.strip()} {'joined' if message.type == 'join' else 'left'} {message.room.id}")
        return
    return print(message.raw)

def onOpenThread(*args: psclient.PSConnection) -> None:
    """Gets run when the thread is opened
    """
    if not args: return
    conn: psclient.PSConnection = args[0]
    while True:
        if conn.isLoggedIn:
            conn.roomList.add(psclient.Room("help", conn))
            conn.roomList.add(psclient.Room("trivia", conn))
            return print("Logged in!")

if __name__ == '__main__':
    showdownConnection: psclient.PSConnection = psclient.PSConnection(
        prefs.getPref("username"),
        prefs.getPref("password"),
        onParsedMessage=onMessage,
        onOpenThread=onOpenThread
    )
    client: psclient.PSClient = psclient.PSClient(showdownConnection)
    interface: PSInterface = PSInterface(showdownConnection)
    client.connect()
