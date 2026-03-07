# Data Channel Modifier — Complete Reference

The Data Channel modifier is 3ds Max's node-based per-vertex/face data processing system. Think **Houdini VOPs but living in the modifier stack**. It chains operators that read mesh data, process it mathematically, and write results to channels like position, selection, vertex color, UVs, normals, and more.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Data Channel Modifier                   │
│                                                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │  INPUT    │──▶│ PROCESS  │──▶│  OUTPUT  │            │
│  │ Operators │   │ Operators│   │ Operators│            │
│  └──────────┘   └──────────┘   └──────────┘            │
│                                                          │
│  Multiple independent pipelines can coexist.             │
│  operator_order defines which ops are active and in      │
│  what sequence they execute.                             │
└─────────────────────────────────────────────────────────┘
```

### Key Concepts

- **Operator Stack**: A flat array of operators (`dcMod.operators[]`). 1-based indexing.
- **Processing Order** (`operator_order`): A 0-based index array defining which operators are active and their execution sequence. Operators NOT in the order are dormant/belong to other pipelines.
- **Data Stack**: Operators pass float or point3 data through an internal stack. Input operators push data, process operators transform it, output operators write it to the mesh.
- **Multiple Pipelines**: A single DC modifier can contain multiple independent operator chains. The `operator_order` sequences them — when an output operator writes, the next input operator starts a fresh pipeline.
- **Element-Aware Processing**: GeoQuantize and TransformElements can operate per-element (connected faces), not just per-vertex.

## MAXScript Interface

### Creating and Accessing

```maxscript
-- Add to an object (MUST be Editable Mesh/Poly)
local obj = $MyObject
convertToPoly obj
local dcMod = DataChannelModifier()
dcMod.display = true
addModifier obj dcMod

