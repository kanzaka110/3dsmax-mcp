from ..server import mcp, client


@mcp.tool()
def execute_maxscript(code: str = "", command: str = "") -> str:
    """Execute arbitrary MAXScript code in 3ds Max. Not a shell.

    Args:
        code: MAXScript code to execute.
        command: Alias for code.
    """
    script = code or command
    if not script:
        return "Error: provide MAXScript code in the 'code' parameter"
    response = client.send_command(script, cmd_type="maxscript")
    return response.get("result", "")
