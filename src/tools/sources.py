from ..server import mcp, client
from ..rv_client import escape_mu_string


@mcp.tool()
def get_sources() -> str:
    """List all sources currently loaded in RV as JSON.

    Returns a JSON array with source node names.
    """
    return client.eval_mu(
        r'{ require commands;'
        r' let srcs = nodesOfType("RVSourceGroup");'
        r' let result = "[";'
        r' for_index (i; srcs) {'
        r'     if (i > 0) result += ",";'
        r'     result += "\"" + srcs[i] + "\"";'
        r' }'
        r' result += "]";'
        r' result;'
        r' }'
    )


@mcp.tool()
def get_source_media_info(source_node: str) -> str:
    """Get detailed media info for a source node.

    Args:
        source_node: The source node name (e.g. "sourceGroup000000").
    """
    safe = escape_mu_string(source_node)
    return client.eval_mu(
        r'{ require commands;'
        f' let media = getStringProperty("{safe}.media.movie");'
        r' let m = media[0];'
        f' let info = sourceMediaInfo("{safe}", m);'
        r' "{\"media\":\"" + m + "\""'
        r' + ",\"width\":" + string(info.width)'
        r' + ",\"height\":" + string(info.height)'
        r' + ",\"startFrame\":" + string(info.startFrame)'
        r' + ",\"endFrame\":" + string(info.endFrame)'
        r' + ",\"fps\":" + string(info.fps)'
        r' + ",\"bitsPerChannel\":" + string(info.bitsPerChannel)'
        r' + ",\"channels\":" + string(info.channels)'
        r' + ",\"isFloat\":" + (if info.isFloat then "true" else "false")'
        r' + "}";'
        r' }'
    )


@mcp.tool()
def get_sources_at_frame(frame: int = -1) -> str:
    """Get source nodes visible at a specific frame.

    Args:
        frame: Frame number to query (-1 for current frame).
    """
    frame_expr = "frame()" if frame == -1 else str(frame)
    return client.eval_mu(
        r'{ require commands;'
        f' let srcs = sourcesAtFrame({frame_expr});'
        r' let result = "[";'
        r' for_index (i; srcs) {'
        r'     if (i > 0) result += ",";'
        r'     result += "\"" + srcs[i] + "\"";'
        r' }'
        r' result += "]";'
        r' result;'
        r' }'
    )


@mcp.tool()
def new_session() -> str:
    """Create a new empty session, clearing all current sources."""
    return client.eval_mu(
        '{ require commands; newSession(); "new session created"; }'
    )


@mcp.tool()
def clear_session() -> str:
    """Clear all sources from the current session."""
    return client.eval_mu(
        '{ require commands; clearSession(); "session cleared"; }'
    )


@mcp.tool()
def save_session(file_path: str) -> str:
    """Save the current session to an .rv file.

    Args:
        file_path: Path for the .rv session file.
    """
    safe = escape_mu_string(file_path)
    return client.eval_mu(
        f'{{ require commands; saveSession("{safe}"); "session saved"; }}'
    )


@mcp.tool()
def get_session_info() -> str:
    """Get current session information as JSON.

    Returns: viewNode, frame, frameStart, frameEnd, sourceCount.
    """
    return client.eval_mu(
        r'{ require commands;'
        r' let srcs = nodesOfType("RVSourceGroup");'
        r' "{\"viewNode\":\"" + string(viewNode()) + "\""'
        r' + ",\"frame\":" + string(frame())'
        r' + ",\"frameStart\":" + string(frameStart())'
        r' + ",\"frameEnd\":" + string(frameEnd())'
        r' + ",\"sourceCount\":" + string(srcs.size())'
        r' + "}";'
        r' }'
    )
