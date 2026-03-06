from ..server import mcp, client


@mcp.tool()
def set_view_mode(mode: str) -> str:
    """Switch RV's view mode.

    Args:
        mode: One of "sequence" (play sources in order),
              "stack" (layer sources for comparison),
              "layout" (tile sources side by side).
    """
    mode_map = {
        "sequence": "defaultSequence",
        "stack": "defaultStack",
        "layout": "defaultLayout",
    }
    view_node = mode_map.get(mode.lower())
    if not view_node:
        return f"Invalid mode '{mode}'. Use: sequence, stack, layout"
    return client.eval_mu(
        f'{{ require commands; setViewNode("{view_node}");'
        f' "view set to {mode}"; }}'
    )


@mcp.tool()
def set_composite_type(composite_type: str = "over") -> str:
    """Set the compositing mode when in stack view.

    Automatically switches to stack view if not already in it.

    Args:
        composite_type: One of "over", "add", "difference",
                        "-difference", "replace", "topmost".
    """
    valid = {"over", "add", "difference", "-difference", "replace", "topmost"}
    if composite_type not in valid:
        return f"Invalid type '{composite_type}'. Use: {', '.join(sorted(valid))}"
    return client.eval_mu(
        '{ require commands;'
        ' setViewNode("defaultStack");'
        f' setStringProperty("#RVStack.composite.type", string[] {{"{composite_type}"}}, true);'
        ' redraw();'
        f' "composite type set to {composite_type}";'
        ' }'
    )


@mcp.tool()
def toggle_wipe() -> str:
    """Toggle wipe mode on/off for A/B comparison in stack view.

    Automatically switches to stack view first.
    """
    return client.eval_mu(
        '{ require commands;'
        ' setViewNode("defaultStack");'
        ' sendInternalEvent("wipe-mode", "");'
        ' "wipe toggled";'
        ' }'
    )


@mcp.tool()
def get_view_info() -> str:
    """Get current view state as JSON.

    Returns: viewNode, viewType, and wipe state.
    """
    return client.eval_mu(
        r'{ require commands;'
        r' let vn = string(viewNode());'
        r' let vtype = "unknown";'
        r' if (vn == "defaultSequence") vtype = "sequence";'
        r' if (vn == "defaultStack") vtype = "stack";'
        r' if (vn == "defaultLayout") vtype = "layout";'
        r' "{\"viewNode\":\"" + vn + "\""'
        r' + ",\"viewType\":\"" + vtype + "\""'
        r' + "}";'
        r' }'
    )
