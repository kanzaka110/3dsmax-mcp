"""Layer 4 verification tools — post-action checks that stop the agent from lying."""

from ..server import mcp, client
from src.helpers.maxscript import safe_string


@mcp.tool()
def verify_scatter_output(name: str) -> str:
    """Verify a Forest Pack scatter object is correctly configured.

    Checks: object exists, has surfaces, has geometry sources, density is non-zero.
    Reports configuration summary and warnings for common misconfigurations.

    Args:
        name: Name of the Forest Pack object to verify.
    """
    safe = safe_string(name)
    maxscript = f"""(
        local esc = MCP_Server.escapeJsonString
        local objName = "{safe}"
        local obj = getNodeByName objName
        if obj == undefined then (
            "{{\\\"error\\\":\\\"Object not found\\\",\\\"name\\\":\\\"" + (esc objName) + "\\\"}}"
        ) else (
            local cn = (classOf obj) as string
            local isForest = false
            try (if (classOf obj) == Forest_Pro do isForest = true) catch ()

            if not isForest then (
                "{{\\\"error\\\":\\\"Not a Forest Pack object\\\",\\\"name\\\":\\\"" + (esc objName) + \
                "\\\",\\\"class\\\":\\\"" + (esc cn) + "\\\"}}"
            ) else (
                local surfCount = try (obj.surflist.count) catch 0
                local surfNames = ""
                try (
                    for i = 1 to obj.surflist.count do (
                        if i > 1 do surfNames += ","
                        if obj.surflist[i] != undefined then
                            surfNames += "\\\"" + (esc obj.surflist[i].name) + "\\\""
                        else
                            surfNames += "null"
                    )
                ) catch ()

                local geomCount = try (obj.cobjlist.count) catch 0
                local geomNames = ""
                try (
                    for i = 1 to obj.cobjlist.count do (
                        if i > 1 do geomNames += ","
                        if obj.cobjlist[i] != undefined then
                            geomNames += "\\\"" + (esc obj.cobjlist[i].name) + "\\\""
                        else
                            geomNames += "null"
                    )
                ) catch ()

                local density = try (obj.maxdensity) catch 0
                local seed = try (obj.seed) catch 0
                local direction = try (obj.direction) catch -1
                local scaleMin = try (obj.scalexmin) catch 100.0
                local scaleMax = try (obj.scalexmax) catch 100.0

                local warnings = ""
                local wc = 0
                if surfCount == 0 do (
                    if wc > 0 do warnings += ","
                    warnings += "\\\"No surfaces assigned\\\""
                    wc += 1
                )
                if geomCount == 0 do (
                    if wc > 0 do warnings += ","
                    warnings += "\\\"No geometry sources\\\""
                    wc += 1
                )
                if density == 0 do (
                    if wc > 0 do warnings += ","
                    warnings += "\\\"Density is zero\\\""
                    wc += 1
                )
                local nullGeoms = 0
                try (for g in obj.cobjlist where g == undefined do nullGeoms += 1) catch ()
                if nullGeoms > 0 do (
                    if wc > 0 do warnings += ","
                    warnings += "\\\"" + (nullGeoms as string) + " null geometry ref(s)\\\""
                    wc += 1
                )

                "{{\\\"valid\\\":true" + \
                ",\\\"name\\\":\\\"" + (esc obj.name) + "\\\"" + \
                ",\\\"surfaces\\\":[" + surfNames + "]" + \
                ",\\\"surfaceCount\\\":" + (surfCount as string) + \
                ",\\\"geometry\\\":[" + geomNames + "]" + \
                ",\\\"geometryCount\\\":" + (geomCount as string) + \
                ",\\\"density\\\":" + (density as string) + \
                ",\\\"seed\\\":" + (seed as string) + \
                ",\\\"direction\\\":" + (direction as string) + \
                ",\\\"scaleRange\\\":[" + (scaleMin as string) + "," + (scaleMax as string) + "]" + \
                ",\\\"warnings\\\":[" + warnings + "]" + \
                "}}"
            )
        )
    )"""
    response = client.send_command(maxscript)
    return response.get("result", '{"error":"No response"}')
