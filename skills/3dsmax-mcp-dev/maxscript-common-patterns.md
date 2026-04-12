# MAXScript: Common Patterns and Recipes

## Undo Blocks

Wrap scene-modifying operations in `undo` blocks to control granularity. One `undo on (...)` block = one undo entry.

```maxscript
-- Named undo block (shows in Edit > Undo menu)
undo "Move Objects" on (
    for obj in selection do obj.pos.z += 10
)

-- Disable undo for heavy batch ops (massive speedup + memory savings)
undo off (
    for i = 2 to objArray.count do attach objArray[1] objArray[i]
)
```

**Critical rule:** Never delete nodes with `undo off` unless they were also created with `undo off`. Deleting undo-tracked nodes while undo is off corrupts the undo stack and can crash Max.

Conditional undo in loops (hold first/last only):
```maxscript
for i = 1 to nVerts do
    with undo (i == 1 or i == nVerts)
        meshop.setvert em i ([1,1,1]*i)
```

## Animate Blocks

```maxscript
animate on (
    at time 0   $box01.pos = [0,0,0]
    at time 50  $box01.pos = [100,0,0]
    at time 100 $box01.pos = [0,0,0]
)
```

Loop-driven animation:
```maxscript
animate on
    for t = 0 to 100 by 5 do
        at time t $foo.pos = $bar.pos + random [-10,-10,-10] [10,10,10]
```

`animate on/off` does NOT change the Auto Key button state. Use `animButtonState` to query/set the UI button.

## Coordinate Systems

```maxscript
in coordsys world  obj.pos             -- world position
in coordsys local  obj.pos             -- local position
in coordsys parent obj.pos             -- parent-relative
in coordsys $other obj.pos             -- relative to another node
in coordsys local  rotate obj (eulerAngles 0 0 45)
in coordsys parent rotate selection (eulerAngles 0 0 90)
```

## Time Context

Read animated values at arbitrary times without moving the slider:
```maxscript
at time 50f  thePos = $box01.pos      -- position at frame 50
at time (t-1f) lastPos = sel.center    -- one frame earlier
```

`sliderTime` gets/sets the actual time slider. `at time` never moves the slider.

## Text File I/O

**Write:**
```maxscript
outFile = createFile @"C:\data\output.txt"
format "Verts: %, Faces: %\n" numV numF to:outFile
for v = 1 to numV do
    format "%\n" (getVert theMesh v) to:outFile
close outFile
```

**Read:**
```maxscript
inFile = openFile @"C:\data\input.txt" mode:"r"
if inFile != undefined do (
    while not eof inFile do (
        line = readLine inFile
        -- process line
    )
    close inFile
)
```

**Read entire file into string:**
```maxscript
f = openFile thePath mode:"r"
seek f #eof
len = filePos f
seek f 0
contents = readChars f len errorAtEOF:false
close f
```

**Append mode:**
```maxscript
f = openFile @"C:\log.txt" mode:"a"
format "% - %\n" localTime "entry" to:f
close f
```

If a script errors before `close`, call `gc()` to release locked files.

## Binary File I/O

```maxscript
-- Write
f = fopen @"C:\data\mesh.bin" "wb"
WriteLong f vertCount #unsigned
for v = 1 to vertCount do (
    p = getVert theMesh v
    WriteFloat f p.x; WriteFloat f p.y; WriteFloat f p.z
)
fclose f

-- Read
f = fopen @"C:\data\mesh.bin" "rb"
vertCount = ReadLong f #unsigned
for v = 1 to vertCount do (
    x = ReadFloat f; y = ReadFloat f; z = ReadFloat f
    setVert theMesh v [x, y, z]
)
fclose f
```

Available types: `ReadByte/WriteByte`, `ReadShort/WriteShort`, `ReadLong/WriteLong`, `ReadFloat/WriteFloat`, `ReadDouble/WriteDouble`, `ReadLongLong/WriteLongLong`, `ReadString/WriteString`. Byte/Short/Long accept `#signed` or `#unsigned`.

