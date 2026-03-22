#include "mcp_bridge/native_handlers.h"
#include "mcp_bridge/handler_helpers.h"
#include "mcp_bridge/bridge_gup.h"

using json = nlohmann::json;
using namespace HandlerHelpers;

// ── native:render_scene ─────────────────────────────────────────
std::string NativeHandlers::RenderScene(const std::string& params, MCPBridgeGUP* gup) {
    return gup->GetExecutor().ExecuteSync([&]() -> std::string {
        json p = params.empty() ? json::object() : json::parse(params, nullptr, false);

        int width = p.value("width", 1920);
        int height = p.value("height", 1080);
        std::string outputPath = p.value("output_path", "");

        // Build MAXScript render command — the SDK render API is complex
        // and MAXScript's render() function handles all the boilerplate
        std::string script = "render outputWidth:" + std::to_string(width) +
                             " outputHeight:" + std::to_string(height) +
                             " vfb:true";

        if (!outputPath.empty()) {
            script += " outputFile:\"" + JsonEscape(outputPath) + "\"";
        }

        RunMAXScript(script);

        json result;
        result["status"] = "rendered";
        result["width"] = width;
        result["height"] = height;
        if (!outputPath.empty()) result["outputFile"] = outputPath;
        return result.dump();
    }, 300000); // 5 minute timeout for rendering
}
