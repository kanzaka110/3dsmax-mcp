#include "mcp_bridge/native_handlers.h"
#include "mcp_bridge/handler_helpers.h"
#include "mcp_bridge/bridge_gup.h"

#include <triobj.h>
#include <objbase.h>
#include <propidl.h>
#include <propkey.h>
#include <future>
#include <set>

using json = nlohmann::json;
using namespace HandlerHelpers;

// ── OLE Structured Storage metadata reader ──────────────────
// .max files are OLE compound documents. We can read file properties
// (title, author, comments, dates) without loading the scene.
static json ReadOLEMetadata(const std::wstring& filePath) {
    json meta;

    // Get file size
    WIN32_FILE_ATTRIBUTE_DATA fad;
    if (GetFileAttributesExW(filePath.c_str(), GetFileExInfoStandard, &fad)) {
        ULARGE_INTEGER sz;
        sz.HighPart = fad.nFileSizeHigh;
        sz.LowPart = fad.nFileSizeLow;
        meta["fileSizeBytes"] = sz.QuadPart;
        double mb = sz.QuadPart / (1024.0 * 1024.0);
        char buf[32];
        snprintf(buf, sizeof(buf), "%.1f MB", mb);
        meta["fileSize"] = buf;

        // File dates
        SYSTEMTIME st;
        FileTimeToSystemTime(&fad.ftCreationTime, &st);
        char dateBuf[64];
        snprintf(dateBuf, sizeof(dateBuf), "%04d-%02d-%02d %02d:%02d:%02d",
                 st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
        meta["created"] = dateBuf;

        FileTimeToSystemTime(&fad.ftLastWriteTime, &st);
        snprintf(dateBuf, sizeof(dateBuf), "%04d-%02d-%02d %02d:%02d:%02d",
                 st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
        meta["modified"] = dateBuf;
    }

    // Open as OLE structured storage
    IStorage* pStorage = nullptr;
    HRESULT hr = StgOpenStorage(filePath.c_str(), nullptr,
                                STGM_READ | STGM_SHARE_DENY_WRITE,
                                nullptr, 0, &pStorage);
    if (FAILED(hr) || !pStorage) {
        meta["oleError"] = "Could not open as structured storage";
        return meta;
    }

    // Read summary info properties
    IPropertySetStorage* pPropSetStg = nullptr;
    hr = pStorage->QueryInterface(IID_IPropertySetStorage, (void**)&pPropSetStg);
    if (SUCCEEDED(hr) && pPropSetStg) {
        IPropertyStorage* pPropStg = nullptr;
        hr = pPropSetStg->Open(FMTID_SummaryInformation, STGM_READ | STGM_SHARE_EXCLUSIVE, &pPropStg);
        if (SUCCEEDED(hr) && pPropStg) {
            // Read title, subject, author, comments
            PROPSPEC propSpec[4];
            PROPVARIANT propVar[4];
            for (int i = 0; i < 4; i++) {
                propSpec[i].ulKind = PRSPEC_PROPID;
                PropVariantInit(&propVar[i]);
            }
            propSpec[0].propid = PIDSI_TITLE;
            propSpec[1].propid = PIDSI_SUBJECT;
            propSpec[2].propid = PIDSI_AUTHOR;
            propSpec[3].propid = PIDSI_COMMENTS;

            hr = pPropStg->ReadMultiple(4, propSpec, propVar);
            if (SUCCEEDED(hr)) {
                auto readStr = [](const PROPVARIANT& pv) -> std::string {
                    if (pv.vt == VT_LPSTR && pv.pszVal) return pv.pszVal;
                    if (pv.vt == VT_LPWSTR && pv.pwszVal) return WideToUtf8(pv.pwszVal);
                    return "";
                };
                std::string title = readStr(propVar[0]);
                std::string subject = readStr(propVar[1]);
                std::string author = readStr(propVar[2]);
                std::string comments = readStr(propVar[3]);
                if (!title.empty()) meta["title"] = title;
                if (!subject.empty()) meta["subject"] = subject;
                if (!author.empty()) meta["author"] = author;
                if (!comments.empty()) meta["comments"] = comments;
            }
            for (int i = 0; i < 4; i++) PropVariantClear(&propVar[i]);
            pPropStg->Release();
        }

        // Read doc summary (custom properties like "Object Count")
        pPropStg = nullptr;
        hr = pPropSetStg->Open(FMTID_DocSummaryInformation, STGM_READ | STGM_SHARE_EXCLUSIVE, &pPropStg);
        if (SUCCEEDED(hr) && pPropStg) {
            // Enumerate all properties
            IEnumSTATPROPSTG* pEnum = nullptr;
            hr = pPropStg->Enum(&pEnum);
            if (SUCCEEDED(hr) && pEnum) {
                STATPROPSTG stat;
                while (pEnum->Next(1, &stat, nullptr) == S_OK) {
                    if (stat.lpwstrName) {
                        PROPSPEC ps;
                        ps.ulKind = PRSPEC_LPWSTR;
                        ps.lpwstr = stat.lpwstrName;
                        PROPVARIANT pv;
                        PropVariantInit(&pv);
                        if (SUCCEEDED(pPropStg->ReadMultiple(1, &ps, &pv))) {
                            std::string key = WideToUtf8(stat.lpwstrName);
                            if (pv.vt == VT_LPSTR && pv.pszVal)
                                meta["docProperties"][key] = std::string(pv.pszVal);
                            else if (pv.vt == VT_LPWSTR && pv.pwszVal)
                                meta["docProperties"][key] = WideToUtf8(pv.pwszVal);
                            else if (pv.vt == VT_I4)
                                meta["docProperties"][key] = pv.lVal;
                            else if (pv.vt == VT_R8)
                                meta["docProperties"][key] = pv.dblVal;
                            PropVariantClear(&pv);
                        }
                        CoTaskMemFree(stat.lpwstrName);
                    }
                }
                pEnum->Release();
            }
            pPropStg->Release();
        }
        pPropSetStg->Release();
    }

    pStorage->Release();
    return meta;
}

// ── native:inspect_max_file ─────────────────────────────────
std::string NativeHandlers::InspectMaxFile(const std::string& params, MCPBridgeGUP* gup) {
    json p = json::parse(params, nullptr, false);
    std::string filePath = p.value("file_path", "");
    bool listObjects = p.value("list_objects", false);

    if (filePath.empty()) throw std::runtime_error("file_path is required");

    std::wstring wpath = Utf8ToWide(filePath);

    // Check file exists
    DWORD attrib = GetFileAttributesW(wpath.c_str());
    if (attrib == INVALID_FILE_ATTRIBUTES) {
        throw std::runtime_error("File not found: " + filePath);
    }

    // Step 1: Read OLE metadata (no main thread needed)
    json meta = ReadOLEMetadata(wpath);

    // Step 2: Optionally list objects using MERGE_LIST_NAMES
    if (listObjects) {
        return gup->GetExecutor().ExecuteSync([&]() -> std::string {
            Interface* ip = GetCOREInterface();

            NameTab nameList;
            int result = ip->MergeFromFile(wpath.c_str(),
                TRUE,           // mergeAll = TRUE (required for MERGE_LIST_NAMES)
                FALSE,          // selMerged
                FALSE,          // refresh
                MERGE_LIST_NAMES, // dupAction = list names only
                &nameList);

            json objects = json::array();
            for (int i = 0; i < nameList.Count(); i++) {
                if (nameList[i]) {
                    objects.push_back(WideToUtf8(nameList[i]));
                }
            }

            json fileInfo;
            fileInfo["filePath"] = filePath;
            fileInfo["metadata"] = meta;
            fileInfo["objectCount"] = objects.size();
            fileInfo["objects"] = objects;
            return fileInfo.dump();
        });
    }

    // Quick mode — just metadata
    json fileInfo;
    fileInfo["filePath"] = filePath;
    fileInfo["metadata"] = meta;
    return fileInfo.dump();
}

// ── native:merge_from_file ──────────────────────────────────
std::string NativeHandlers::MergeFromFile(const std::string& params, MCPBridgeGUP* gup) {
    return gup->GetExecutor().ExecuteSync([&params]() -> std::string {
        json p = json::parse(params, nullptr, false);
        std::string filePath = p.value("file_path", "");
        auto objectNames = p.value("object_names", std::vector<std::string>{});
        bool selectMerged = p.value("select_merged", true);
        std::string dupAction = p.value("duplicate_action", "rename");

        if (filePath.empty()) throw std::runtime_error("file_path is required");

        std::wstring wpath = Utf8ToWide(filePath);
        Interface* ip = GetCOREInterface();

        // Determine dup action
        int dupFlag = MERGE_DUPS_RENAME;
        if (dupAction == "skip") dupFlag = MERGE_DUPS_SKIP;
        else if (dupAction == "merge") dupFlag = MERGE_DUPS_MERGE;
        else if (dupAction == "delete_old") dupFlag = MERGE_DUPS_DELOLD;

        // Capture existing node names for diffing
        INode* root = ip->GetRootNode();
        std::vector<INode*> existingNodes;
        CollectNodes(root, existingNodes);
        std::set<std::string> existingNames;
        for (INode* n : existingNodes) {
            existingNames.insert(WideToUtf8(n->GetName()));
        }

        int result;
        if (objectNames.empty()) {
            // Merge all
            result = ip->MergeFromFile(wpath.c_str(),
                TRUE,           // mergeAll
                selectMerged ? TRUE : FALSE,
                TRUE,           // refresh
                dupFlag);
        } else {
            // Selective merge — build NameTab
            NameTab mrgList;
            for (const auto& name : objectNames) {
                std::wstring wname = Utf8ToWide(name);
                mrgList.AddName(wname.c_str());
            }
            result = ip->MergeFromFile(wpath.c_str(),
                TRUE,           // mergeAll must be TRUE when mrgList provided
                selectMerged ? TRUE : FALSE,
                TRUE,           // refresh
                dupFlag,
                &mrgList);
        }

        if (!result) {
            throw std::runtime_error("MergeFromFile failed for: " + filePath);
        }

        // Diff to find newly merged nodes
        std::vector<INode*> afterNodes;
        CollectNodes(ip->GetRootNode(), afterNodes);
        json mergedNames = json::array();
        for (INode* n : afterNodes) {
            std::string nm = WideToUtf8(n->GetName());
            if (existingNames.find(nm) == existingNames.end()) {
                mergedNames.push_back(nm);
            }
        }

        ip->RedrawViews(ip->GetTime());

        json res;
        res["filePath"] = filePath;
        res["mergedCount"] = mergedNames.size();
        res["merged"] = mergedNames;
        res["message"] = "Merged " + std::to_string(mergedNames.size()) + " objects from " + filePath;
        return res.dump();
    });
}

// ── native:batch_file_info ──────────────────────────────────
// Reads OLE metadata from multiple .max files in parallel (no main thread needed)
std::string NativeHandlers::BatchFileInfo(const std::string& params, MCPBridgeGUP* gup) {
    json p = json::parse(params, nullptr, false);
    auto filePaths = p.value("file_paths", std::vector<std::string>{});
    bool listObjects = p.value("list_objects", false);

    if (filePaths.empty()) throw std::runtime_error("file_paths is required");

    // For metadata-only mode, we can parallelize on worker threads
    if (!listObjects) {
        // Launch async tasks for each file
        std::vector<std::future<json>> futures;
        for (const auto& fp : filePaths) {
            futures.push_back(std::async(std::launch::async, [fp]() -> json {
                json fileInfo;
                fileInfo["filePath"] = fp;

                std::wstring wpath = Utf8ToWide(fp);
                DWORD attrib = GetFileAttributesW(wpath.c_str());
                if (attrib == INVALID_FILE_ATTRIBUTES) {
                    fileInfo["error"] = "File not found";
                    return fileInfo;
                }

                // COM init for this thread
                CoInitializeEx(nullptr, COINIT_MULTITHREADED);
                fileInfo["metadata"] = ReadOLEMetadata(wpath);
                CoUninitialize();
                return fileInfo;
            }));
        }

        // Collect results
        json results = json::array();
        for (auto& f : futures) {
            results.push_back(f.get());
        }

        json response;
        response["fileCount"] = results.size();
        response["files"] = results;
        return response.dump();
    }

    // With object listing, we need the main thread for MergeFromFile(MERGE_LIST_NAMES)
    return gup->GetExecutor().ExecuteSync([&filePaths]() -> std::string {
        Interface* ip = GetCOREInterface();
        json results = json::array();

        for (const auto& fp : filePaths) {
            json fileInfo;
            fileInfo["filePath"] = fp;

            std::wstring wpath = Utf8ToWide(fp);
            DWORD attrib = GetFileAttributesW(wpath.c_str());
            if (attrib == INVALID_FILE_ATTRIBUTES) {
                fileInfo["error"] = "File not found";
                results.push_back(fileInfo);
                continue;
            }

            fileInfo["metadata"] = ReadOLEMetadata(wpath);

            // List objects
            NameTab nameList;
            ip->MergeFromFile(wpath.c_str(), TRUE, FALSE, FALSE, MERGE_LIST_NAMES, &nameList);

            json objects = json::array();
            for (int i = 0; i < nameList.Count(); i++) {
                if (nameList[i]) objects.push_back(WideToUtf8(nameList[i]));
            }
            fileInfo["objectCount"] = objects.size();
            fileInfo["objects"] = objects;
            results.push_back(fileInfo);
        }

        json response;
        response["fileCount"] = results.size();
        response["files"] = results;
        return response.dump();
    });
}
