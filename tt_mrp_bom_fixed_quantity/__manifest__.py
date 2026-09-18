# -*- coding: utf-8 -*-
{
    'name': "Fixed Quantity Components on Bills of Materials",
    'summary': "Consume a component with a fixed quantity, whatever the quantity produced",
    'description': """
Fixed Quantity Components
=========================

Odoo always scales the components of a bill of materials to the quantity to
produce. A bill of materials expressed in square meters - 80 m2 of turf plus
1 core for a 4 x 20 m roll - therefore asks for ``0.5 core`` when only 40 m2 are
manufactured, which no factory can issue.

This module adds a **Quantity Mode** on every bill of materials line:

* **Proportional** - the Odoo standard, the quantity follows the quantity to
  produce. This is the default, so existing bills of materials keep working
  exactly as before.
* **Fixed Quantity** - the quantity written on the line is consumed as is,
  whatever the quantity to produce.

It suits any component used once per unit produced: cores, labels, protective
films, caps, strappings, slings.

The fixed quantity is applied when the component moves are created, so
reservations, consumption and traceability are right from the start, without any
automated correction afterwards. Fixed components also keep their full quantity
on backorders, since each backorder is a separate physical unit.

The mode never locks the line: the quantity can still be changed by hand on the
manufacturing order - to declare a damaged component, for instance - and that
entry survives every later recomputation.
""",
    'author': "TaghrasTech",
    'website': 'https://github.com/taghrastech',
    'category': 'Manufacturing/Manufacturing',
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['mrp'],
    'data': [
        'views/mrp_bom_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
