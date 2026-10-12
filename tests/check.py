#!/usr/bin/env python3
"""Run math, input-validation, text and SVG regressions with installed tools.

Uses Python's standard library, Typst and pdftotext (Poppler). All compiler
outputs are kept in memory. An isolated local package lets registry examples
compile before publication. TYPST_BIN selects a compiler for version checks.
"""
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import tomllib
import unittest
import xml.etree.ElementTree as ET
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[1]
TYPST = os.environ.get("TYPST_BIN", "typst")
PACKAGE_PATH = ROOT / "tests" / "rendered" / "packages"
PREAMBLE = '#import "/lib.typ": feasible-region\n#set page(width: auto, height: auto, margin: 1cm)\n'


def prepare_local_package():
    manifest = tomllib.loads((ROOT / "typst.toml").read_text())["package"]
    destination = PACKAGE_PATH / "preview" / manifest["name"] / manifest["version"]
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("typst.toml", "lib.typ", "geometry.typ", "README.md", "LICENSE"):
        shutil.copyfile(ROOT / name, destination / name)


def compile_source(source, fmt="pdf"):
    return subprocess.run(
        [TYPST, "compile", "--root", str(ROOT), "--package-path", str(PACKAGE_PATH), "--format", fmt, "-", "-"],
        input=source.encode(), capture_output=True, check=False,
    )


def typst_tuple(items):
    return "(" + ",".join(items) + ("," if len(items) == 1 else "") + ")"


def input_rows(constraints, first_quadrant):
    """Exact rational inequalities: coefficients . (x,y) <= rhs."""
    rows = []
    for a, b, c, op in constraints:
        sign = -1 if op in (">", ">=") else 1
        rows.append(((Fraction(sign * a), Fraction(sign * b)), Fraction(sign * c), op in ("<", ">")))
    if first_quadrant:
        rows += [((Fraction(-1), Fraction(0)), Fraction(0), False),
                 ((Fraction(0), Fraction(-1)), Fraction(0), False)]
    return rows


def eliminate(rows):
    """Fourier–Motzkin elimination of the first coordinate; strictness propagates."""
    positive = [r for r in rows if r[0][0] > 0]
    negative = [r for r in rows if r[0][0] < 0]
    out = [(a[1:], c, strict) for a, c, strict in rows if a[0] == 0]
    for ap, cp, sp in positive:
        for an, cn, sn in negative:
            out.append((tuple(p / ap[0] - n / an[0] for p, n in zip(ap[1:], an[1:])),
                        cp / ap[0] - cn / an[0], sp or sn))
    # Merge duplicates to keep intermediate systems small.
    merged = {}
    for a, c, strict in out:
        scale = next((abs(v) for v in a if v), abs(c) or Fraction(1))
        key = (tuple(v / scale for v in a), c / scale)
        merged[key] = merged.get(key, False) or strict
    return [(a, c, strict) for (a, c), strict in merged.items()]


def exact_projection(constraints, objective, sense, first_quadrant):
    """Independent oracle: project the feasible set onto Z, without vertices/rays."""
    rows = [(a + (Fraction(0),), c, s) for a, c, s in input_rows(constraints, first_quadrant)]
    gx, gy = map(Fraction, objective)
    rows += [((gx, gy, Fraction(-1)), Fraction(0), False),
             ((-gx, -gy, Fraction(1)), Fraction(0), False)]
    rows = eliminate(eliminate(rows))
    lower, upper = None, None
    lower_open = upper_open = False
    for (a,), c, strict in rows:
        if a == 0:
            if c < 0 or (c == 0 and strict):
                return "infeasible", None
        elif a > 0:
            bound = c / a
            if upper is None or bound < upper:
                upper, upper_open = bound, strict
            elif bound == upper:
                upper_open |= strict
        else:
            bound = c / a
            if lower is None or bound > lower:
                lower, lower_open = bound, strict
            elif bound == lower:
                lower_open |= strict
    if lower is not None and upper is not None:
        if lower > upper or (lower == upper and (lower_open or upper_open)):
            return "infeasible", None
    value, is_open = (upper, upper_open) if sense == "max" else (lower, lower_open)
    if value is None:
        return "unbounded", None
    return ("unattained" if is_open else "finite"), value