Use `fseek f offset #seek_set` / `#seek_cur` / `#seek_end` and `ftell f` for random access.

## DotNet Interop

**Creating objects:**
```maxscript
dnObj = dotNetObject "System.Drawing.Size" 100 200
dnClass = dotNetClass "System.IO.File"
```

**Calling static methods:**
```maxscript
(dotNetClass "System.IO.File").ReadAllText @"C:\data.txt"
(dotNetClass "System.IO.File").WriteAllText @"C:\out.txt" theString
```

**Event handlers:**
```maxscript
timer = dotNetObject "System.Windows.Forms.Timer"
fn onTick = ( print localTime )
dotNet.addEventHandler timer "Tick" onTick
timer.interval = 1000
timer.start()
-- cleanup: timer.stop(); dotNet.removeAllEventHandlers timer
```

**Load an assembly:**
```maxscript
dotNet.loadAssembly "System.Xml"
```

**Inspect unknown objects:**
```maxscript
showProperties dnObj   -- list properties
showMethods dnObj      -- list methods
showEvents dnObj       -- list events
dotNet.showConstructors (dotNetClass "System.Drawing.Point")
```

**DotNet controls in rollouts:**
```maxscript
rollout myRol "Test" (
    dotNetControl lv "System.Windows.Forms.ListView" height:200
    on myRol open do (
        lv.View = lv.View.Details
        lv.Columns.Add "Name" 120
    )
)
```

**DotNet forms (standalone UI):**
```maxscript
hForm = dotNetObject "System.Windows.Forms.Form"
hForm.Text = "My Tool"
hForm.Size = dotNetObject "System.Drawing.Size" 300 200
btn = dotNetObject "System.Windows.Forms.Button"
btn.Text = "Click"
hForm.Controls.Add btn
fn onBtnClick s e = ( print "clicked" )
dotNet.addEventHandler btn "Click" onBtnClick
hForm.Show()
```

## Callbacks / Notifications

```maxscript
-- Register
fn onNodeCreated = ( format "Node created: %\n" (callbacks.notificationParam()) )
callbacks.addScript #nodeCreated onNodeCreated id:#myTool

-- Remove by ID
callbacks.removeScripts id:#myTool
-- Remove by type + ID
callbacks.removeScripts #nodeCreated id:#myTool

-- Inspect
callbacks.show #preRender
```

Common callback types: `#filePreOpen`, `#filePostOpen`, `#filePreSave`, `#preRender`, `#postRender`, `#preRenderFrame`, `#postRenderFrame`, `#selectionSetChanged`, `#nodeCreated`, `#nodePostDelete`, `#sceneNodeAdded`, `#systemPreReset`, `#systemPostReset`.

Use `callbacks.notificationParam()` inside callback to get event-specific data.

## Progress Bars

**Built-in status bar progress:**
```maxscript
progressStart "Processing..." allowCancel:true
for i = 1 to total do (
    -- do work
    if not (progressUpdate (100.0*i/total)) do exit
)
progressEnd()
```

**Percentage gotcha:** Always multiply by `100.0` first: `100.0*i/total` (not `i/total*100` which integer-divides to 0).

**DotNet progress dialog (standalone):**
```maxscript
dlg = dotNetObject "MaxCustomControls.ProgressDialog"
dlg.Show()
dlg.Text = "Working..."
dlg.Controls.Item[1].Text = "Step 1 of N"
dlg.Controls.Item[2].Value = 50  -- percent
-- when done:
dlg.Close()
```

## Error Handling

```maxscript
try (
    -- risky operations
    loadMaxFile thePath
) catch (
    format "Error: %\n" (getCurrentException())
)
```

Always validate before operating:
```maxscript
if selection.count == 0 do return (messageBox "Nothing selected")
if not isValidNode theNode do return()
if (classOf obj) != Editable_Poly do return()
```

Check properties before access:
```maxscript
if isProperty obj #radius then obj.radius = 10
-- or
if hasProperty obj "radius" do obj.radius = 10
```

## String Formatting

