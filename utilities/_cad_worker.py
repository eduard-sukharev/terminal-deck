"""Out-of-process chamfer/fillet worker.

OCC can segfault (not raise) on some chamfers of complex solids, which would
take the whole build down. ``cad_helpers`` therefore runs each attempt here, in
a child process; a crash only costs that attempt. Kept free of project imports
so the spawned child starts fast.
"""

from __future__ import annotations


def treat(in_path: str, out_path: str, mode: str, keys: list, size: float) -> None:
    import build123d as b3d

    shape = b3d.import_brep(in_path)
    wanted = {tuple(k) for k in keys}
    edges = []
    for edge in shape.edges():
        p = edge.position_at(0.5)
        if (round(p.X, 3), round(p.Y, 3), round(p.Z, 3), round(edge.length, 3)) in wanted:
            edges.append(edge)
    if not edges:
        b3d.export_brep(shape, out_path)
        return
    result = b3d.chamfer(edges, size) if mode == "chamfer" else b3d.fillet(edges, size)
    if result is None or not result.is_valid:
        raise ValueError("invalid result")
    b3d.export_brep(result, out_path)
