
import sys

# Default greeting target when no argument is provided.
DEFAULT_NAME = "World"

class Greeter:
    """Sends personalised greetings to one or more named targets."""

    def say_hello(self, name: str) -> str:
        """Greet a single person and return the formatted message.

        Raises:
            ValueError: If name is an empty string.
        """
        if not name:
            raise ValueError("Name must not be empty")
        message = f"Hello, {name}!"
        print(message)
        return message

    def greet(self, names: list[str]) -> list[str]:
        """Greet every non-empty name in the list in order.

        Empty strings are silently skipped.
        Returns a list of the formatted greeting messages.
        """
        return [self.say_hello(n) for n in names if n.strip()]


def parse(argv: list[str]) -> list[str]:
    """Return the list of names from argv, defaulting to [DEFAULT_NAME].

    Strips whitespace from each argument and drops any blank strings.
    """
    names = [a.strip() for a in argv if a.strip()]
    return names if names else [DEFAULT_NAME]


def run() -> None:
    """Entry point: parse CLI args and greet each name in order."""
    Greeter().greet(parse(sys.argv[1:]))


if __name__ == "__main__":
    run()