-- Access the interface
local dcIF = dcMod.DataChannelModifier
```

### Interface Methods

| Method | Description |
|--------|-------------|
| `dcIF.NumberOperators()` | Total available operator types |
| `dcIF.OperatorName i &name` | Get operator type name by index |
| `dcIF.OperatorInfo i &info` | Get operator description |
| `dcIF.OperatorID i &idA &idB` | Get class ID for AddOperator |
| `dcIF.AddOperator idA idB whereAt` | Add operator at stack position |
| `dcIF.StackCount()` | Current operator count in modifier |
| `dcIF.StackOperatorName i &name` | Get stack operator name |
| `dcIF.SelectStackOperator i` | Select operator (UI) |
| `dcIF.DeleteStackOperator i` | Remove operator |
| `dcIF.ReorderStackOperator indexList` | Reorder operators |
| `dcIF.SavePreset name tooltip` | Save current graph as preset |
| `dcIF.LoadPreset name` | Load a preset graph |
| `dcIF.PresetCount()` | Number of saved presets |
| `dcIF.PresetName i &name` | Get preset name |

### Modifier Properties

| Property | Type | Description |
|----------|------|-------------|
| `operators` | Array | All operator instances |
| `operator_enabled` | Bool[] | Per-operator enable state |
| `operator_order` | Int[] | 0-based processing sequence |
| `operator_ops` | Int[] | Per-operator blend mode (0=Replace, 1=Add, 2=Sub, 3=Mul, 4=Div, 5=Dot, 6=Cross) |
| `operator_frozen` | Bool[] | Per-operator freeze state |
| `display` | Bool | Viewport display |
| `debugInfo` | Bool | Show debug overlay |
| `showNumericData` | Bool | Show per-vertex values |
| `floatDisplay` | Int | 0=Ticks, 1=Shaded Colors |
| `point3Display` | Int | 0=Position, 1=Color, 2=Vector, 3=Shaded |
| `minColor/midColor/maxColor` | Color | Gradient for shaded display |

---

## Operator Catalog (32 Operators)

### INPUT Operators

#### Vertex Input
Reads per-vertex data from the mesh into the stack.

| Property | Values |
|----------|--------|
| `input` | 0=Position, 1=SoftSelection/VData, 100=Selection, 101=Average Normal, 102=Map Channel 1, 103=Map Channel 2, 200+=Extended channels |
| `xyz` | 0=XYZ (all), 1=X only, 2=Y only, 3=Z only |
| `Internal` | Internal flag (usually 1) |

**ID**: `(3658656257, 0)`

#### Face Input
Reads per-face data from the mesh.

| Property | Values |
|----------|--------|
| `input` | 0=Selection, 1=Material ID, 2=Smooth Group, 3=Area, 4=Normal, 5=Planarity |

**ID**: `(38019502, 0)`

#### Edge Input
Reads per-edge data from the mesh.

| Property | Values |
|----------|--------|
| `input` | 0=Selection, 1=Crease Weights, 2=Edge Angle |

**ID**: `(590351565, 0)`

#### XYZ Space
Copies vertex position onto the stack in a chosen coordinate space.

| Property | Values |
|----------|--------|
| `space` | 0=Local, 1=World, 2=Node (relative to `node`) |
| `normalize` | Bool — normalize to min/max range |
| `min/max` | Float — normalization range |
| `node` | Reference node for space=2 |

**ID**: `(236038690, 0)`

#### Component Space
Copies a single position axis (X, Y, or Z) to the stack as a float.

| Property | Values |
|----------|--------|
| `component` | 0=X, 1=Y, 2=Z |
| `space` | 0=Local, 1=World |
| `normalize` | Bool |
| `min/max` | Float |

**ID**: `(236038707, 0)`

#### Curvature
Computes surface curvature per vertex as a float value.

**ID**: `(236108612, 0)` — Uses defaults, auto-computed from mesh topology.

#### Velocity
Computes per-vertex motion as a point3 (requires animation).

| Property | Values |
|----------|--------|
| `timeoffset` | Int — frames to offset |
| `worldSpace` | Bool |
| `noTranslation` | Bool — ignore object translation |

**ID**: `(237091669, 0)`

#### Node Influence
Float value based on distance from a reference node to each vertex/element.

| Property | Values |
|----------|--------|
| `node` | Reference node |
| `minRange/maxRange` | Float — distance range |
| `minValue/maxValue` | Float — output range |
| `mode` | 0=By Vertex, 1=By Element, 2=By Object |
| `hold` | Int |
| `falloffCurve` | CurveControl |
| `radiusCurve` | CurveControl — radius over time |
| `strengthCurve` | CurveControl — strength over time |

**ID**: `(3416675101, 0)`

#### Tension Deform
Computes squash/stretch from mesh deformation (requires animation/skinning).

| Property | Values |
|----------|--------|
| `mode` | 0=Edge Length, 1=Edge Angle |
| `stretch/squash` | Float — amounts |
| `stretchRange/squashRange` | Float |
| `outputSquash/outputStretch` | Bool |

**ID**: `(1215902043, 0)`

#### Distort
Uses a texture map to modify vertex values.

| Property | Values |
|----------|--------|
| `map` | TextureMap — Noise, Bitmap, etc. |
| `strength` | Float |

**ID**: `(301607866, 0)`

#### Maxscript (Script Operator)
Arbitrary MAXScript code for per-vertex/face processing. **The most powerful operator.**

| Property | Values |
|----------|--------|
| `script` | String — the MAXScript code |
| `elementtype` | 0=Vertices, 1=Faces |
| `DataType` | 0=Float, 1=Point3 |

**ID**: `(2597005274, 0)`

Script signature:
```maxscript
on Process theNode theMesh elementType outputType outputArray do
(
    -- theNode: scene node
    -- theMesh: PolyMesh copy (use polyop.* functions)
    -- elementType: 1=Vertices, 2=Faces (set by engine)
    -- outputType: 1=Floats, 2=Point3s (set by engine)
    -- outputArray: fill this with per-vert/face values
)
```

#### Maxscript Process
Like Maxscript but processes existing stack data rather than generating new data.

**ID**: `(3180516783, 0)`

#### Expression Float / Expression Point3
Uses 3ds Max expression controllers for data generation.

| Property | Values |
|----------|--------|
| `expControl` | Float_Expression or Position_Expression controller |

**IDs**: Float `(1185521650, 0)`, Point3 `(1185521649, 0)`

---

### PROCESS Operators

#### Vector
Combines an external vector with stack data using various math operations.

| Property | Values |
|----------|--------|
| `space` | 0=Add, 1=Subtract, 2=Dot Product, 3=Cross Product, 4=Multiply |
| `dir` | 0=World axis, 1=Local axis, 2=Custom vector |
| `x/y/z` | Float — custom direction components |
| `node` | Reference node for direction |

**ID**: `(1155607757, 0)`

#### Scale
Multiplies the stack value by a constant.

| Property | Values |
|----------|--------|
| `scale` | Float — multiplication factor |

**ID**: `(283192250, 0)`

#### Clamp
Limits stack values to a range.

| Property | Values |
|----------|--------|
| `clampMin` | Float |
| `clampMax` | Float |

**ID**: `(551627706, 0)`

#### Invert
Inverts stack values (1 - value for floats, negation for point3).

| Property | Values |
|----------|--------|
| `invert` | Bool |

**ID**: `(1135524769, 0)`

#### Normalize
Normalizes stack values to a target range.

| Property | Values |
|----------|--------|
| `normalizeMin/normalizeMax` | Float — target range |
| `rangeOverride` | Bool — use explicit source range |
| `rangeMin/rangeMax` | Float — source range when override=true |

**ID**: `(103725985, 0)`

#### Curve
Remaps values through a curve control (like a transfer function).

| Property | Values |
|----------|--------|
| `curve` | CurveControl |
| `normalize` | Bool |

**ID**: `(1944136634, 0)`

#### Smooth
Spatial smoothing of values based on neighboring vertices.

| Property | Values |
|----------|--------|
| `iteration` | Int |
| `smoothAmount` | Float |

**ID**: `(2481007546, 0)`

#### Decay
Temporal persistence/decay of values (requires scrubbing timeline).

| Property | Values |
|----------|--------|
| `decay` | Float — decay per frame |
| `Samples` | Int |
| `smooth` | Bool |
| `iterations` | Int — smoothing iterations |
| `resetType` | 0=Use Frame, 1=Reset To Zero |
| `resetFrame` | Int |
| `useCurve` | Bool |

**ID**: `(284830921, 0)`

#### Point3 To Float
Converts point3 stack data to float.

| Property | Values |
|----------|--------|
| `floatType` | 0=Length (magnitude), 1=X, 2=Y, 3=Z |

**ID**: `(1137503061, 0)`

#### GeoQuantize
Makes all vertices in a geometric element share the same value.

| Property | Values |
|----------|--------|
| `mode` | 0=By Vertex, 1=By Element, 2=By Object |

**ID**: `(496046533, 0)`

#### Convert To SubObject Type
Copies data between vertex/face/edge levels.

| Property | Values |
|----------|--------|
| `subObject` | Target type |
| `vertex` | 0=Position, 1=Normal, 2=Map |
| `mapChan` | Int — map channel when vertex=2 |

**ID**: `(2888899789, 0)`

#### Color Space Conversion
Converts between color spaces (RGB, HSL, etc.).

**ID**: `(3257339550, 0)`

---

### OUTPUT Operators

#### Vertex Output
Writes stack data to a mesh vertex channel.

| Property | Values |
|----------|--------|
| `output` | **0=Position, 1=Vertex Color, 2=Map Channel, 3=Normals, 4=Selection, 5=Vertex Crease, 6=VData** |
| `channelNum` | Int — channel number for Map Channel/VData |
| `xyz` | 0=XYZ, 1=X, 2=Y, 3=Z |
| `replace` | **0=Replace, 1=Add, 2=Subtract, 3=Multiply** |

**ID**: `(2882382387, 0)`

#### Face Output
Writes stack data to face-level mesh data.

| Property | Values |
|----------|--------|
| `output` | **0=Selection, 1=Material ID, 2=Smoothing Group** |
| `type` | 0=Replace, 1=Add, 2=Subtract, 3=Multiply |

**ID**: `(52689454, 0)`

#### Edge Output
Writes stack data to edge-level mesh data.

| Property | Values |
|----------|--------|
| `output` | **0=Selection, 1=Crease Weights** |
| `type` | 0=Replace, 1=Add, 2=Subtract, 3=Multiply |

**ID**: `(17934909, 0)`

---

### COMPOSITE Operators

These operators both read AND write — they consume stack data and modify the mesh directly.

#### Transform Elements
Transforms mesh elements (position, rotation, scale) driven by stack/selection data.

| Property | Values |
|----------|--------|
| `inputChannel` | **0=From Stack, 1=Soft Selection, 2=Vertex Color Luminance, 3=Vertex Color as XYZ, 4=None** |
| `transformType` | **0=Position, 1=Rotation, 2=Scale %, 3=Scale % Uniform** |
| `XEnable/YEnable/ZEnable` | Bool — axis enables |
| `xoffset1/yoffset1/zoffset1` | Float — min values (when input=0) |
| `xoffset2/yoffset2/zoffset2` | Float — max values (when input=1) |
| `pointAtNode` | Bool |
| `pointNode` | Node reference |
| `axisMode` | 0=X, 1=Y, 2=Z |
| `pointElements` | Bool — use element centers |
| `randomize` | Bool |
| `randomize1/randomize2` | Float — random range |
| `seed` | Int |
| `phase` | Float — animated offset |

**ID**: `(655960264, 0)`

#### Color Elements
Colors mesh elements from various sources.

| Property | Values |
|----------|--------|
| `inputOption` | 0=Vertex Colors, 1=Map, 2=Soft Selection, 3=From Stack |
| `colorOption` | 0=Face, 1=Element |
| `useColors` | Bool |
| `color1/color2` | Color — gradient endpoints |
| `outputChannel` | Int — target map channel |
| `randomize` | Bool |
| `HRand/SRand/LRand` | Bool — randomize Hue/Saturation/Lightness |
| `randomizeHPercent/SPercent/LPercent` | Float |
| `seed` | Int |

**ID**: `(1270620223, 0)`

#### Delta Mush
Smooths deformed mesh while retaining original detail.

| Property | Values |
|----------|--------|
| `strength` | Float (default 1.0) |
| `iterations` | Int (default 10) |
| `pinBorders` | Bool (default true) |
| `outputMode` | 0=Relaxed Base, 1=Relaxed, 2=Relaxed Delta |

**ID**: `(3367109027, 0)`

---

## Pipeline Patterns (Recipes)

### Select Vertices by Slope
Select upward-facing vertices (for snow, moss, etc.):
```
VertexInput(input=101, AvgNormal)
  → Vector(space=2, DotProduct, dir=2, z=1.0)
  → Clamp(0.0, 1.0)
  → VertexOutput(output=4, Selection)