class Correctness(unittest.TestCase):
    def svg(self, call):
        result = compile_source(PREAMBLE + call, "svg")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return [node.attrib for node in ET.fromstring(result.stdout).iter()
                if node.tag.endswith("}path")]

    def text(self, call):
        result = compile_source(PREAMBLE + call)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        result = subprocess.run(["pdftotext", "-", "-"], input=result.stdout, capture_output=True, check=True)
        return " ".join(result.stdout.decode().split())

    def test_mathematical_assertions_and_render_battery(self):
        for source in ("analysis.typ", "regression.typ", "../gallery/examples.typ", "../gallery/g2-es.typ", "../gallery/additional.typ"):
            with self.subTest(source=source):
                result = subprocess.run([TYPST, "compile", "--root", str(ROOT), "--package-path", str(PACKAGE_PATH),
                                         str(ROOT / "tests" / source), "-"], capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_independent_exact_projection(self):
        rng = random.Random(137)
        cases = []
        for _ in range(100):
            constraints = [(rng.randrange(-3, 4), rng.randrange(-3, 4), rng.randrange(-5, 6),
                            rng.choice(("<", "<=", ">", ">=")))
                           for _ in range(rng.randrange(0, 6))]
            cases.append((constraints, (rng.randrange(-3, 4), rng.randrange(-3, 4)),
                          rng.choice(("min", "max")), rng.choice((True, False))))
        source = '#import "/geometry.typ": analyze\n'
        for i, (rows, objective, sense, quadrant) in enumerate(cases):
            constraints = typst_tuple([typst_tuple([str(a), str(b), str(c), json.dumps(op)]) for a, b, c, op in rows])
            source += f'#let m{i} = analyze({constraints}, objective: {typst_tuple(list(map(str, objective)))}, sense: {json.dumps(sense)}, first-quadrant: {str(quadrant).lower()})\n'
            source += f'#metadata((status: m{i}.status, value: m{i}.value, bounded: m{i}.bounded))<result>\n'
        result = subprocess.run([TYPST, "query", "--root", str(ROOT), "-", "<result>", "--field", "value"],
                                input=source.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        actual = json.loads(result.stdout)
        self.assertEqual(len(actual), len(cases))
        for case, model in zip(cases, actual):
            with self.subTest(case=case):
                status, value = exact_projection(*case)
                actual_status = model["status"] if model["status"] in ("infeasible", "unbounded", "unattained") else "finite"
                self.assertEqual(actual_status, status)
                if value is not None:
                    self.assertTrue(math.isclose(model["value"], float(value), abs_tol=1e-8))
                if status != "infeasible":
                    bounded = all(exact_projection(case[0], g, "max", case[3])[0] != "unbounded"
                                  for g in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                    self.assertEqual(model["bounded"], bounded)

    def test_invalid_inputs_have_explicit_errors(self):
        cases = [
            ('#feasible-region(1)', "constraints must be an array"),
            ('#feasible-region(((1,1,4),))', "must contain (a, b, c, op"),
            ('#feasible-region(((1,1,4,"=="),))', "constraint operator must be"),
            ('#feasible-region(((1,"x",4,"<="),))', "constraint coefficients must be finite"),
            ('#feasible-region(((1,1,calc.inf,"<="),))', "constraint coefficients must be finite"),
            ('#feasible-region(((1e-300,0,1e300,"<="),))', "normalized constraint exceeds the floating-point range"),
            ('#feasible-region(((1,1,4,"<=",3),))', "constraint color must be a color"),
            ('#feasible-region((), objective: (1,))', "objective must contain"),
            ('#feasible-region((), objective: (1,"x"))', "objective coefficients must be finite"),
            ('#feasible-region((), objective: (1,1,3))', "objective color must be a color"),
            ('#feasible-region((), sense: "minimize")', "sense must be max or min"),
            ('#feasible-region((), size: (0,4))', "size must contain two positive"),
            ('#feasible-region((), margin: 0.9)', "margin must be a finite number >= 1"),
            ('#feasible-region((), gradient: 1)', "must be booleans"),
            ('#feasible-region((), first-quadrant: 1)', "first-quadrant must be a boolean"),
            ('#feasible-region((), region-color: 1)', "region-color must be a color"),
            ('#feasible-region((), lang: "fr")', "lang must be en or es"),
            ('#feasible-region(((1,1,4,"<="),), labels: ())', "labels must contain one entry"),
        ]
        for call, message in cases:
            with self.subTest(call=call):
                result = compile_source(PREAMBLE + call)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr.decode())

    def test_table_does_not_hide_diagnostics(self):
        for table in ("true", "false"):
            with self.subTest(table=table):
                text = self.text(f'#feasible-region(((1,1,4,">="),), objective: (1,1), table: {table})')
                self.assertIn("No finite max:", text)
                text = self.text(f'#feasible-region(((1,1,4,"<"),), objective: (1,1), table: {table})')
                self.assertIn("Supremum:", text)
                self.assertIn("not attained", text)

    def test_vertex_free_optimum_and_zero_objective_text(self):
        text = self.text('#feasible-region(((1,0,100,">="),), objective: (1,0), sense: "min", first-quadrant: false)')
        self.assertNotIn("Infeasible", text)
        self.assertIn("optimal line", text)
        text = self.text('#feasible-region(((1,1,4,"<="),), objective: (0,0))')
        self.assertIn("Every feasible point is optimal", text)
        self.assertNotIn("segment", text)
        text = self.text('#feasible-region(((1,1,4,"<"),), objective: (1,1), lang: "es")')
        self.assertIn("Supremo:", text)
        self.assertIn("no alcanzado", text)

    def test_small_scaled_objective_keeps_its_nonzero_value(self):
        text = self.text('#feasible-region(((1,1,4,"<="),), objective: (1e-10,1e-10))')
        self.assertIn("0.0000000004", text)
        self.assertIn("Multiple solution:", text)

    def test_corner_boundary_has_distinct_endpoints(self):
        paths = self.svg('#feasible-region(((-2,1,0,"<="),(1,0,4,"<="),(0,1,4,"<=")))')
        boundary = [p for p in paths if p.get("stroke") == "#1a9850"]
        self.assertEqual(len(boundary), 1)
        self.assertIn("l ", boundary[0]["d"])

    def test_strict_boundary_has_no_solid_underlay(self):
        paths = self.svg('#feasible-region(((1,1,4,"<"),))')
        boundary = [p for p in paths if p.get("stroke") == "#1a9850"]
        self.assertEqual(len(boundary), 1)
        self.assertTrue(boundary[0].get("stroke-dasharray"))
        border = [p for p in paths if p.get("stroke-width") == "0.9" and p.get("stroke") == "#22477a"]
        self.assertEqual(len(border), 2)  # Only the two included coordinate axes.

    def test_minimum_arrow_points_toward_decreasing_values(self):
        import re
        for aspect in ("true", "false"):
            with self.subTest(aspect=aspect):
                paths = self.svg(f'#feasible-region(((1,1,4,">="),(1,0,1,">=")), objective: (2,3), sense: "min", equal-aspect: {aspect})')
                gradient = [p for p in paths if p.get("stroke") == "#6a1b9a" and p.get("stroke-width") == "1.1" and "Z" not in p.get("d", "")]
                self.assertEqual(len(gradient), 1)
                step = re.search(r"l (-?[\d.]+) (-?[\d.]+)", gradient[0]["d"])
                self.assertIsNotNone(step)
                dx, dy = map(float, step.groups())
                self.assertLess(dx, 0)
                self.assertGreater(dy, 0)  # SVG's y axis points downward.
                optimum_line = [p for p in paths if p.get("stroke") == "#6a1b9a" and p.get("stroke-width") == "1.2"]
                self.assertEqual(len(optimum_line), 1)
                line_step = re.search(r"l (-?[\d.]+) (-?[\d.]+)", optimum_line[0]["d"])
                self.assertIsNotNone(line_step)
                tx, ty = map(float, line_step.groups())
                self.assertAlmostEqual((dx * tx + dy * ty) / math.hypot(dx, dy) / math.hypot(tx, ty), 0, places=7)

    def test_optimization_arrow_labels_match_the_sense(self):
        source = (PREAMBLE + '#feasible-region(((1,1,4,">="),(1,0,1,">=")), objective: (2,3), sense: "min")\n'
                  '#pagebreak()\n#feasible-region(((1,1,4,"<="),(1,3,6,"<=")), objective: (3,4), sense: "max")')
        result = compile_source(source)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        result = subprocess.run(["pdftotext", "-", "-"], input=result.stdout, capture_output=True, check=True)
        pages = ["".join(page.split()) for page in result.stdout.decode().split("\f")]
        self.assertIn("min𝑍", pages[0])
        self.assertIn("max𝑍", pages[1])
        self.assertNotIn("∇", pages[0])
        self.assertNotIn("∇", pages[1])

    def test_unattained_face_is_never_highlighted_as_solid(self):
        paths = self.svg('#feasible-region(((1,1,4,"<"),), objective: (1,1))')
        highlights = [p for p in paths if p.get("stroke-width") == "3.4"]
        self.assertEqual(len(highlights), 1)
        self.assertTrue(highlights[0].get("stroke-dasharray"))

    def test_optimal_ray_and_line_have_continuation_arrows(self):
        for call, expected in (
            ('#feasible-region(((-1,1,0,">="),), objective: (-1,1), sense: "min")', 1),
            ('#feasible-region(((1,0,100,">="),), objective: (1,0), sense: "min", first-quadrant: false)', 2),
        ):
            with self.subTest(call=call):
                paths = self.svg(call)
                arrows = [p for p in paths if p.get("stroke") == "#6a1b9a" and p.get("stroke-width") == "3.4" and "Z" in p.get("d", "")]
                self.assertEqual(len(arrows), expected)


if __name__ == "__main__":
    prepare_local_package()
    unittest.main(verbosity=2)
