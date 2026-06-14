
"""Entry point for the JS runtime.

Usage:
    python -m js_runtime.main <file.js>
    python -m js_runtime.main -e 'console.log("hi")'
    cat script.js | python -m js_runtime.main
"""
import sys
from .lexer import Tokenizer
from .parser import Parser
from .runtime import Interpreter
from .errors import JSSyntaxError, JSReferenceError, JSTypeError


def run(source: str) -> int:
    try:
        tokens = Tokenizer(source).tokenize()
        ast = Parser(tokens).parse()
        Interpreter().run(ast)
        return 0
    except JSSyntaxError as e:
        sys.stderr.write(f"SyntaxError: {e.message} at line {e.line}, col {e.column}\n"); return 1
    except JSReferenceError as e:
        sys.stderr.write(f"ReferenceError: {e.message}\n"); return 1
    except JSTypeError as e:
        sys.stderr.write(f"TypeError: {e.message}\n"); return 1
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n"); return 1


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        src = sys.stdin.read()
        return run(src)
    if argv[0] in ("-e", "--eval"):
        return run(argv[1])
    if argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    with open(argv[0], "r", encoding="utf-8") as f:
        return run(f.read())


if __name__ == "__main__":
    sys.exit(main())
