import json
import os

from ..server import mcp, client
from ..rv_client import escape_mu_string


def _load_ocio_config(config_path: str | None = None):
    """Load an OCIO config from path or $OCIO env var."""
    import PyOpenColorIO as OCIO

    if config_path:
        return OCIO.Config.CreateFromFile(config_path.replace("\\", "/"))
    return OCIO.GetCurrentConfig()


def _get_scene_linear_role() -> str:
    """Get the scene-linear color space name from the active OCIO config."""
    import PyOpenColorIO as OCIO

    config = OCIO.GetCurrentConfig()
    cs = config.getColorSpace(OCIO.ROLE_SCENE_LINEAR)
    return cs.getName() if cs else "ACEScg"


def _find_ocio_node_in_pipeline(pipeline: str, ocio_type: str) -> str:
    """Find an existing OCIO node in a pipeline group. Returns node name or empty string."""
    return client.eval_mu(
        '{ require commands;'
        f' let _members = nodesInGroup("{pipeline}");'
        f' let _found = "";'
        f' for_each (_m; _members) if (nodeType(_m) == "{ocio_type}") _found = _m;'
        ' _found;'
        ' }'
    )


def _ensure_ocio_in_pipeline(pipeline: str, ocio_type: str, extra_types: str = "") -> str:
    """Ensure an OCIO node type exists in a pipeline. Returns the OCIO node name.

    If the pipeline doesn't already contain the OCIO type, sets pipeline.nodes
    to include it (RV auto-creates the node). Then finds and returns the node.
    """
    existing = _find_ocio_node_in_pipeline(pipeline, ocio_type)
    if existing:
        return existing

    # Set pipeline.nodes — RV auto-creates nodes of these types
    if extra_types:
        types_mu = f'string[] {{"{ocio_type}", "{extra_types}"}}'
    else:
        types_mu = f'string[] {{"{ocio_type}"}}'

    client.eval_mu(
        '{ require commands;'
        f' setStringProperty("{pipeline}.pipeline.nodes", {types_mu}, true);'
        ' }'
    )

    # Find the auto-created node
    return _find_ocio_node_in_pipeline(pipeline, ocio_type)


@mcp.tool()
def get_ocio_config(config_path: str | None = None) -> str:
    """Get OCIO config information as JSON.

    Returns color spaces, displays, views, and looks from the active
    OCIO config (or a specific config file).

    Args:
        config_path: Optional path to an OCIO config file.
                     If omitted, uses the $OCIO environment variable.
    """
    try:
        config = _load_ocio_config(config_path)
    except Exception as e:
        return json.dumps({"error": str(e)})

    displays = {}
    for display in config.getDisplays():
        displays[display] = list(config.getViews(display))

    colorspaces = [cs.getName() for cs in config.getColorSpaces()]
    looks = [look.getName() for look in config.getLooks()]

    roles = {}
    for role_name, cs_name in config.getRoles():
        roles[role_name] = cs_name

    return json.dumps({
        "description": config.getDescription(),
        "version": f"{config.getMajorVersion()}.{config.getMinorVersion()}",
        "colorSpaces": colorspaces,
        "displays": displays,
        "looks": looks,
        "roles": roles,
        "configPath": os.environ.get("OCIO", ""),
    })


@mcp.tool()
def set_ocio_colorspace(colorspace: str, source_node: str | None = None) -> str:
    """Set the OCIO input color space for a source.

    Inserts an OCIOFile node into the source's linearize pipeline,
    converting from the specified color space to scene-linear.

    Args:
        colorspace: Input color space name (e.g. "sRGB - Texture", "ACEScg").
        source_node: Source group name (e.g. "sourceGroup000000").
                     If omitted, uses the first source.
    """
    scene_linear = _get_scene_linear_role()
    safe_cs = escape_mu_string(colorspace)
    safe_out = escape_mu_string(scene_linear)

    if source_node:
        src = escape_mu_string(source_node)
    else:
        src = client.eval_mu(
            '{ require commands; let _srcs = nodesOfType("RVSourceGroup");'
            ' if (_srcs.size() > 0) _srcs[0] else ""; }'
        )
        if not src:
            return json.dumps({"error": "no sources loaded"})

    pipeline = f"{src}_tolinPipeline"
    node = _ensure_ocio_in_pipeline(pipeline, "OCIOFile", "RVLensWarp")

    if not node:
        return json.dumps({"error": "failed to create OCIOFile node"})

    return client.eval_mu(
        '{ require commands;'
        f' setStringProperty("{node}.ocio.function", string[] {{"color"}}, true);'
        f' setStringProperty("{node}.ocio.inColorSpace", string[] {{"{safe_cs}"}}, true);'
        f' setStringProperty("{node}.ocio_color.outColorSpace", string[] {{"{safe_out}"}}, true);'
        f' setIntProperty("{node}.ocio.active", int[] {{1}}, true);'
        f' ocioUpdateConfig("{node}");'
        ' redraw();'
        f' "OCIO colorspace {safe_cs} -> {safe_out} on {src}";'
        ' }'
    )


