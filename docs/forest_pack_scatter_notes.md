# Forest Pack Scatter Notes (MCP)

This documents what worked in production while implementing `scatter_forest_pack`.

## What Must Be Set

- `fp.surflist` must contain valid surface nodes.
- Area/distribution lists must be initialized together:
  - `fp.arnodelist`
  - `fp.arnamelist`
  - `fp.artypelist`
  - `fp.arincexclist`
  - `fp.arprojectlist`
  - `fp.pf_aractivelist`
  - `fp.aridlist`
- `fp.cobjlist` must contain source geometry nodes.
- `fp.namelist`, `fp.problist`, and `fp.geomlist` must align to source count.

If area lists are missing or inactive, Forest can appear configured but show no real distribution.

## Critical Defaults That Fixed Real Failures

- `fp.geomlist`: use `2` per source for custom object mode.
- `fp.pf_aractivelist`: must be `true` for each area.
- Use explicit world-unit decode for size-related params:
  - `units.decodeValue "<value>cm"`
- Density section size is important:
  - `fp.units_x`
  - `fp.units_y`

Most "it has params but nothing scatters" issues were from density units or inactive area list.

## Facing Mode Rules

- `fp.direction = 0` for surface-normal alignment (sprinkles/debris).
- `fp.direction = 1` for world-up alignment (trees/upright assets).

Recommended tool-level validation: allow only `0` or `1`.

## Practical Unit Guidance

- Always treat scatter sizing as explicit centimeters in tool inputs.
- Decode to world units inside MAXScript with `units.decodeValue`.
- Keep non-zero minimum clamps for width/height/icon/density units.

Defaults that were reliably visible for small test scenes:

- `source_width_cm = 5.0`
- `source_height_cm = 5.0`
- `icon_size_cm = 30.0`
- `density_units_x_cm = 300.0`
- `density_units_y_cm = 300.0`

For larger visible spread tests, using around `500.0` for density units helped.

## Error Handling That Helped Debugging

- Return explicit error if `Forest_Pro` class is unavailable.
- Return explicit error with missing object names for surfaces/sources.
- Return JSON summary after build:
  - surface count
  - source count
  - distribution count
  - density
  - seed

This made scene-side verification much faster than guessing from viewport alone.

