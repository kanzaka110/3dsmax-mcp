from ..server import mcp, client
from ..safety import wrap_with_safety


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
    return wrap_with_safety("execute_maxscript", response.get("result", ""))
