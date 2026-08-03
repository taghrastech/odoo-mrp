# Changelog

All notable changes to `tt_mrp_backorder_traceability` are documented in this file.

## [18.0.1.0.0] — 2026-08-03

First release.

### Added

- **Original MO** (`tt_split_root_id`) — the root of a chain of splits and
  backorders. Self-referenced on the original order, so grouping by this field
  gathers the original together with everything derived from it.
- **Derived From** (`tt_split_parent_id`) — the immediate parent, which reads
  cascading splits.
- **Origin** (`tt_split_origin`) — *Original*, *Split*, *Backorder* or
  *Undetermined*.
- **Splits & Backorders** tab on the manufacturing order form: the whole chain
  with its quantity totals (to produce, produced, remaining, cancelled), a
  progress bar, the source document, and the lots consumed.
- Search filters *Original MOs*, *Splits*, *Backorders*, and grouping by
  **Original MO**, **Origin** and **Source Document** — the last one is not
  offered by the standard search view.
- Optional columns on the manufacturing orders list.
- French translation.

### Behaviour

- Links are written through `_get_backorder_mo_vals()`, the extension point the
  standard module itself uses. Every split path converges there: split wizard,
  backorder wizard on validation, mass production by lot or serial number,
  subcontracting and the Shop Floor.
- *Split* and *Backorder* are told apart by whether quantities were given
  upfront: a deliberate split provides them, the remainder of an order closed
  short does not.
- Splitting an order that is already derived keeps the **initial** order as root,
  never the intermediate one.
- Only orders that actually produced a new order are flagged: splitting with the
  remaining quantity cancelled creates nothing and marks nothing.
- Deleting the root promotes the oldest remaining member instead of dissolving
  the chain.
- Duplicating an order gives a standalone order, never a chain member.
- Consumed lots are shown only when the order consumes the very product it
  produces. On a regular order the components are other products, and the column
  is dropped.
- Cancelled component moves are excluded everywhere: they carry no material.

### Existing data

- A post-install hook rebuilds the root on orders split before installation,
  keyed on procurement group, reference base name and product. The `-NNN` suffix
  must match the backorder sequence exactly, so a reference such as
  `MO-2026-0018` coming from a custom sequence is never mistaken for a family.
  The hook is idempotent and can be run again.

### Known limitations

- The immediate parent is not rebuilt on historical data. `backorder_sequence`
  is a flat counter that does not encode which order was split from which, nor
  whether an order came from a split or a backorder, so those orders are
  reported as *Undetermined* rather than given an invented parentage.
- Quantities are summed as-is across a chain, which is correct because every
  order of a chain shares the same product and unit of measure.
- Consumed lots are listed without their quantities: a many2many cannot carry
  them. The quantities stay one click away, in the components tab of the order.