@mcp.tool()
def set_ocio_display(display: str, view: str) -> str:
    """Set the OCIO display transform.

    Inserts an OCIODisplay node into the display pipeline.

    Args:
        display: Display name (e.g. "sRGB - Display").
        view: View name (e.g. "ACES 1.0 - SDR Video").
    """
    safe_display = escape_mu_string(display)
    safe_view = escape_mu_string(view)
    scene_linear = _get_scene_linear_role()
    safe_linear = escape_mu_string(scene_linear)

    pipeline = "displayGroup0_colorPipeline"
    node = _ensure_ocio_in_pipeline(pipeline, "OCIODisplay")

    if not node:
        return json.dumps({"error": "failed to create OCIODisplay node"})

    return client.eval_mu(
        '{ require commands;'
        f' setStringProperty("{node}.ocio.function", string[] {{"display"}}, true);'
        f' setStringProperty("{node}.ocio_display.display", string[] {{"{safe_display}"}}, true);'
        f' setStringProperty("{node}.ocio_display.view", string[] {{"{safe_view}"}}, true);'
        f' setStringProperty("{node}.ocio.inColorSpace", string[] {{"{safe_linear}"}}, true);'
        f' setIntProperty("{node}.ocio.active", int[] {{1}}, true);'
        f' ocioUpdateConfig("{node}");'
        ' redraw();'
        f' "OCIO display {safe_display}/{safe_view} activated";'
        ' }'
    )


@mcp.tool()
def set_ocio_look(look: str, direction: str = "forward", source_node: str | None = None) -> str:
    """Apply an OCIO look to a source.

    Inserts an OCIOLook node into the source's look pipeline.

    Args:
        look: Look name from the OCIO config.
        direction: "forward" or "inverse".
        source_node: Source group name. If omitted, uses the first source.
    """
    safe_look = escape_mu_string(look)
    dir_val = 0 if direction == "forward" else 1
    scene_linear = _get_scene_linear_role()
    safe_linear = escape_mu_string(scene_linear)

    if source_node:
        src = escape_mu_string(source_node)
    else:
        src = client.eval_mu(
            '{ require commands; let _srcs = nodesOfType("RVSourceGroup");'
            ' if (_srcs.size() > 0) _srcs[0] else ""; }'
        )
        if not src:
            return json.dumps({"error": "no sources loaded"})

    pipeline = f"{src}_lookPipeline"
    node = _ensure_ocio_in_pipeline(pipeline, "OCIOLook")

    if not node:
        return json.dumps({"error": "failed to create OCIOLook node"})

    return client.eval_mu(
        '{ require commands;'
        f' setStringProperty("{node}.ocio.function", string[] {{"look"}}, true);'
        f' setStringProperty("{node}.ocio_look.look", string[] {{"{safe_look}"}}, true);'
        f' setIntProperty("{node}.ocio_look.direction", int[] {{{dir_val}}}, true);'
        f' setStringProperty("{node}.ocio.inColorSpace", string[] {{"{safe_linear}"}}, true);'
        f' setIntProperty("{node}.ocio.active", int[] {{1}}, true);'
        f' ocioUpdateConfig("{node}");'
        ' redraw();'
        f' "OCIO look {safe_look} applied to {src}";'
        ' }'
    )


