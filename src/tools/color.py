from ..server import mcp, client
from ..rv_client import escape_mu_string


@mcp.tool()
def set_lut(lut_file_path: str, target: str = "look") -> str:
    """Load a LUT file and activate it.

    Args:
        lut_file_path: Path to the LUT file (.3dl, .csp, .cube, etc.).
        target: Where to apply: "look" (color pipeline),
                "linearize" (input linearization),
                "display" (display transform).
    """
    target_map = {
        "look": "#RVColor",
        "linearize": "#RVLinearize",
        "display": "#RVDisplayColor",
    }
    node = target_map.get(target.lower())
    if not node:
        return f"Invalid target '{target}'. Use: look, linearize, display"
    safe = escape_mu_string(lut_file_path)
    return client.eval_mu(
        '{ require commands;'
        f' readLUT("{safe}", "{node}");'
        f' setIntProperty("{node}.lut.active", int[] {{1}}, true);'
        ' redraw();'
        f' "LUT loaded on {target}";'
        ' }'
    )


@mcp.tool()
def clear_lut(target: str = "look") -> str:
    """Deactivate the LUT on a target.

    Args:
        target: Which LUT to clear: "look", "linearize", or "display".
    """
    target_map = {
        "look": "#RVColor",
        "linearize": "#RVLinearize",
        "display": "#RVDisplayColor",
    }
    node = target_map.get(target.lower())
    if not node:
        return f"Invalid target '{target}'. Use: look, linearize, display"
    return client.eval_mu(
        '{ require commands;'
        f' setIntProperty("{node}.lut.active", int[] {{0}}, true);'
        ' redraw();'
        f' "LUT cleared on {target}";'
        ' }'
    )


@mcp.tool()
def set_cdl(
    slope: list[float] | None = None,
    offset: list[float] | None = None,
    power: list[float] | None = None,
    saturation: float | None = None,
) -> str:
    """Set CDL (Color Decision List) values.

    All parameters are optional — only provided values are changed.

    Args:
        slope: RGB slope values [r, g, b].
        offset: RGB offset values [r, g, b].
        power: RGB power values [r, g, b].
        saturation: Global saturation value.
    """
    parts = ['{ require commands;']
    parts.append(' setIntProperty("#RVColor.CDL.active", int[] {1}, true);')
    if slope and len(slope) == 3:
        parts.append(
            f' setFloatProperty("#RVColor.CDL.slope",'
            f' float[] {{{slope[0]}, {slope[1]}, {slope[2]}}}, true);'
        )
    if offset and len(offset) == 3:
        parts.append(
            f' setFloatProperty("#RVColor.CDL.offset",'
            f' float[] {{{offset[0]}, {offset[1]}, {offset[2]}}}, true);'
        )
    if power and len(power) == 3:
        parts.append(
            f' setFloatProperty("#RVColor.CDL.power",'
            f' float[] {{{power[0]}, {power[1]}, {power[2]}}}, true);'
        )
    if saturation is not None:
        parts.append(
            f' setFloatProperty("#RVColor.CDL.saturation",'
            f' float[] {{{saturation}}}, true);'
        )
    parts.append(' redraw(); "CDL set"; }')
    return client.eval_mu("".join(parts))


@mcp.tool()
def clear_cdl() -> str:
    """Deactivate CDL color correction."""
    return client.eval_mu(
        '{ require commands;'
        ' setIntProperty("#RVColor.CDL.active", int[] {0}, true);'
        ' redraw();'
        ' "CDL cleared";'
        ' }'
    )


