# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.tools import float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _tt_is_fixed_qty_move(self):
        """Whether this component move is driven by a fixed quantity BoM line."""
        self.ensure_one()
        return bool(
            self.raw_material_production_id
            and not self.additional
            and self.bom_line_id.tt_qty_type == 'fixed'
            # a component whose unit was changed by hand is left to the standard
            and self.product_uom == self.bom_line_id.product_uom_id
        )

    @api.depends('bom_line_id.tt_qty_type')
    def _compute_should_consume_qty(self):
        """A fixed component is expected in full as soon as something is produced."""
        super()._compute_should_consume_qty()
        for move in self:
            if not move._tt_is_fixed_qty_move():
                continue
            # nothing left to produce, keep the zero computed by the standard
            if float_is_zero(move.should_consume_qty, precision_rounding=move.product_uom.rounding):
                continue
            move.should_consume_qty = move.product_uom_qty
