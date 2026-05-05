
"""Minimal hello-world CLI example.

Usage:
- Call `Greeter().say_hello(name)` to greet one name and return the message.
- Call `Greeter().greet(names)` to greet a list of non-empty names in order.
- Call `run()` to parse command-line arguments and execute the CLI flow.
"""
import sys

DEFAULT_NAME = "World"

class Greeter:
    def say_hello(self, name: str) -> str:
        if not name:
            raise ValueError("Name must not be empty")
        message = f"Hello, {name}!"
        print(message)
        return message

    def greet(self, names: list[str]) -> list[str]:
        return [self.say_hello(n) for n in names if n.strip()]


def parse(argv: list[str]) -> list[str]:
    names = [a.strip() for a in argv if a.strip()]
    return names if names else [DEFAULT_NAME]


def run() -> None:
    Greeter().greet(parse(sys.argv[1:]))


if __name__ == "__main__":
    run()
