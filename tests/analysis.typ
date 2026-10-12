// Mathematical regression tests. These assertions do not import CeTZ.
#import "../geometry.typ": analyze, satisfies, dot, epsilon, line-in-frame
#let close(a, b) = calc.abs(a - b) < 1e-8
#let check(R, status, value: none, objective: (1, 1), sense: "max", first-quadrant: true) = {
  let m = analyze(R, objective: objective, sense: sense, first-quadrant: first-quadrant)
  assert.eq(m.status, status)
  if value != none { assert(close(m.value, value), message: repr(m)) }
  if m.feasible { assert(satisfies(m.witness, m.constraints, open: true)) }
  if ("unique", "segment", "ray", "line", "all").contains(status) {
    assert(satisfies(m.optimum, m.constraints, open: true))
    assert(close(dot(objective, m.optimum), m.value))
  }
  m
}
#let triangle = ((1, 1, 4, "<="), (1, 3, 6, "<="))
#let m = check(triangle, "unique", objective: (3, 4), value: 13)
#assert(close(m.optimum.at(0), 3) and close(m.optimum.at(1), 1))
#assert.eq(m.vertices.len(), 4)
#assert(m.bounded)
#let m = check(((1, 1, 4, ">="), (1, 0, 1, ">=")), "unique", objective: (2, 3), sense: "min", value: 8)
#assert(not m.bounded)
#let m = check(((1, 1, 4, ">="),), "unbounded")
#let m = check(((1, 1, 4, "<="), (1, 0, 3, "<=")), "segment", value: 4)
#let m = check(((0, 1, 1, ">="),), "ray", objective: (0, 1), sense: "min", value: 1)
#let m = check(((1, 0, 5, ">="), (1, 0, 3, "<=")), "infeasible")

// Narrow cones and oblique zero-cost rays cannot fall between angular samples.
#let m = check(((0.01, -1, 0, "<="), (0.02, -1, 0, ">=")), "unbounded", objective: (1, 0))
#assert(not m.bounded)
#let m = check(((-1, 1, 0, ">="),), "ray", objective: (-1, 1), sense: "min", value: 0)
#let m = check(((1, -1, 0, "<="), (-1, 1, 0, "<=")), "line", objective: (1, -1), first-quadrant: false, value: 0)

// Positive rescaling of individual constraints or objectives preserves meaning.
#for scale in (1e-10, 1e-5, 1, 1e5, 1e10) {
  let R = triangle.map(r => (r.at(0) * scale, r.at(1) * scale, r.at(2) * scale, r.at(3)))
  let m = check(R, "unique", objective: (3, 4), value: 13)
  assert(m.bounded)
  let m = check(triangle, "unique", objective: (3 * scale, 4 * scale), value: 13 * scale)
  assert(calc.abs(m.value - 13 * scale) <= 1e-8 * calc.abs(13 * scale))
  assert.eq(m.optimal-indices.len(), 1)
  let m = check(((1, 1, 4, ">="),), "unbounded", objective: (scale, scale))
}

// Closed feasibility is not sufficient for a strict system.
#let m = check(((1, 1, 4, "<"),), "unattained", value: 4)
#assert.eq(m.optimal-indices, ())
#let m = check(((1, 1, 2, ">"),), "unattained", sense: "min", value: 2)
#let m = check(((1, 0, 1, ">"), (1, 0, 1, "<=")), "infeasible")
#assert.eq(m.witness, none)
#assert(m.bounded)
#assert.eq(m.recession, ())
#let m = check(((1, 0, 0, "<"),), "infeasible")
#let m = check(((0, 0, 0, "<"),), "infeasible")
#let m = check(((0, 0, 1, ">="),), "infeasible")
#let m = check(((0, 0, 1, "<"),), "unbounded")
#let m = check(((1, 1, 4, "<="), (1, 0, 0, ">"), (0, 1, 0, ">")), "segment", value: 4)
#assert.eq(m.optimal-indices, ()) // The open edge has optima, but neither endpoint.
#let m = check(((1, 1, 4, "<="), (1, 0, 5, "<")), "segment", value: 4)
#let m = check(((1, 0, 2, ">"), (0, 1, 1, ">=")), "ray", objective: (0, 1), sense: "min", value: 1)

// Vertex-free systems: half-plane, strip, line, plane; far from the origin too.
#let m = check(((1, 0, 100, ">="),), "line", objective: (1, 0), sense: "min", value: 100, first-quadrant: false)
#assert.eq(m.vertices, ())
#let m = check(((1, 0, -100, "<="),), "line", objective: (1, 0), value: -100, first-quadrant: false)
#let m = check(((1, 0, 100, ">="), (1, 0, 101, "<=")), "line", objective: (1, 0), sense: "min", value: 100, first-quadrant: false)
#let m = check(((1, 0, 100, ">"), (1, 0, 101, "<")), "unattained", objective: (1, 0), sense: "min", value: 100, first-quadrant: false)
#let m = check(((1, 0, 1e12, ">"), (1, 0, 1e12 + 1, "<")), "unattained", objective: (1, 0), sense: "min", value: 1e12, first-quadrant: false)
#let m = check((), "unbounded", first-quadrant: false)
#let m = check((), "all", objective: (0, 0), value: 0, first-quadrant: false)
#let m = check(triangle, "all", objective: (0, 0), value: 0)
#assert.eq(m.optimal-indices.len(), 4)
#let m = check(((1, 1, 4, "<="),), "none", objective: none)

// Degenerate bounded regions and redundant constant constraints.
#let m = check(((1, 0, 2, "<="), (1, 0, 2, ">="), (0, 1, 2, "<="), (0, 1, 2, ">=")), "unique", value: 4)
#let m = check(((1, 1, 4, "<="), (1, 1, 4, ">=")), "segment", value: 4)
#let m = check(((1, 1, 4, "<="), (1, 1, 4, "<="), (0, 0, 5, "<=")), "segment", value: 4)

// A line through a frame corner needs two distinct endpoints.
#let points = line-in-frame(-2, 1, 0, 0, 0, 4.6, 4.6)
#assert.eq(points.len(), 2)
#assert.eq(points.first(), (0.0, 0.0))
#assert(close(points.last().at(0), 2.3) and close(points.last().at(1), 4.6))

Mathematical assertions passed.