```maxscript
-- format to listener
format "Name: %, Pos: %\n" obj.name obj.pos

-- format to string via StringStream
ss = stringStream ""
format "% at %" obj.name obj.pos to:ss
result = ss as string

-- formattedPrint for C-style formatting
formattedPrint 3.14159 format:".2f"   --> "3.14"
formattedPrint 255 format:"#04x"      --> "0x00ff"  (hex)
formattedPrint 42 format:"06d"        --> "000042"  (zero-padded)
formattedPrint "abc" format:"10s"     --> "       abc" (right-aligned)
```

## Collection Iteration Patterns

**Iterate collection directly (faster when no index needed):**
```maxscript
for obj in selection do obj.wireColor = red
```

**By index (when index or progress needed):**
```maxscript
for i = 1 to selection.count do (
    selection[i].wireColor = red
    progressUpdate (100.0*i/selection.count)
)
```

**Collect (builds array from loop):**
```maxscript
bigObjects = for obj in geometry where obj.max.z > 100 collect obj
names = for obj in selection collect obj.name
```

**Filter by class:**
```maxscript
for obj in geometry where classOf obj == Editable_Poly do ( ... )
```

**Filter by property existence:**
```maxscript
for obj in geometry where isProperty obj #radius do obj.radius = 10
```

**Reverse iteration (safe deletion):**
```maxscript
for i = arr.count to 1 by -1 where arr[i] < threshold do
    deleteItem arr i
```

**Mapped operations (no loop needed):**
```maxscript
selection.wireColor = green            -- set property on all
hide selection                          -- mapped function
select (for o in objects where not o.isHiddenInVpt collect o)
```

## Batch File Processing

```maxscript
thePath = getSavePath caption:"Select Folder"
if thePath != undefined do (
    theFiles = getFiles (thePath + "\\*.max")
    for f in theFiles do (
        loadMaxFile f useFileUnits:true quiet:true
        -- do work here
        saveMaxFile f
    )
    resetMaxFile #noPrompt
)
```

## Performance Tips

**1. Disable viewport redraws:**
```maxscript
with redraw off (
    -- heavy scene modifications here
)
-- or: disableSceneRedraw() ... enableSceneRedraw()
```

**2. Disable undo for batch ops:** See Undo Blocks above. 85 sec -> 7 sec for 100K iterations.

**3. Switch away from Modify panel:**
```maxscript
max create mode   -- avoids modifier stack reevaluation
-- or
suspendEditing()
-- do work
resumeEditing()
```

**4. Cache frequently used functions/objects:**
```maxscript
local polyop_getvert = polyop.getvert  -- 470ms -> 0ms per 100K calls
local ep_bo = ep.baseobject            -- avoid repeated node lookup
```

**5. Pre-initialize arrays:**
```maxscript
arr = #()
arr[10000] = 0   -- allocates once, then assign by index
for i = 1 to 10000 do arr[i] = random 1 100
-- much faster than: for i = 1 to 10000 do append arr (random 1 100)
```

**6. Use `for...in` over `for i = 1 to .count` when no index is needed** (1.3x faster).

**7. Use `collect` instead of manual `append`** in loops.

**8. Use bitArrays for face/vert selections** -- far more memory efficient than integer arrays.

**9. Use `matchPattern` over `findString`** for substring checks (1.6x faster).

**10. Use `#name` values instead of `"string"` literals** where possible (8x faster for comparisons).

**11. Use StringStream for building large strings:**
```maxscript
ss = stringStream ""
for i = 1 to 10000 do format "%" i to:ss
result = ss as string
-- much less memory than repeated string concatenation
```

**12. Avoid `return`, `break`, `exit`, `continue`** -- they use C++ exceptions (extremely slow). Use `while` conditions or `if/then/else` instead:
```maxscript
-- BAD: 15890 ms per 100K
fn bad v = (if v == true do return 1; 0)
-- GOOD: 47 ms per 100K
fn good v = (if v == true then 1 else 0)

-- BAD: break in loop (84265 ms)
for i = 1 to 1000 do if i == 10 do (res = i; break)
-- GOOD: while condition (1359 ms)
local found = true
for i = 1 to 1000 while found do
    if i == 10 do (res = i; found = false)
```