```

### Select by World Position (Height)
Select vertices based on Z height:
```
ComponentSpace(component=2, Z, space=1, World)
  → Normalize(min=0, max=1, rangeOverride=true, rangeMin=0, rangeMax=100)
  → Clamp(0.0, 1.0)
  → VertexOutput(output=4, Selection)
```

### Random Element Scale (Explode/MoGraph)
Scale elements randomly with attractor influence:
```
NodeInfluence(node=Attractor, mode=1, Element)
  → GeoQuantize(mode=1, Element)
  → TransformElements(inputChannel=0, Stack, transformType=3, Scale%)
  → VertexOutput(output=0, Position)
```

### Curvature-Based Vertex Color
Paint concave/convex regions for wear maps:
```
Curvature
  → Normalize(0.0, 1.0)
  → Curve (remap falloff)
  → VertexOutput(output=1, Vertex Color)
```

### Geometric Motion Blur
Smear vertices along their velocity vector:
```
Velocity(worldSpace=true)
  → Scale(0.01)
  → Decay(3.9, smooth=true)
  → VertexOutput(output=0, Position, replace=1, Add)
```

### Camera-Facing Selection
Select vertices facing a camera:
```
VertexInput(input=0, Position)
  → XYZSpace(space=1, World)
  → Vector(space=3, CrossProduct, dir=2, node=Camera)
  → Clamp(0.0, 1.0)
  → VertexOutput(output=4, Selection)
