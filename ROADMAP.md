# Constraint-Based Layout Composition — Roadmap

## Architectural Decision

**Approach**: Declarative Constraints + Procedural Resolvers + Dependency Graph

**Rejected alternatives**:
- ❌ General CSP solver (python-constraint, z3) — can't handle 3D rigid-body geometry with rotations
- ❌ Full automatic solver — search space too large (continuous X,Y,Z,rotation × N components)
- ❌ Recommender-only — doesn't produce placements, requires manual iteration

**Core design**:
1. **Constraint dataclasses** (`layouts/constraints.py`) — declare the *what* (edge alignment, clearance, Z-stack, cable path, etc.)
2. **Procedural resolvers** (`layouts/resolvers/`) — small (~30 lines each) geometric procedures for the *how*
3. **LayoutComposer** (`layouts/composer.py`) — builds a dependency graph, topo-sorts constraints, dispatches to resolvers, post-validates

---

## Files

### New files
```
layouts/
├── constraints.py        # Constraint dataclass hierarchy
├── composer.py           # LayoutComposer, ConstraintResolver protocol
├── layout_constrained.py # ConstraintLayout (Layout subclass)
├── resolvers/
│   └── __init__.py       # Default resolver registry
```

### Modified files
```
layouts/__init__.py       # +ConstraintLayout in LAYOUTS
```

### Files ported later (Phases 1-5)
```
layouts/layout_default_v2.py   # Constraint-based default (Phase 2)
layouts/layout_compact_v2.py   # Constraint-based compact (Phase 5)
```

---

## Constraint Hierarchy (`layouts/constraints.py`)

```python
Constraint (base, frozen dataclass)
├── kind: str
├── priority: ConstraintPriority  # HARD / SOFT / GOAL
├── description: str

Concrete types:
├── EdgeAlignment      # Align component edge to another edge (or enclosure wall)
├── CenteredOn          # Center component on axis within region
├── Clearance           # Minimum gap between component keepouts
├── ZStack              # Stacking order with Z-gaps between layers
├── SharePlane          # Components on same Z plane
├── RegionConstraint    # Component within named region of enclosure interior
├── CablePath           # Cable route between connectors with straight-line passage
├── FootprintMatch      # Two enclosure halves share XY footprint
├── RelativePlacement   # Component B relative to A with explicit offset
├── TargetEnvelope      # Optional hint for enclosure size (used by region constraints)
```

---

## Resolver Protocol (`layouts/composer.py`)

```python
class ConstraintResolver(Protocol):
    kind: str  # matches Constraint.kind

    def resolve(
        self,
        constraint: Constraint,
        components: dict[str, Component],
        current: dict[str, Placement],
        config: Config,
    ) -> ResolverResult: ...
```

**ResolverResult**:
- `success: bool`
- `placements: dict[str, Placement]` — new/changed only
- `message: str` — error or info

---

## LayoutComposer Flow

```
Layout recipe (list[Constraint])
    │
    ▼
LayoutComposer.compose(constraints, components, config)
    │
    ├─ Build dependency graph
    ├─ Topological sort
    ├─ For each constraint:
    │     dispatch to registered resolver
    │     resolver reads current placements
    │     resolver writes new/modified placements
    │
    ├─ Post-pass: validate ALL constraints
    │     - HARD: error if violated
    │     - SOFT: warn if violated
    │     - GOAL: report metric
    │
    ▼
list[Placement] + ConstraintReport
```

---

## Refactoring Phases

### Phase 0 ✅ (current)
**Infrastructure** — no behavior change:
- `constraints.py` with dataclass hierarchy
- `composer.py` skeleton (stub compose that returns empty)
- `resolvers/__init__.py` with default registry
- `layout_constrained.py` — ConstraintLayout subclass
- Wire into `layouts/__init__.py`

### Phase 1 — Core Resolvers
Implement 3 resolvers:
1. **EdgeAlignmentResolver** — align component edge to enclosure edge or another component
2. **CenteredOnResolver** — center component on X/Y within enclosure or relative to another
3. **ZStackResolver** — assign Z to layers

### Phase 2 — Full Coverage + Port Default Layout
Implement remaining resolvers:
- ClearanceResolver, RegionResolver, CablePathResolver, FootprintMatchResolver, RelativePlacementResolver
- Rewrite `LayoutDefault` as constraints in `layout_default_v2.py`
- Verify output matches original to floating-point tolerance

### Phase 3 — Post-Validation
- Add `ConstraintReport` to `LayoutComposer.compose()`
- Wire constraint report into pipeline's validation step
- 3 existing validation checks migrate to constraint post-validation

### Phase 4 — Config-Driven Recipes
- Load constraint recipes from YAML
- Allow per-layout YAML files in `config/layouts/`
- `--layout-recipe` CLI flag

### Phase 5 — Port Compact Layout
- Rewrite `LayoutCompact` as constraints
- Remove old layouts after verification

---

## Suggested Constraint Priority

| Priority | Resolver behavior | Post-check behavior |
|----------|-------------------|---------------------|
| **HARD** | Must satisfy. Error if impossible. | Error — build stops |
| **SOFT** | Satisfy if possible, but other HARD constraints take priority | Warning — build continues |
| **GOAL** | Record optimization metric | Metric printed in report |

---

## Migration Principle

**Old layouts keep working during every phase.** The `Layout` ABC is unchanged. `ConstraintLayout` is a new subclass added alongside existing layouts. There is never a broken pipeline.

---

## Key Design Rules

- **No CadQuery imports** in constraints, composer, or resolvers — all pure geometry math
- **`--steps data` continues to work** without miniforge
- **Every module passes `python -m py_compile`**
- Resolvers are **testable in isolation** (~30 lines each)
