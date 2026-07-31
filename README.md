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

## Compatibility

| Module | Odoo 18 |
|--------|:-------:|
| `tt_mrp_bom_fixed_quantity` | ✅ |

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