```

### Animated Text Reveal (MXS Script Operator)
Reveal vertices sequentially over time:
```maxscript
on Process theNode theMesh elementType outputType outputArray do
(
    if theMesh == undefined then return 0
    local nv = polyop.getNumVerts theMesh
    local duration = 96.0
    outputArray.count = nv
    for i = 1 to nv do (
        if (i as float / nv as float) < (sliderTime.frame / duration)
            then outputArray[i] = 0
            else outputArray[i] = 1
    )
)
```

### Per-Element Random Color
```
MXS Script(seed per vertex → random float)
  → GeoQuantize(mode=1, Element)
  → ColorElements(inputOption=3, FromStack, colorOption=1, Element)
  → VertexOutput(output=2, MapChannel, channelNum=2)
```

---

## MCP Tool Reference

Five tools are available via the 3dsmax-mcp bridge:

### `add_data_channel`
Build a complete DC operator graph on an object. Pass an array of operator definitions with types and params.

### `inspect_data_channel`
Read back the full operator graph with all parameters — for debugging or understanding existing setups.

### `set_data_channel_operator`
Modify individual operator parameters without rebuilding the graph.

### `add_dc_script_operator`
Convenience tool to add a MAXScript Script Operator with automatic output wiring.

### `list_dc_presets` / `load_dc_preset`
Discover and load saved Data Channel presets.

---

## Pitfalls & Lessons Learned

1. **Object must be Editable Mesh/Poly** — DC modifier won't work on parametric objects. Always `convertToPoly` first.

2. **operator_order is 0-based** — The indices in `operator_order` are 0-based offsets into the `operators[]` array (which is 1-based in MAXScript). So operator_order `#(0, 1, 2)` maps to `operators[1], operators[2], operators[3]`.

