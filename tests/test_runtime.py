"""Unit tests. Run with:  python -m unittest js_runtime.tests.test_runtime"""
import io, sys, unittest, contextlib, os

# allow running tests from any cwd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from js_runtime.lexer import Tokenizer
from js_runtime.parser import Parser
from js_runtime.runtime import Interpreter


def run_js(src: str) -> str:
    tokens = Tokenizer(src).tokenize()
    ast = Parser(tokens).parse()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().run(ast)
    return buf.getvalue()


class HackathonTests(unittest.TestCase):
    def test_case_1_even_odd(self):
        src = 'let num = 7; if (num % 2 === 0) { console.log(num + " is Even"); } else { console.log(num + " is Odd"); }'
        self.assertEqual(run_js(src), "7 is Odd\n")

    def test_case_2_pattern(self):
        src = '''
        for (let i = 1; i <= 5; i++) {
          let row = "";
          for (let j = 1; j <= i; j++) row += "*";
          console.log(row);
        }'''
        self.assertEqual(run_js(src), "*\n**\n***\n****\n*****\n")

    def test_case_3_armstrong(self):
        src = '''
        function isArmstrong(num) {
          let temp = num, sum = 0;
          while (temp > 0) { let d = temp % 10; sum += d ** 3; temp = Math.floor(temp/10); }
          return sum === num;
        }
        console.log(isArmstrong(153));
        console.log(isArmstrong(123));
        '''
        self.assertEqual(run_js(src), "true\nfalse\n")

    def test_case_4_spread_reverse(self):
        src = '''
        let arr = [1,2,3,4,5];
        let reversed = [...arr].reverse();
        console.log("Original: " + arr.join(", "));
        console.log("Reversed: " + reversed.join(", "));
        '''
        self.assertEqual(run_js(src), "Original: 1, 2, 3, 4, 5\nReversed: 5, 4, 3, 2, 1\n")

    def test_case_5_palindrome(self):
        src = '''
        let s = "racecar";
        let r = s.split("").reverse().join("");
        console.log(s === r ? s + " is a Palindrome" : s + " is not a Palindrome");
        '''
        self.assertEqual(run_js(src), "racecar is a Palindrome\n")


class CoreFeatureTests(unittest.TestCase):
    def test_closure(self):
        src = '''
        function mk(){ let c=0; return function(){ c++; return c; }; }
        let f = mk();
        console.log(f()); console.log(f()); console.log(f());
        '''
        self.assertEqual(run_js(src), "1\n2\n3\n")

    def test_coercion(self):
        src = 'console.log(1+"2"); console.log("5"*2); console.log(true+1);'
        self.assertEqual(run_js(src), "12\n10\n2\n")

    def test_loose_strict_equality(self):
        src = 'console.log(null == undefined); console.log(null === undefined);'
        self.assertEqual(run_js(src), "true\nfalse\n")

    def test_array_methods(self):
        src = 'console.log([1,2,3].map(x=>x*2).filter(x=>x>2).reduce((a,b)=>a+b,0));'
        self.assertEqual(run_js(src), "10\n")

    def test_rest_spread(self):
        src = 'function s(...n){let t=0;for(let x of n)t+=x;return t;} console.log(s(...[1,2,3,4]));'
        self.assertEqual(run_js(src), "10\n")

    def test_try_catch(self):
        src = 'try { throw new Error("x"); } catch(e) { console.log(e.message); }'
        self.assertEqual(run_js(src), "x\n")

    def test_switch(self):
        src = '''
        function d(n){ switch(n){ case 1: return "a"; case 2: return "b"; default: return "?"; } }
        console.log(d(1)); console.log(d(2)); console.log(d(9));
        '''
        self.assertEqual(run_js(src), "a\nb\n?\n")


if __name__ == "__main__":
    unittest.main()
