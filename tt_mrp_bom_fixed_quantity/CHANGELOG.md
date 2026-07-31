# Changelog

All notable changes to `tt_mrp_bom_fixed_quantity` are documented in this file.

## [18.0.1.0.0] — 2026-07-31

First release.

### Added

- **Quantity Mode** (`tt_qty_type`) on bill of materials lines, with two modes:
  - *Proportional* — the Odoo standard, the quantity follows the quantity to
    produce. Default value, so existing bills of materials are unaffected.
  - *Fixed Quantity* — the quantity written on the line is consumed as is,
    whatever the quantity to produce.
- The field is shown in the **Components** tab of the bill of materials form and
  on the bill of materials line form.
- French translation.

### Behaviour

- The fixed quantity is applied while the component moves are created, through
  `mrp.bom.line._prepare_line_done_values()`. Quantities are therefore correct
  from the very first write, which keeps reservations, consumption and
  traceability consistent. No scheduled action and no post-creation fix-up.
- The *Update quantity* wizard no longer rescales fixed components.
- Splitting a manufacturing order gives the full fixed quantity to the original
  order **and** to every backorder, since each backorder is a separate physical
  unit.
- On a partial production, a fixed component is expected and consumed in full;
  it is no longer reported as under-consumed on a strict-consumption bill of
  materials.
- A genuine over-consumption is still reported by the standard consumption
  check.
- The mode never locks the line: the quantity can be changed by hand on the
  manufacturing order, and that entry survives the *Update quantity* wizard and
  the creation of backorders.

### Known limitations

- A manufacturing order producing more than the nominal quantity of the bill of
  materials still consumes the fixed quantity only once. Adjust the component
  quantity by hand when this happens.
- The **Bill of Materials Overview** report recomputes its quantities inline
  instead of exploding the bill of materials, so it keeps displaying the
  proportional value for fixed components.
