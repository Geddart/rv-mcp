from ..server import mcp, client


@mcp.tool()
def execute_mu(code: str) -> str:
    """Execute arbitrary Mu code in RV and return the result.

    The code is evaluated via remote-eval. Use 'require commands;'
    at the start if you need commands functions like play(), stop(), etc.

    Examples:
        execute_mu("{ require commands; string(frame()); }")
        execute_mu("{ require commands; play(); \\"playing\\"; }")
        execute_mu("{ require commands; sources(); }")
    """
    return client.eval_mu(code)
