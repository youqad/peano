from dataclasses import dataclass
from enum import Enum
from random import randint, choices, choice, sample
from typing import List
from sympy.solvers import solve
from sympy import Symbol
import click
import pickle
from tqdm import tqdm


class TermFormatType(Enum):
    LOWER_DEGREE = 0
    LOWER_DEGREE_PRODUCT = 1
    DIVISION_BY_CONSTANT = 2
    DEGREE_SUM = 3
    DEGREE_SUBTRACTION = 4
    X = 5


@dataclass
class TermFormat:
    type: TermFormatType
    probability: float
    complexity: float


@dataclass
class TermConfig:
    constants: List[str]
    formats: List[TermFormat]
    complexity: float


def generate_term(degree: int, config: TermConfig) -> str:
    """Generates a term of at most degree d"""

    def gt_r(d: int, c: int) -> str:
        # Base case, degree is zero
        if d == 0:
            return choice(config.constants)
        # Recursive case, positive degree
        available_formats = [f for f in config.formats if f.complexity <= c]
        term_format = choices(
            available_formats, weights=[f.probability for f in available_formats]
        )[0]
        c = c - term_format.complexity
        match term_format.type:
            case TermFormatType.LOWER_DEGREE:
                return gt_r(d - 1, c)
            case TermFormatType.LOWER_DEGREE_PRODUCT:
                l = randint(0, d - 1)
                return f"(* {gt_r(d-l, c)} {gt_r(l, c)})"
            case TermFormatType.DIVISION_BY_CONSTANT:
                return f"(/ {gt_r(d, c)} {gt_r(0, c)})"
            case TermFormatType.DEGREE_SUM:
                return f"(+ {gt_r(d, c)} {gt_r(d, c)})"
            case TermFormatType.DEGREE_SUBTRACTION:
                return f"(- {gt_r(d, c)} {gt_r(d, c)})"
            case TermFormatType.X:
                # TODO: higher powers of x as well
                return "x"
        raise Exception(f"Unknown term format {term_format}")

    return gt_r(degree, config.complexity)


def format(
    term: str,
) -> str:
    """Formats an equation string to be human readable,
    currently supports only binary operators that function
    like +, e.g. + - / * = etc."""

    def f_r(e: str) -> str:
        # Base case, single term
        if not e.startswith("("):
            return e
        # Recursive case
        e = e[1:-1]
        operator = e.split(" ")[0]

        def split(s: str) -> str:
            stack = []
            for i, c in enumerate(s):
                if c == "(":
                    stack.append(i)
                elif c == ")" and stack:
                    stack.pop()
                if c == ' ' and len(stack) == 0:
                    return i

        e = e[2:]
        s = split(e)
        return f"({f_r(e[:s])} {operator} {f_r(e[s+1:])})"

    return f_r(term)


def sympy_solve_equation(equation: str):
    """Solves using sympy, takes in a Peano formatted equation"""
    x = Symbol("x")  # Need this because of "eval"
    equation = format(equation)
    equation_parts = equation.split("=")
    lhs = equation_parts[0]
    rhs = equation_parts[1]
    equation = f"{lhs} - ({rhs})"
    return solve(eval(equation))


def make_config(n_constants: int, complexity: float) -> TermConfig:
    constant_pool = [str(i) for i in range(-3, 4)]
    return TermConfig(
        sample(constant_pool, n_constants),
        [
            TermFormat(TermFormatType.LOWER_DEGREE, 0.25, 0),
            TermFormat(TermFormatType.LOWER_DEGREE_PRODUCT, 0.25, 1),
            TermFormat(TermFormatType.DIVISION_BY_CONSTANT, 0.25, 1),
            TermFormat(TermFormatType.DEGREE_SUM, 0.25, 1),
            TermFormat(TermFormatType.DEGREE_SUBTRACTION, 0.25, 1),
            TermFormat(TermFormatType.X, 0.25, 0),
        ],
        complexity,
    )

@click.command()
@click.option("--n", default=100, help="Number of unique equations to generate.")
@click.option("--degree", default=1, help="The maximum degree of a generated equation.")
@click.option("--max-complexity", default=3, help="The maximum complexity of generated equations.")
@click.option("--output", default="equations.pkl", help="Output filepath (.pkl)")
def generate(n, degree, max_complexity, output):
    """Generates N equations of degree DEGREE in a pickled file OUTPUT"""
    equations = dict()
    with tqdm(total=n) as pbar:
        while len(equations) < n:
            config = make_config(randint(2, 4), randint(1, max_complexity))
            equation = (
                f"(= {generate_term(degree, config)} {generate_term(degree, config)})"
            )
            if equation in equations:
                continue
            try:
                solution = sympy_solve_equation(equation)
            except KeyboardInterrupt:
                break
            except:
                continue
            if len(solution) == 0:
                continue
            solution = str(solution[0])  # Works for linear equations
            equations[equation] = solution
            pbar.update(1)
    with open(output, 'wb') as output:
        pickle.dump(equations, output)

if __name__ == "__main__":
    generate()
