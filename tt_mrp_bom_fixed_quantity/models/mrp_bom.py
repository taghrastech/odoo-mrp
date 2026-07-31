# -*- coding: utf-8 -*-

from odoo import fields, models


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    tt_qty_type = fields.Selection(
        selection=[
            ('proportional', 'Proportional'),
            ('fixed', 'Fixed Quantity'),
        ],
        string='Quantity Mode',
        default='proportional',
        required=True,
        copy=True,
        help="Proportional: the quantity follows the quantity to produce, as Odoo "
             "does by default.\n"
             "Fixed Quantity: the quantity written on this line is consumed as is, "
             "whatever the quantity to produce. Use it for a component consumed "
             "once per unit produced, such as a core, a label or a wrapping film.")

    def _prepare_line_done_values(self, quantity, product, original_quantity, parent_line, boms_done):
        """Ignore the manufacturing ratio on a fixed quantity line.

        This is the single place where the exploded quantity of a leaf line is
        decided, so overriding it covers manufacturing orders, kits and work
        orders at once. The value returned here is what lands verbatim in the
        ``product_uom_qty`` of the component move, and both quantities are
        expressed in ``product_uom_id``, so no unit conversion is needed.
        """
        values = super()._prepare_line_done_values(
            quantity, product, original_quantity, parent_line, boms_done)
        if self.tt_qty_type == 'fixed':
            values['qty'] = self.product_qty
        return values