**13. Avoid `execute()`** -- use `getProperty`/`setProperty`/`getNodeByName` instead.

## Gotchas

- **Integer division truncates:** `1/3` = `0`. Use `1.0/3` or `1/3.0` for float result.
- **Percentage calculation order:** `100.0*i/total` works. `i/total*100` always yields 0 for i < total.
- **`undefined` vs `unsupplied`:** `undefined` = uninitialized variable. `unsupplied` = omitted keyword argument. Check keyword args with `param == unsupplied`.
- **String mutability:** `append "A" "B"` modifies the original string in place. Calling a function that builds on a string literal mutates it permanently. Use `copy` or StringStream.
- **File locking:** If a script errors before `close`, the file stays locked until `gc()` is called.
- **Undo + delete = crash:** Deleting undo-tracked objects with `undo off` corrupts the undo stack. Either `clearUndoBuffer()` first, or keep undo on for deletes.
- **Modify panel overhead:** Having the Modify panel active causes stack reevaluation on every property change. Switch to Create panel or use `suspendEditing()`.
- **DotNet JIT penalty:** First invocation of any .NET code in a session is slow (JIT compilation). Second call uses cached binaries.
- **DotNet event handlers must be global scope.** For struct methods, create a global wrapper: `fn wrapper a b = myStruct.myMethod a b`.
- **`for o in objects do selectMore o` is catastrophically slow** (11 minutes for 1000 objects). Use `select objects` or `select (for o in objects where <test> collect o)` instead.
- **Node path names with `$`:** `$box*` matches by name pattern. Use `getNodeByName "Box001"` for exact lookup, or `$Box001` for literal names.
- **`at time` is read-only without `animate on`.** Setting properties inside `at time` without `animate on` sets the value at the current time, not at the specified time.
- **Assemblies cannot be unloaded** once loaded via `dotNet.loadAssembly`.
- **Callbacks registered with functions cannot be persisted.** Only string-based callbacks support `persistent:true`.
- **Always use `#noPrompt` with `resetMaxFile`** in batch scripts to avoid blocking save dialogs.
- **DotNet lifetime control**: unreferenced .NET objects may not be collected by MAXScript GC. Use `dotNet.setLifetimeControl obj #dotnet` to let .NET manage the object's lifetime, or `#mxs` (default) for MAXScript-managed.
- **Change handler `do` body runs in isolated context**: cannot reference local variables from surrounding scope. Store state in globals or struct members.
- **Accumulated change handlers leak**: unmanaged `when` constructs persist and degrade performance. Always store the returned ChangeHandler value and call `deleteChangeHandler` to dismiss.
- **Bitmap memory**: `close bm` after `openBitmap`/`renderMap` to release memory. Unclosed bitmaps accumulate. Use `freeSceneBitmaps()` to flush texture caches.

## INI File I/O (Built-in)

```maxscript
-- Read
val = getINISetting @"C:\config.ini" "Section" "Key"

-- Write
setINISetting @"C:\config.ini" "Section" "Key" "Value"

-- Delete key
delINISetting @"C:\config.ini" "Section" "Key"
-- Delete section
delINISetting @"C:\config.ini" "Section"

-- List all sections
getINISetting @"C:\config.ini"
-- List all keys in a section
getINISetting @"C:\config.ini" "Section"
```

Commonly used for tool configuration. Returns empty string `""` if key not found.

## Change Handlers (when construct)

Monitor object attribute changes:
```maxscript
-- Monitor transform changes
local handler = when transform $Box001 changes val do (
    format "Box moved to: %\n" $Box001.pos
)

-- Monitor multiple objects
when geometry selection changes do (
    format "Geometry changed on selection\n"
)

-- Monitor name changes
when name $* changes do (
    format "Something renamed\n"
)

-- Dismiss handler
deleteChangeHandler handler
```

