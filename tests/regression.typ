// Regression battery for feasible-region.
// Render check: `typst compile --root . tests/regression.typ out.pdf`.
// Mathematical correctness is checked separately in analysis.typ and check.py.
#import "../lib.typ": feasible-region
#set page(width: auto, height: auto, margin: 1cm)
#set text(9pt)

// -- canonical cases --------------------------------------------------------

// 1. bounded + unique optimum       → Z = 13 at (3,1)
#feasible-region(((1,1,4,"<="),(1,3,6,"<=")), objective: (3,4), sense: "max")
#pagebreak()

// 2. unbounded + finite minimum     → Z = 8 at (4,0)
#feasible-region(((1,1,4,">="),(1,0,1,">=")), objective: (2,3), sense: "min")
#pagebreak()

// 3. unbounded objective            → "no finite maximum"
#feasible-region(((1,1,4,">="),(1,0,1,">=")), objective: (1,1), sense: "max")
#pagebreak()

// 4. multiple optima (segment)      → Z = 4 on the segment (0,4)–(3,1)
#feasible-region(((1,1,4,"<="),(1,0,3,"<=")), objective: (1,1), sense: "max")
#pagebreak()

// 5. multiple optima (ray)          → Z = 1 on the ray from (0,1) along +x
#feasible-region(((0,1,1,">="),), objective: (0,1), sense: "min")
#pagebreak()

// 6. outside the first quadrant     → Z = 5 at (1,2)
#feasible-region(
  ((1,0,3,"<="),(1,0,-2,">="),(0,1,2,"<="),(0,1,-1,">="),(1,1,3,"<=")),
  objective: (1,2), sense: "max", first-quadrant: false,
)
#pagebreak()

// 7. strict inequality              → triangle (0,0),(4,0),(0,4), dashed boundary
#feasible-region(((1,1,4,"<"),))
#pagebreak()

// 8. incompatible system            → "Infeasible region"
#feasible-region(((1,0,5,">="),(1,0,3,"<=")))
#pagebreak()

// 9. localization (Spanish)         → same as (1), labels in Spanish
#feasible-region(((1,1,4,"<="),(1,3,6,"<=")), objective: (3,4), sense: "max", lang: "es")

// -- degenerate / adversarial (must not panic) ------------------------------
#pagebreak()
// point region
#feasible-region(((1,0,2,"<="),(1,0,2,">="),(0,1,2,"<="),(0,1,2,">=")), objective: (1,1))
#pagebreak()
// duplicate + always-true constraints
#feasible-region(((1,1,4,"<="),(1,1,4,"<="),(0,0,5,"<=")), objective: (1,1), sense: "max")
#pagebreak()

// -- colors ------------------------------------------------------------------
// per-constraint color (5th element), objective color (3rd), and region-color
#feasible-region(
  ((1, 1, 4, "<=", red), (1, 3, 6, "<=", teal)),
  objective: (3, 4, olive), region-color: rgb("#2b8a3e"),
)
#pagebreak()
// many constraints → distinct auto colors, no repeats
#feasible-region(
  ((1,0,7,"<="),(0,1,7,"<="),(1,1,11,"<="),(2,1,13,"<="),(1,2,13,"<="),(3,1,17,"<="),(1,3,17,"<="),(1,1,2,">=")),
  objective: (1,1), sense: "max",
)

// -- regressions from the correctness review ---------------------------------
#pagebreak()
// narrow cone: unbounded region and objective
#feasible-region(((0.01,-1,0,"<="),(0.02,-1,0,">=")), objective: (1,0))
#pagebreak()
// oblique optimal ray along y=x, with a continuation arrow
#feasible-region(((-1,1,0,">="),), objective: (-1,1), sense: "min")
#pagebreak()
// supremum 4, not attained; no optimal table rows or solid optimal segment
#feasible-region(((1,1,4,"<"),), objective: (1,1))
#pagebreak()
// empty strict system: no fill or vertices
#feasible-region(((1,0,1,">"),(1,0,1,"<=")), objective: (1,0))
#pagebreak()
// distant vertex-free half-plane: minimum 100 on the entire line x=100
#feasible-region(((1,0,100,">="),), objective: (1,0), sense: "min", first-quadrant: false)
#pagebreak()
// open optimal segment: all interior points optimal, both endpoints excluded
#feasible-region(((1,1,4,"<="),(1,0,0,">"),(0,1,0,">")), objective: (1,1))
#pagebreak()
// zero objective: whole region highlighted
#feasible-region(((1,1,4,"<="),), objective: (0,0))
#pagebreak()
// strict boundary through origin: visible dashed y=2x, no solid underlay
#feasible-region(((-2,1,0,"<"),(1,0,4,"<="),(0,1,4,"<=")))
#pagebreak()
// table disabled: unbounded-objective warning must remain visible
#feasible-region(((1,1,4,">="),), objective: (1,1), table: false)
#pagebreak()
// rescaled triangle: same finite optimum and plot as x+y<=4
#feasible-region(((1e-10,1e-10,4e-10,"<="),), objective: (1,1))
#pagebreak()
// vertex-free open strip: localized unattained infimum
#feasible-region(((1,0,100,">"),(1,0,101,"<")), objective: (1,0), sense: "min", first-quadrant: false, lang: "es")
#pagebreak()
// anisotropic scales: descent arrow remains perpendicular, labeled min Z
#feasible-region(((1,1,4,">="),(1,0,1,">=")), objective: (2,3), sense: "min", equal-aspect: false)
#pagebreak()
// zero objective on a degenerate segment: whole segment is optimal
#feasible-region(((1,1,4,"<="),(1,1,4,">=")), objective: (0,0))
