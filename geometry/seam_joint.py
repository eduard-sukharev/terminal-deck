"""Glued filament pins that align adjacent Sections of a part (ADR 0003, 0006).

A pin is not a lug and has no bore. Two parallel printed fins straddle the
Seam and leave a ``gap``-wide slot between them; a length of filament is glued
into the slot while the part is assembled. The pin therefore registers the two
Sections and holds them while the screws that cross the Seam are still out --
the job the whole joint needs at the start of assembly, not a structural
member.

The fins may stand up from a floor (the Tray) or hang down from a ceiling (the
Deck, the Bezel); :func:`pin_planes` says which, per part. They are added to
the whole part *before* it is split, so the split cuts each fin in half and
every Section prints its own share (``engagement`` = half the fin length).

Sites are placements, not derived geometry: ``slide.seam_pin_sites`` lists the
pocket centres along each Seam, each annotated with why it is clear of the
interior. The build checks that every site sits on a straight run of the Seam
and clear of everything the part already holds (:func:`pocket_rect` and
:func:`pocket_z` are what those checks measure).
"""

from __future__ import annotations

from utilities import cad_helpers

#: The parts whose Seams take pins, in build order.
SEAM_PIN_PARTS: tuple[str, ...] = (
    "chassis_tray",
    "chassis_deck",
    "screen_lid_bezel",
    "screen_lid_back",
)

#: How far a fin is sunk into the substrate it grows from, so the union is a
#: real overlap rather than a face-to-face touch (mm).
SINK: float = 0.5


def pin_planes(config, budget) -> dict[str, tuple[float, bool]]:
    """Each part's ``(substrate z, fins stand up?)``, in the device frame.

    A fin grows out of the surface the part prints on or hangs from: the
    Tray's floor (up), the Deck's top skin and the Bezel's front panel (down),
    the Back plate's inner face (up). Deriving all four here keeps the case
    builders and the checks on one source.
    """
    wall = config.wall_thickness
    slide = config.slide
    lid_bottom = budget.chassis_top + slide.lid_clearance
    return {
        "chassis_tray": (wall, True),
        "chassis_deck": (budget.chassis_top - wall, False),
        "screen_lid_bezel": (budget.thickness - slide.lid_front, False),
        "screen_lid_back": (lid_bottom + slide.lid_back, True),
    }


