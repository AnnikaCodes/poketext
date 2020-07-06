"""An example plugin

Author: Annika <annika0uwu@gmail.com>"""

from prompt_toolkit import HTML, print_formatted_text as printf # type: ignore

def dadJoke(arguments: str) -> None:
    """A command function

    Args:
        arguments (str): the arguments
        (for example, if a command is "%eval self.connection.this.id == 'Annika'",
        arguments would be "self.connection.this.id == 'Annika'")
    """
    splits = ["I'm", "im", "i'm"]
    response = HTML(f"<ansired>You must include {', '.join(splits[:-1])}, or {splits[-1]} in your message.</ansired>")
    for split in splits:
        if split in arguments:
            thing = arguments.split(split, 1)[1]
            if not thing: continue
            if thing[0] != ' ': thing = ' ' + thing
            response = HTML(f"<ansigreen>Hi{thing}, I'm pokétext!</ansigreen>")
    printf(response)

commands = {"dadjoke": dadJoke, "alias": dadJoke} # A dictionary mapping commands/aliases to functions (or methods)