Monitorable attributes: `geometry`, `topology`, `names`, `transform`, `select`, `subobjectSelect`, `parameters`, `controller`.

**handleAt parameter**: controls when callback fires:
```maxscript
-- Default: fires at unknown time (possibly mid-operation)
when transform $Box001 changes do (...)

-- Fire at redraw time (safer for UI updates)
when transform $Box001 changes handleAt:#redrawViews do (...)
```

**Deletion monitoring:**
```maxscript
when $Box001 deleted obj do (
    format "% was deleted\n" obj.name
)
```

## Node Event System (3ds Max 2009+)

More comprehensive than `when` constructs. Catches events that `when` misses (undo/redo, linking, layer changes).

```maxscript
fn myCallback evt nd = (
    format "Event: % on nodes: %\n" evt nd
)

nec = NodeEventCallback mouseUp:true delay:200 \
    added:myCallback \
    deleted:myCallback \
    nameChanged:myCallback \
    geometryChanged:myCallback \
    topologyChanged:myCallback \
    materialChanged:myCallback \
    wireColorChanged:myCallback \
    selectionChanged:myCallback \
    linkChanged:myCallback \
    layerChanged:myCallback \
    controllerChanged:myCallback \
    hideChanged:myCallback \
    freezeChanged:myCallback

-- Disable/enable
nec.enabled = false
nec.enabled = true

-- Cleanup (critical!)
nec = undefined
gc light:true
```

`mouseUp:true` delays firing until mouse release (prevents per-frame spam during dragging). `delay:` coalesces rapid events (ms).

## Viewport Redraw Callbacks

Draw custom overlays in viewports:
```maxscript
fn myRedrawCallback = (
    gw.setTransform (matrix3 1)
    gw.text [10,10,0] "Hello Viewport" color:yellow
    gw.enlargeUpdateRect #whole
    gw.updateScreen()
)

-- Register
registerRedrawViewsCallback myRedrawCallback

-- Unregister (ALWAYS clean up — leaks cause permanent lag)
unRegisterRedrawViewsCallback myRedrawCallback
```

**Warning**: Heavy operations in redraw callbacks cause viewport lag. Keep callback functions minimal.

## Garbage Collection Details

```maxscript
-- Full GC: frees all reclaimable values, FLUSHES UNDO BUFFER
gc()

-- Light GC: skips MAXWrapper values, preserves undo
gc light:true

-- Check heap usage
heapSize     -- current heap allocation (bytes)
heapFree     -- available heap (bytes)
```

**How automatic GC works:**
1. Heap runs low → tries light GC first (preserves undo)
2. If insufficient → full GC (flushes undo buffer)
3. If still insufficient → expands heap

**Rules:**
- Use `gc light:true` in tools where undo preservation matters
- Call `gc()` (full) to release locked file handles from errored scripts
- Never rely on `gc light:true` to collect node references — they are MAXWrapper-derived
- Heavy scripts should periodically `gc light:true` to prevent GC pauses at unpredictable moments

## Debugging Techniques

**MAXScript Debugger** (built-in):
- Open via MAXScript menu → Debugger
- Supports breakpoints, step-through, variable inspection
- Manual breakpoint: insert `break()` in code
- Examine locals, globals, and call stack while paused

**Profiling with timeStamp:**
```maxscript
t1 = timeStamp()
-- code to profile
t2 = timeStamp()
format "Elapsed: %ms\n" (t2 - t1)
```

**Runtime inspection:**
```maxscript
classOf obj             -- exact class
superClassOf obj        -- superclass
showProperties obj      -- list all properties
showMethods obj         -- list all methods
showInterfaces obj      -- list all interfaces
isValidNode obj         -- check if node reference is still valid
isProperty obj #name    -- check if property exists
getMAXScriptHost()      -- determine execution context
```

**Error source info (3ds Max 2018+):**
```maxscript
try ( riskyOp() ) catch (
    format "Error: %\n" (getCurrentException())
    format "File: %\n" (getErrorSourceFileName())
    format "Line: %\n" (getErrorSourceFileLine())
)
```
