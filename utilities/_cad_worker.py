"""Out-of-process chamfer/fillet worker.

OCC can segfault (not raise) on some chamfers of complex solids, which would
take the whole build down. ``cad_helpers`` therefore runs each attempt here, in
a child process; a crash only costs that attempt. Kept free of project imports
so the spawned child starts fast.
"""

from __future__ import annotations


def _key(edge) -> tuple:
    p = edge.position_at(0.5)
    return (round(p.X, 3), round(p.Y, 3), round(p.Z, 3), round(edge.length, 3))


def treat(in_path: str, out_path: str, mode: str, keys: list, size: float) -> None:
    import build123d as b3d

    shape = b3d.import_brep(in_path)
    wanted = {tuple(k) for k in keys}
    edges = []
    for edge in shape.edges():
        if _key(edge) in wanted:
            edges.append(edge)
    if not edges:
        b3d.export_brep(shape, out_path)
        return
    result = b3d.chamfer(edges, size) if mode == "chamfer" else b3d.fillet(edges, size)
    if result is None or not result.is_valid:
        raise ValueError("invalid result")
    b3d.export_brep(result, out_path)


def treat_variable(in_path: str, out_path: str, items: list) -> None:
    """Fillet a network of edges, each with its own radius.

    ``items`` is ``[[key, size], ...]``. The edges may meet at vertices (a
    boss's vertical chord and its base ring do), so they are filleted in one
    ``BRepFilletAPI_MakeFillet`` pass: OCC builds the corner blend, which it
    cannot do when the same edges are treated one set after the other.
    """
    import build123d as b3d
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet

    shape = b3d.import_brep(in_path)
    wanted = {tuple(k): size for k, size in items}
    builder = BRepFilletAPI_MakeFillet(shape.wrapped)
    added = 0
    for edge in shape.edges():
        size = wanted.get(_key(edge))
        if size is not None:
            builder.Add(size, edge.wrapped)
            added += 1
    if not added:
        b3d.export_brep(shape, out_path)
        return
    builder.Build()
    if not builder.IsDone():
        raise ValueError("fillet not done")
    result = b3d.Part(builder.Shape())
    if result is None or not result.is_valid:
        raise ValueError("invalid result")
    b3d.export_brep(result, out_path)