@mcp.tool()
def get_ocio_state() -> str:
    """Get current OCIO state for all sources and display as JSON.

    Returns which sources have OCIO nodes and their settings.
    """
    return client.eval_mu(
        r'{ require commands;'
        r' let _oFiles = nodesOfType("OCIOFile");'
        r' let _oDisps = nodesOfType("OCIODisplay");'
        r' let _oLooks = nodesOfType("OCIOLook");'
        r' let _r = "{\"sources\":[";'
        r' for_index (_i; _oFiles) {'
        r'     if (_i > 0) _r += ",";'
        r'     let _n = _oFiles[_i];'
        r'     let _inCS = getStringProperty(_n + ".ocio.inColorSpace").front();'
        r'     let _outCS = getStringProperty(_n + ".ocio_color.outColorSpace").front();'
        r'     let _act = getIntProperty(_n + ".ocio.active").front();'
        r'     _r += "{\"node\":\"" + _n + "\""'
        r'         + ",\"inColorSpace\":\"" + _inCS + "\""'
        r'         + ",\"outColorSpace\":\"" + _outCS + "\""'
        r'         + ",\"active\":" + string(_act) + "}";'
        r' }'
        r' _r += "],\"display\":[";'
        r' for_index (_j; _oDisps) {'
        r'     if (_j > 0) _r += ",";'
        r'     let _dn = _oDisps[_j];'
        r'     let _disp = getStringProperty(_dn + ".ocio_display.display").front();'
        r'     let _view = getStringProperty(_dn + ".ocio_display.view").front();'
        r'     let _dAct = getIntProperty(_dn + ".ocio.active").front();'
        r'     _r += "{\"node\":\"" + _dn + "\""'
        r'         + ",\"display\":\"" + _disp + "\""'
        r'         + ",\"view\":\"" + _view + "\""'
        r'         + ",\"active\":" + string(_dAct) + "}";'
        r' }'
        r' _r += "],\"looks\":[";'
        r' for_index (_k; _oLooks) {'
        r'     if (_k > 0) _r += ",";'
        r'     let _ln = _oLooks[_k];'
        r'     let _look = getStringProperty(_ln + ".ocio_look.look").front();'
        r'     let _lAct = getIntProperty(_ln + ".ocio.active").front();'
        r'     _r += "{\"node\":\"" + _ln + "\""'
        r'         + ",\"look\":\"" + _look + "\""'
        r'         + ",\"active\":" + string(_lAct) + "}";'
        r' }'
        r' _r += "]}";'
        r' _r;'
        r' }'
    )


@mcp.tool()
def clear_ocio(target: str = "all") -> str:
    """Remove OCIO nodes and restore default RV pipeline.

    Args:
        target: What to clear — "linearize", "display", "look", or "all".
    """
    valid = {"linearize", "display", "look", "all"}
    if target not in valid:
        return json.dumps({"error": f"Invalid target '{target}'. Use: {', '.join(sorted(valid))}"})

    parts = ["{ require commands;"]
    cleared = []

    if target in ("linearize", "all"):
        # Find all linearize pipelines that have OCIOFile and reset them
        parts.append(
            ' let _cFiles = nodesOfType("OCIOFile");'
            ' for_each (_cf; _cFiles) {'
            '     let _cfg = nodeGroup(_cf);'
            '     setStringProperty(_cfg + ".pipeline.nodes",'
            '         string[] {"RVLinearize", "RVLensWarp"}, true);'
            ' }'
        )
        cleared.append("linearize")

    if target in ("display", "all"):
        parts.append(
            ' let _cDisps = nodesOfType("OCIODisplay");'
            ' for_each (_cd; _cDisps) {'
            '     let _cdg = nodeGroup(_cd);'
            '     setStringProperty(_cdg + ".pipeline.nodes",'
            '         string[] {"RVDisplayColor"}, true);'
            ' }'
        )
        cleared.append("display")

    if target in ("look", "all"):
        parts.append(
            ' let _cLooks = nodesOfType("OCIOLook");'
            ' for_each (_cl; _cLooks) {'
            '     let _clg = nodeGroup(_cl);'
            '     setStringProperty(_clg + ".pipeline.nodes",'
            '         string[] {"RVLookLUT"}, true);'
            ' }'
        )
        cleared.append("look")

    parts.append(f' redraw(); "OCIO cleared: {", ".join(cleared)}"; }}')
    return client.eval_mu("".join(parts))
