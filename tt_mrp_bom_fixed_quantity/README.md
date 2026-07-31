# Fixed Quantity Components on Bills of Materials

Consume a bill of materials component with a **fixed quantity**, whatever the quantity produced.

## Why

Odoo always scales the components of a bill of materials to the quantity to produce:

```
component qty = (qty to produce / BoM qty) x BoM line qty
```

Take a roll of synthetic turf, 4 × 20 m, described in square meters:

| Bill of materials (80 m²) | Quantity |
|---|---|
| Turf | 80 m² |
| Core | 1 unit |

Manufacturing 40 m² applies a ratio of `40 / 80 = 0.5`, so Odoo asks for **half a core** — which no factory can issue. A roll always needs one whole core, whatever its length.

The same applies to any component consumed once per unit produced: labels, protective films, caps, strappings, slings.

## What it does

The module adds a **Quantity Mode** on every bill of materials line:

| Mode | Behaviour |
|---|---|
| **Proportional** | The Odoo standard: the quantity follows the quantity to produce. This is the default, so existing bills of materials keep working exactly as before. |
| **Fixed Quantity** | The quantity written on the line is consumed as is, whatever the quantity to produce. |

With the core set to *Fixed Quantity*:

| Manufactured | Turf | Core |
|---:|---:|---:|
| 20 m² | 20 m² | **1** |
| 35 m² | 35 m² | **1** |
| 40 m² | 40 m² | **1** |
| 60 m² | 60 m² | **1** |
| 80 m² | 80 m² | **1** |

## How it works

The fixed quantity is applied while the component moves are created, not corrected afterwards. The module extends `mrp.bom.line._prepare_line_done_values()`, the single point of the bill of materials explosion that decides the quantity of a component line. The value it returns lands verbatim in `product_uom_qty` of the `stock.move`.

Quantities are therefore right from the very first write, which keeps reservations, consumption and traceability consistent. There is no scheduled action and no post-creation fix-up.

The remaining overrides only neutralise the proportional recomputations that the standard applies afterwards:

| Situation | Behaviour for a fixed component |
|---|---|
| *Update quantity* wizard | The quantity is left untouched |
| Manufacturing order split / backorder | Each order gets the full fixed quantity, since each is a separate physical unit |
| Partial production | The component is expected and consumed in full |
| Strict consumption check | No false alert; a genuine over-consumption is still reported |

## Manual entry stays possible

The mode drives the computed value, it never locks the line. The quantity can still be changed by hand on the manufacturing order — to declare a damaged component, for instance — and that entry survives the *Update quantity* wizard and the creation of backorders.

No constraint, no `readonly` and no forced value is added on the component quantity.

## Compatibility

- Odoo 18, Community and Enterprise
- Multi-level bills of materials, product variants, kits (phantom) and subcontracting
- Existing bills of materials are strictly unaffected: every line defaults to *Proportional*

## Known limitations

- A manufacturing order producing more than the nominal quantity of the bill of materials still consumes the fixed quantity only once. Adjust the component quantity by hand when this happens.
- The **Bill of Materials Overview** report recomputes its quantities inline instead of exploding the bill of materials, so it keeps displaying the proportional value for fixed components.

## License

LGPL-3
