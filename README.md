# js_runtime — a JavaScript runtime written in pure Python

A production-quality, dependency-free JavaScript interpreter implemented from
scratch in Python 3.12+. No Node, V8, QuickJS, Duktape, js2py, etc. — the
lexer, parser, and tree-walking interpreter are all hand-written.

## Quick start

```bash
# Run a file
python -m js_runtime.main path/to/script.js

# Run an inline snippet
python -m js_runtime.main -e 'console.log("hello, " + (1 + 2))'

# Pipe via stdin
echo 'console.log([1,2,3].map(x=>x*x).reduce((a,b)=>a+b,0))' | python -m js_runtime.main

# Run the test suite
python -m unittest js_runtime.tests.test_runtime -v
```

> Run commands from the directory **containing** the `js_runtime/` folder so
> Python can import the package.
>

## Architecture

```
js_runtime/
├── lexer/           Tokenizer + token definitions
├── parser/          Recursive-descent parser with Pratt-style precedence
├── ast/             AST node dataclasses + visitor base
├── runtime/         Value system, environments/scope, tree-walking interpreter
├── builtins/        console, Math, Date, Array methods, String methods
├── errors/          JSSyntaxError, JSTypeError, JSReferenceError
├── tests/           unittest-based regression suite
├── main.py          CLI entry point
└── README.md
```

### Pipeline

1. **Lexer** (`lexer/tokenizer.py`) — character stream → tokens with
   line/column info. Handles keywords, identifiers, numeric & string &
   template literals, single/double/triple-character operators, line & block
   comments.
2. **Parser** (`parser/parser.py`) — tokens → AST. Recursive-descent with
   precedence-climbing for binary operators (see `parser/precedence.py`).
   Supports all of: variable declarations (`let`/`const`/`var`), blocks,
   `if`/`else`, `switch`/`case`/`default`, `for`/`for-of`/`for-in`,
   `while`/`do-while`, `return`/`break`/`continue`, `try`/`catch`/`finally`/
   `throw`, function declarations & expressions, arrow functions, member
   access (`.` and `[]`), call expressions, `new`, spread (`...`) in arrays
   & call args, rest parameters, array & object literals (incl. shorthand),
   conditional (ternary), assignment ops (`=`, `+=`, `-=`, `*=`, `/=`, `%=`),
   unary (`-`, `+`, `!`, `~`, `typeof`), update (`++`, `--`).
3. **Interpreter** (`runtime/interpreter.py`) — tree walks the AST. Uses
   Python exceptions internally for `return`/`break`/`continue`/`throw`
   unwinding. Lexical scope via the `Environment` chain (`runtime/environment.py`)
   with const enforcement and closure capture.

### Value system (`runtime/values.py`)

| JS type    | Python representation             |
| ---------- | --------------------------------- |
| Number     | `int` or `float` (incl. NaN, ±∞)  |
| String     | `str`                             |
| Boolean    | `bool`                            |
| Null       | `None`                            |
| Undefined  | singleton `UNDEFINED`             |
| Object     | `dict` (insertion-ordered)        |
| Array      | `list`                            |
| Function   | `JSFunction` or Python `callable` |

Implements JS-style coercion: `1 + "2" === "12"`, `"5" * 2 === 10`,
`true + 1 === 2`, `null == undefined` (true), `null === undefined` (false),
`NaN !== NaN`, etc.

## Supported language features

- Statements: var/let/const, blocks, if/else, switch, for/for-of/for-in,
  while, do-while, return, break, continue, try/catch/finally, throw.
- Expressions: literals, identifiers, arrays, objects (incl. shorthand &
  computed keys & spread), member access, calls, new, arrow & function
  expressions, unary, binary (arith/compare/equality/logical/bitwise/`in`),
  ternary, assignment ops, update (`++`/`--`), spread/rest.
- Closures, recursion, callbacks, higher-order functions.
- Operator precedence matches JavaScript.

## Built-ins

- `console.log`, `console.error`, `console.warn`, `console.info`, `console.debug`
- `Math.floor / ceil / round / abs / max / min / pow / sqrt / random / trunc / sign / log / exp / sin / cos / tan`, `Math.PI`, `Math.E`
- `Date` — `new Date()`, `new Date(ms)`, `new Date(y,m,d,...)`; instance
  methods `getFullYear / getMonth / getDate / getHours / getMinutes /
  getSeconds / getTime / toISOString / toString`
- Arrays — `push / pop / shift / unshift / slice / splice / concat /
  includes / indexOf / sort / reverse / join / map / filter / reduce /
  find / findIndex / some / every / forEach / flat`, plus `length` and
  numeric indexing.
- Strings — `replace / replaceAll / substring / slice / split / trim /
  trimStart / trimEnd / toUpperCase / toLowerCase / includes / startsWith /
  endsWith / indexOf / lastIndexOf / charAt / charCodeAt / repeat /
  concat / padStart / padEnd`, plus `length` and numeric indexing.
- Globals: `parseInt`, `parseFloat`, `isNaN`, `isFinite`, `String`,
  `Number`, `Boolean`, `Array`, `Object`, `JSON.stringify`, `JSON.parse`,
  `Error`, `TypeError`, `RangeError`, `SyntaxError`, `ReferenceError`,
  `NaN`, `Infinity`, `undefined`.

## Errors

- `JSSyntaxError` raised by lexer/parser, with line & column.
- `JSReferenceError` raised when reading an undeclared identifier.
- `JSTypeError` raised on bad type operations (e.g. calling a non-function,
  reading properties of null/undefined, writing to a `const`).

`try { ... } catch (e) { ... }` catches both JS-thrown values (via `throw`)
and native runtime errors (exposed as `{ name, message }` Error objects).

## Hackathon test cases

The 5 provided test programs are checked in under `js_runtime/tests/test1.js`
through `test5.js` and are also covered by `tests/test_runtime.py`.

```
python -m js_runtime.main js_runtime/tests/test1.js
python -m js_runtime.main js_runtime/tests/test2.js
...
```

All 5 produce the expected output exactly. The unit-test module additionally
covers closures, coercion, equality, array methods, rest/spread, try/catch,
and switch behaviour.

## Design notes

- **Why a tree-walking interpreter?** Simpler, easier to debug, and fast
  enough for hackathon-scale programs. A bytecode VM would be the next
  step for performance.
- **Why Python lists/dicts as JS arrays/objects?** Lets all built-in
  methods operate directly on familiar data structures with no
  marshalling overhead, while still preserving JS semantics through the
  helpers in `runtime/values.py`.
- **Control flow via exceptions.** `return`, `break`, `continue`, and
  `throw` are implemented as internal Python exceptions (`_Return`,
  `_Break`, `_Continue`, `_JSThrow`). This keeps the interpreter
  recursive and the AST node handlers tiny, at a small perf cost.

## Limitations

This is a sizeable subset of JavaScript, not a 100% ES spec implementation.
Notable gaps (not required by the hackathon spec):

- No prototypes / `class` / inheritance / `this` binding tricks beyond
  basic method calls.
- No async/await / Promises / generators.
- Template literals are tokenized but `${...}` interpolation is not
  evaluated.
- No regex literals.
- Number semantics use Python `int`/`float`; very large numbers and some
  edge bit-twiddling cases will not match V8 byte-for-byte.

These can be added incrementally without changing the architecture.
