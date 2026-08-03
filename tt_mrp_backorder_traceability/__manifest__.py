# -*- coding: utf-8 -*-
{
    'name': "Manufacturing Splits and Backorders Traceability",
    'summary': "Link, filter and group manufacturing orders with their splits and backorders",
    'description': """
Manufacturing Backorder Traceability
====================================

When a manufacturing order is split or generates a backorder, Odoo names the new
orders ``MO/0001-001``, ``MO/0001-002``, ... but stores no relational link between
them. The only native hint is the procurement group, which is unreliable: MTO and
other pull routes propagate the same group across unrelated manufacturing orders.

This module adds a dependable link between a manufacturing order and every
backorder or split derived from it:

* **Original MO** - the root of the whole family, self-referenced on the root
  itself so grouping keeps the original and its backorders together.
* **Split From** - the immediate parent, to follow cascading splits.
* A consolidated **Split & Backorders** tab listing the entire family with its
  quantity totals, and a button to open each order.
* Search filters and a **Group by > Original MO** entry in the manufacturing
  orders list view.

Every split path is covered, including the split wizard, the backorder wizard on
validation, mass production by lot/serial number, subcontracting and the Shop
Floor.
""",
    'author': "TaghrasTech",
    'website': "https://github.com/taghrastech",
    'category': 'Manufacturing/Manufacturing',
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['mrp'],
    'data': [
        'views/mrp_production_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
