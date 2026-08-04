"""Tests for cable routing."""

from routing.cable_routing import CableRouter, CableRoute, MIN_BEND_RADIUS_MM
from utilities.constants import CONNECTOR_HDMI, CONNECTOR_USB_C


def test_min_bend_radii():
    assert CONNECTOR_HDMI in MIN_BEND_RADIUS_MM
    assert CONNECTOR_USB_C in MIN_BEND_RADIUS_MM


def test_route_length():
    route = CableRoute(CONNECTOR_HDMI, (0, 0, 0), (30, 0, 0), 30.0)
    assert route.length == 30.0


def test_bend_pass():
    route = CableRoute(CONNECTOR_HDMI, (0, 0, 0), (30, 0, 0), 30.0)
    assert route.passes_bend()


def test_bend_fail():
    route = CableRoute(CONNECTOR_HDMI, (0, 0, 0), (30, 0, 0), 10.0)
    assert not route.passes_bend()


def test_router_track():
    router = CableRouter()
    route = router.track(CONNECTOR_USB_C, (0, 0, 0), (50, 0, 0))
    assert len(router.routes) == 1
    assert route.cable_type == CONNECTOR_USB_C


def test_tunnel_diameter():
    router = CableRouter(clearance=2.0)
    router.track(CONNECTOR_HDMI, (0, 0, 0), (50, 0, 0))
    # HDMI cable diameter 5.0 + 2*clearance
    assert router.tunnel_diameter() == 9.0


def test_failing_routes():
    router = CableRouter()
    router.track(CONNECTOR_HDMI, (0, 0, 0), (50, 0, 0), bend_radius=5.0)
    assert len(router.failing_routes()) == 1
