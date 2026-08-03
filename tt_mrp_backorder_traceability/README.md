# Manufacturing Splits and Backorders Traceability

Link, filter and group manufacturing orders with their splits and backorders.

## The problem it solves

When a manufacturing order is split, or when it is closed short and leaves a
backorder, Odoo renames the orders `MO/0001-001`, `MO/0001-002`, … but stores
**no relational link between them**. Two native hints look like they could
stand in, and neither holds:

- **`procurement_group_id`** — pull routes such as make-to-order propagate a
  single procurement group across manufacturing orders that have nothing to do
  with one another. The native *Backorders* button, which relies on it, therefore
  reports unrelated orders as related.
- **`backorder_sequence`** — a flat counter used only to build the `-NNN`
  suffix, and computed *per procurement group*, so make-to-order pollutes it too.
  It points at nothing.

The consequence is practical: there is no way to filter or group a family of
splits and backorders in the manufacturing orders list, and no way to see, from
one order, what became of the rest of the quantity.

## What the module adds

### A dependable link

- **Original MO** — the root of the whole chain. It is also set on the original
  order itself, so grouping by this field keeps the original together with
  everything derived from it.
- **Derived From** — the immediate parent, which reads cascading splits.
- **Origin** — how each order came to be: *Original*, *Split*, *Backorder*, or
  *Undetermined* for orders derived before the module was installed.

Every split path is covered, including the split wizard, the backorder wizard on
validation, mass production by lot or serial number, subcontracting and the Shop
Floor. They all converge on a single native extension point, so no code path is
patched one by one.

### A consolidated tab

A **Splits & Backorders** tab lists the whole chain in place, with its quantity
totals — to produce, produced, remaining, cancelled — and a progress bar. Rows
open in the standard dialog, editable, with the expand-to-page button.

For orders that consume the very product they produce, as a cutting or
portioning operation does, the tab also shows the **lots consumed** by each order
and by the chain as a whole. On a regular order the components belong to other
products, so the column is dropped rather than filled with noise.

### Filters and grouping

In the manufacturing orders list: search on the original order, filters for
*Original MOs*, *Splits* and *Backorders*, and grouping by **Original MO**,
**Origin** and **Source Document**.

### Existing data

On installation, chains created before the module are rebuilt from the
procurement group, the reference base name and the product, with the `-NNN`
suffix checked against the backorder sequence so a reference like
`MO-2026-0018` coming from a custom sequence is never split into a family by
mistake.

The immediate parent is **not** guessed on historical data: `backorder_sequence`
is a flat counter that does not encode which order came from which, so those
orders are reported as *Undetermined* rather than given an invented parentage.

## Notes

- Purely additive: no native behaviour is changed, and the native *Backorders*
  button is left in place.
- Depends on `mrp` only.
- French translation.
- Compatible with Odoo 18, Community and Enterprise.

## License

LGPL-3