3. **Operators not in order are dormant** — They exist in the array but don't execute. Multiple independent pipelines coexist by having separate sequences in the order.

4. **TransformElements reads from stack OR selection** — When `inputChannel=0` (From Stack), it uses the last stack value. When `inputChannel=1` (Soft Selection), it reads the mesh's soft selection weights. The stack approach requires the data to flow through preceding operators in the order.

5. **GeoQuantize is essential for per-element operations** — Without it, TransformElements and ColorElements operate per-vertex, creating torn/inconsistent element transforms. Always add GeoQuantize(mode=1) before element-level operators.

6. **Script Operator signature variations** — Older scripts use 4 args (`theNode, theMesh, elementType, outputType, outputArray`), newer ones add `theTime` as a 6th argument. Both work.

7. **Operator IDs are stable** — The `(idA, idB)` class IDs are version-independent. The same IDs work across 3ds Max 2017-2025+.

8. **Curve operator curves aren't easily scriptable** — The `curve` property is a CurveControl reference. Setting specific curve shapes via MAXScript requires manipulating the CurveControl's points, which is complex. For simple remapping, use Scale + Clamp + Normalize instead.

9. **VertexOutput replace modes matter** — `replace=0` overwrites, `replace=1` adds to existing values. This is critical for motion blur (add velocity to position) vs. direct position replacement.

10. **Node references in operators** — NodeInfluence.node and Vector.node must be set to actual scene node references (`getNodeByName "name"`), not strings.

---

## Built-in Presets (3ds Max 2025)

Stored in `<3ds Max install>\en-US\plugcfg\DataChannelPresets`:

| Preset | Added In |
|--------|----------|
| Angle Mask | 2017.1 |
| Auto Edge Crease Weights | 2017.1 |
| Delta Mush | 2017.1 |
| Dirt Map | 2017.1 |
| Edge Wear Mask | 2017.1 |
| Explode Elements | 2024.2 |
| Map to Soft Selection | 2024.2 |
| Random Element Color | 2024.2 |
| Smooth Push | 2024.2 |
| Invert Soft Selection | 2025 |
| Select Border Edges of Selected Polygons | 2025 |
| Select Hard Edges By Smoothing Group | 2025 |
| Select Open Edges | 2025 |
| Select Open Edge Verts | 2025 |
| Select UV Seam Edges | 2025 |
| Select Top | 2025 |
| Select Polygon by Elements | 2025 |
| Convert Face VC to Vertex VC | 2025 |
| Convert Material ID to Smoothing Group | 2025 |

---

## Version History

| Version | Additions |
|---------|-----------|
| **2017.1** | Data Channel modifier introduced with all base operators |
| **2024.2** | MAXScript Process Operator, Expression Float/Point3, 4 new presets |
| **2025** | 10 new presets focused on selection and data conversion |

**Backward compatibility**: Incompatible with 3ds Max 2017 and earlier (displays as stand-in). Set `DataChannelSaveAs2017 = 1` in `3dsmax.ini` for backward save.

---

## Technical Constraints

1. **Operators targeting different sub-object types** (edge, face, vertex) cannot coexist in the same stack unless `Convert To SubObject Type` bridges them.
2. **Output operators have no blend mode** — they always write the result.
3. **Input operators at the top** must use Replace blend mode.
4. **Freeze** locks operator values (shown in blue) — values stop updating.
5. **Multiple input/output pairs** can exist in a single DC modifier, enabling multi-channel operations within one modifier instance.

---

## Sources

- [Autodesk 3ds Max Developer Help — Data Channel Modifier](https://help.autodesk.com/view/MAXDEV/2025/ENU/?guid=GUID-FCBC7CA5-BFA5-4C5C-8D92-4E40C9EC1388)
- [Autodesk 3ds Max Help — Data Channel Modifier](https://help.autodesk.com/view/3DSMAX/2025/ENU/?guid=GUID-99C5FAEC-993A-404F-BB09-B52C30679564)
- [Data Channel Modifier Operator Classes](https://help.autodesk.com/cloudhelp/2019/ENU/3DSMax-MAXScript/files/GUID-F55E55FE-A78F-431D-9B47-2670DAABEAB6.htm)
- [Data Channel Input Operators](https://help.autodesk.com/cloudhelp/2017/ENU/3DSMax/files/GUID-D9D9CEC2-8633-4F27-98C8-AFD8FEE5A644.htm)
- ChangsooEun example scenes (`D:\3dsMax\Data_Channel_3dsmax\`)
