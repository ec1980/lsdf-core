
import sys

class Greeter:
    def say_hello(self, name: str) -> str:
        if not name: raise ValueError("Name empty")
        print(f"Hello {name}")
        return f"Msg: {name}"

def run_loop():
    args = sys.argv[1:]
    Greeter().say_hello(args[0] if args else "World")

if __name__ == "__main__":
    run_loop()
