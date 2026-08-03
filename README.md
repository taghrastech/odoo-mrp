# Odoo Manufacturing Modules

Open-source Odoo modules developed by **[TaghrasTech](https://github.com/taghrastech)**.

---

## Modules

### [`tt_mrp_bom_fixed_quantity`](tt_mrp_bom_fixed_quantity/) — Fixed Quantity Components on Bills of Materials

Consume a bill of materials component with a **fixed quantity**, whatever the quantity produced.

- Adds a **Quantity Mode** on each bill of materials line: *Proportional* (Odoo standard, default) or *Fixed Quantity*
- The fixed quantity is applied when the component moves are created, so reservations, consumption and traceability are right from the start — no automated correction afterwards
- Fixed components keep their full quantity on backorders, since each backorder is a separate physical unit
- Never locks the line: the quantity stays editable by hand on the manufacturing order, and that entry survives every later recomputation
- Works with multi-level bills of materials, variants, kits and subcontracting
- Existing bills of materials are untouched — every line defaults to *Proportional*
- French translation
- Compatible with Odoo 18 (CE & EE)

**The problem it solves.** Odoo always scales components to the quantity to produce. A bill of materials expressed in square meters — 80 m² of turf plus 1 core for a 4 × 20 m roll — therefore asks for `0.5 core` when only 40 m² are manufactured, which no factory can issue. The same applies to labels, protective films, caps, strappings and slings: anything consumed once per unit produced.

---

### [`tt_mrp_backorder_traceability`](tt_mrp_backorder_traceability/) — Manufacturing Splits and Backorders Traceability

Link, filter and group manufacturing orders with their splits and backorders.

- Adds **Original MO**, **Derived From** and **Origin** (*Original*, *Split*, *Backorder*) on every manufacturing order
- A **Splits & Backorders** tab shows the whole chain in place, with its quantity totals, a progress bar, the source document and the lots consumed
- Search filters and grouping by **Original MO**, **Origin** and **Source Document** in the manufacturing orders list
- Covers every split path: split wizard, backorder wizard on validation, mass production by lot or serial number, subcontracting and the Shop Floor
- Rebuilds the chains of orders split before installation, without inventing a parentage the data cannot support
- Purely additive: no native behaviour is changed
- French translation
- Compatible with Odoo 18 (CE & EE)

**The problem it solves.** Splitting a manufacturing order, or closing one short, renames the orders `MO/0001-001`, `MO/0001-002`, … but stores no link between them. `procurement_group_id` cannot stand in, because make-to-order routes propagate a single group across unrelated orders — which is exactly what the native *Backorders* button relies on. `backorder_sequence` cannot either: it is a flat counter, computed per procurement group, that points at nothing. So there is no way to filter a family of splits in the list, nor to see from one order what became of the rest of the quantity.

---

## Compatibility

| Module | Odoo 18 |
|--------|:-------:|
| `tt_mrp_bom_fixed_quantity` | ✅ |
| `tt_mrp_backorder_traceability` | ✅ |

Backports for Odoo 17 and 19 are maintained in their respective branches once released.

---

## Installation

Clone the branch matching your Odoo version:

```bash
git clone -b 18.0 https://github.com/taghrastech/odoo-mrp.git
```

Then add the cloned folder to your `addons_path` in `odoo.conf` and install the module from the **Apps** menu.

---

## License

LGPL-3
