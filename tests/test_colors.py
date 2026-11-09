"""glTF color palette: every component must be tellable apart in a viewer."""

from main import BuildPipeline
from utilities.colors import COMPONENT_COLORS, DEFAULT_COLOR, color_for


def _roles() -> list[str]:
    pipeline = BuildPipeline(layout_name="slider")
    pipeline.load_config()
    return list(pipeline.load_components())


def test_every_component_has_its_own_color():
    roles = _roles()
    missing = [r for r in roles if r not in COMPONENT_COLORS]
    assert not missing, f"no glTF color for components: {missing}"
    colors = [color_for(r)[:3] for r in roles]
    assert len(set(colors)) == len(colors), "two components share one color"
    assert all(color_for(r)[:3] != DEFAULT_COLOR[:3] for r in roles)


def test_case_shell_is_translucent_and_components_are_opaque():
    assert color_for("case")[3] < 1.0
    for role in _roles():
        assert color_for(role)[3] == 1.0, f"{role} should be opaque"