def _dedupe(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Drop consecutive duplicate points (a zero chamfer makes two coincide)."""
    out: list[tuple[float, float]] = []
    for point in points:
        if not out or point != out[-1]:
            out.append(point)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def fin_profile(pin, side: int) -> list[tuple[float, float]]:
    """One fin's ``(y, z)`` cross-section, measured from the pocket centre.

    ``side`` is -1 for the fin on the slot's negative-Y side and +1 for the
    other. ``z`` runs from ``-SINK`` (inside the substrate) to the free end, so
    the same profile serves a fin that stands up and one that hangs down; the
    caller mirrors it by the growth direction.

    The wall thickness (``fin``) is constant from top to bottom. The chamfer is
    a 45° expansion at the base: from the substrate surface, a triangle
    extends outward by ``chamfer`` so the fin flares into the floor. The slot
    face (inner wall) stays square and vertical.
    """
    inner = side * pin.gap / 2.0
    outer = side * (pin.gap / 2.0 + pin.fin)
    points = [
        (inner, -SINK),
        (outer + side * pin.chamfer, -SINK),
        (outer, -SINK + pin.chamfer),
        (outer, pin.height),
        (inner, pin.height),
    ]
    return _dedupe(points)


def pocket_rect(pin, x: float, y: float) -> tuple[float, float, float, float]:
    """``(x0, x1, y0, y1)`` of the pocket centred on the Seam at ``(x, y)``.

    The pocket is X-normal: the fins run across the Seam, the slot between them
    runs along it. Every configured site is on a straight (X-constant) run, so
    this rectangle is exact.
    """
    return (
        x - pin.engagement,
        x + pin.engagement,
        y - pin.pocket_width / 2.0,
        y + pin.pocket_width / 2.0,
    )


def pocket_z(pin, substrate: float, upward: bool) -> tuple[float, float]:
    """Z span of the pocket, including the part sunk into the substrate (mm)."""
    if upward:
        return (substrate - SINK, substrate + pin.height)
    return (substrate - pin.height, substrate + SINK)


def fins(
    pin,
    x: float,
    y: float,
    substrate: float,
    upward: bool,
    chamfer: bool = True,
    length: float | None = None,
):
    """The two fin solids of one pocket, in the device frame.

    ``chamfer=False`` drops the 45° base flare (the outer wall runs straight
    down into the substrate), which a part with little room around the pocket
    needs -- the keyboard plate is only one wall thick beside its key rows.
    ``length`` overrides ``pin.length``: the fins' extent across the Seam, so
    their engagement. A part whose Seam jogs uses it to bridge a step of that
    length, half of it into each Section.
    """
    length = pin.length if length is None else length
    sign = 1.0 if upward else -1.0
    solids = []
    for side in (-1, 1):
        profile = [
            (py, substrate + sign * pz) for py, pz in fin_profile(pin, side)
        ]
        if not chamfer:
            profile = _square_fin(profile, side, pin)
        fin = cad_helpers.extrude_profile_x(profile, length)
        solids.append(cad_helpers.translate(fin, x, y, 0.0))
    return solids


def _square_fin(
    profile: list[tuple[float, float]], side: int, pin
) -> list[tuple[float, float]]:
    """Drop the base flare: the fin becomes a plain rectangle (no 45° base)."""
    inner = side * pin.gap / 2.0
    outer = side * (pin.gap / 2.0 + pin.fin)
    base_z = min(z for _, z in profile)
    top_z = max(z for _, z in profile)
    return [(inner, base_z), (outer, base_z), (outer, top_z), (inner, top_z)]


def step_at(seam, depth: float, y: float, tol: float = 1e-6):
    """The Seam's jog *at* ``y`` as ``(x_centre, x_travel)``, or ``None``.

    A row-jogging Seam steps sideways between rows; the jog is a horizontal
    run at one Y, so this only answers for a ``y`` on a band boundary. The jog's
    centre is the midpoint of the two band X values, its travel their distance.
    A boundary whose two bands share one X (a straight run, no actual step) and
    any ``y`` inside a band both return ``None``.
    """
    bands = seam.segments(depth)
    for (_, y1, x), nxt in zip(bands, bands[1:]):
        if abs(y - y1) <= tol:
            travel = abs(nxt[2] - x)
            if travel <= tol:
                return None
            return ((x + nxt[2]) / 2.0, travel)
    return None


def step_length(seam, depth: float, y: float) -> float | None:
    """The X travel of the Seam's jog at ``y`` (mm), or ``None`` on a straight run."""
    step = step_at(seam, depth, y)
    return None if step is None else step[1]


def pin_placement(
    seam, depth: float, y: float, pin, follow_step: bool
) -> tuple[float, float]:
    """The ``(x_centre, x_length)`` a fin pair at site ``y`` occupies.

    On a straight run this is the Seam's own X and ``pin.length``. With
    ``follow_step`` and a site on a jog, the pair is centred on the jog's
    midpoint and spans its travel plus ``2 * pin.engagement`` (so each half
    reaches at least 5 mm into its Section).
    """
    x = seam.x_at(y)
    length = pin.length
    if follow_step:
        step = step_at(seam, depth, y)
        if step is not None:
            x = step[0]
            length = step[1] + 2.0 * pin.engagement
    return x, length


def pin_footprint(
    seam, depth: float, y: float, pin, follow_step: bool
) -> tuple[float, float, float, float]:
    """The fin pair's plan rectangle ``(x0, x1, y0, y1)`` at site ``y``.

    The single source the build and the validation read, so a check and the
    solid can never disagree about where a pin is.
    """
    x, length = pin_placement(seam, depth, y, pin, follow_step)
    half = pin.pocket_width / 2.0
    return (x - length / 2.0, x + length / 2.0, y - half, y + half)


def add_pins(
    body,
    seam,
    pin,
    sites,
    substrate: float,
    upward: bool,
    chamfer: bool = True,
    follow_step: bool = False,
):
    """Union the Seam's pin fins into ``body``.

    Called on the whole part before it is split, so each Section keeps its
    half of every fin. A part with no configured sites comes back unchanged.
    ``chamfer=False`` keeps every fin rectangular (no base flare).

    ``follow_step=True`` makes a fin pair bridge the Seam's jog at its site
    (see :func:`pin_placement`); a site on a straight run keeps ``pin.length``
    and the Seam's own X.
    """
    depth = _seam_depth(seam, sites)
    for y in sites:
        x, length = pin_placement(seam, depth, y, pin, follow_step)
        body = cad_helpers.union(
            body,
            *fins(pin, x, y, substrate, upward, chamfer, length),
        )
    return body


def _seam_depth(seam, sites) -> float:
    """The Seam's Y extent, taken from its bands (their outer ends)."""
    bands = seam.bands
    return max(bands[-1][1] - bands[0][0], 1.0)


def site_on_straight_run(seam, depth: float, y: float, pin) -> bool:
    """True when the whole pocket sits inside one straight run of the Seam."""
    half = pin.pocket_width / 2.0
    for y0, y1, _ in seam.segments(depth):
        if y0 + half - 1e-9 <= y <= y1 - half + 1e-9:
            return True
    return False