@mcp.tool()
def set_exposure(value: float, channel: str = "all") -> str:
    """Set exposure adjustment.

    Args:
        value: Exposure value (0.0 = no change).
        channel: "all" for uniform, or "r", "g", "b" for per-channel.
    """
    if channel == "all":
        vals = f"{value}, {value}, {value}"
    elif channel in ("r", "g", "b"):
        defaults = {"r": 0.0, "g": 0.0, "b": 0.0}
        defaults[channel] = value
        vals = f"{defaults['r']}, {defaults['g']}, {defaults['b']}"
    else:
        return f"Invalid channel '{channel}'. Use: all, r, g, b"
    return client.eval_mu(
        '{ require commands;'
        ' setIntProperty("#RVColor.color.active", int[] {1}, true);'
        f' setFloatProperty("#RVColor.color.exposure", float[] {{{vals}}}, true);'
        ' redraw();'
        f' "exposure set to {value} ({channel})";'
        ' }'
    )


@mcp.tool()
def set_gamma(value: float) -> str:
    """Set gamma correction.

    Args:
        value: Gamma value (1.0 = no change).
    """
    return client.eval_mu(
        '{ require commands;'
        ' setIntProperty("#RVColor.color.active", int[] {1}, true);'
        f' setFloatProperty("#RVColor.color.gamma", float[] {{{value}, {value}, {value}}}, true);'
        ' redraw();'
        f' "gamma set to {value}";'
        ' }'
    )


@mcp.tool()
def set_saturation(value: float) -> str:
    """Set saturation.

    Args:
        value: Saturation value (1.0 = normal, 0.0 = desaturated).
    """
    return client.eval_mu(
        '{ require commands;'
        ' setIntProperty("#RVColor.color.active", int[] {1}, true);'
        f' setFloatProperty("#RVColor.color.saturation", float[] {{{value}}}, true);'
        ' redraw();'
        f' "saturation set to {value}";'
        ' }'
    )


@mcp.tool()
def get_color_settings() -> str:
    """Get current color correction settings as JSON.

    Requires at least one source loaded in the session.
    """
    sources = client.eval_mu(
        r'{ require commands; string(nodesOfType("RVSourceGroup").size()); }'
    )
    if sources == "0":
        return '{"error":"no sources loaded"}'
    return client.eval_mu(
        r'{ require commands;'
        r' let cdlActive = getIntProperty("#RVColor.CDL.active").front();'
        r' let colorActive = getIntProperty("#RVColor.color.active").front();'
        r' let lutActive = getIntProperty("#RVColor.lut.active").front();'
        r' "{\"cdlActive\":" + string(cdlActive)'
        r' + ",\"colorActive\":" + string(colorActive)'
        r' + ",\"lutActive\":" + string(lutActive)'
        r' + "}";'
        r' }'
    )


@mcp.tool()
def set_display_gamma(gamma: float) -> str:
    """Set display gamma.

    Args:
        gamma: Display gamma value (e.g. 2.2 for sRGB-like).
    """
    return client.eval_mu(
        '{ require commands;'
        ' setIntProperty("#RVDisplayColor.color.active", int[] {1}, true);'
        f' setFloatProperty("#RVDisplayColor.color.gamma", float[] {{{gamma}, {gamma}, {gamma}}}, true);'
        ' redraw();'
        f' "display gamma set to {gamma}";'
        ' }'
    )


@mcp.tool()
def set_display_srgb(enabled: bool = True) -> str:
    """Enable or disable sRGB display transform.

    Args:
        enabled: True to enable sRGB, False to disable.
    """
    val = 1 if enabled else 0
    state = "enabled" if enabled else "disabled"
    return client.eval_mu(
        '{ require commands;'
        f' setIntProperty("#RVDisplayColor.color.sRGB", int[] {{{val}}}, true);'
        ' redraw();'
        f' "sRGB display {state}";'
        ' }'
    )


@mcp.tool()
def set_background(method: str = "black") -> str:
    """Set the viewport background.

    Args:
        method: One of "black", "checker", "grey18", "grey50", "crosshatch".
    """
    valid = {"black", "checker", "grey18", "grey50", "crosshatch"}
    if method not in valid:
        return f"Invalid method '{method}'. Use: {', '.join(sorted(valid))}"
    return client.eval_mu(
        f'{{ require commands; setBGMethod("{method}"); redraw();'
        f' "background set to {method}"; }}'
    )
