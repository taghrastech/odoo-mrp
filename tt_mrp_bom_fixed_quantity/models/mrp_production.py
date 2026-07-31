# -*- coding: utf-8 -*-

from odoo import models
from odoo.tools import float_compare, float_is_zero


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _tt_fixed_qty_moves(self):
        """Component moves of these orders driven by a fixed quantity BoM line."""
        return self.move_raw_ids.filtered(
            lambda m: m.state not in ('done', 'cancel') and m._tt_is_fixed_qty_move())

    def _update_raw_moves(self, factor):
        """Keep fixed components out of the "Update quantity" rescaling.

        The standard blindly multiplies the current demand of every component
        move. Letting it run and putting the previous demand back also preserves
        a quantity the user typed by hand, which forcing the BoM value would not.
        """
        update_info = super()._update_raw_moves(factor)
        rescaled = []
        for move, old_qty, new_qty in update_info:
            if move._tt_is_fixed_qty_move():
                move.with_context(
                    do_not_unreserve=True, no_procurement=True,
                ).product_uom_qty = old_qty
            else:
                rescaled.append((move, old_qty, new_qty))
        # fixed moves did not move, they must not be logged as rescheduled either
        return rescaled

    def _split_productions(self, amounts=False, cancel_remaining_qty=False, set_consumed_qty=False):
        """Give every split order the full quantity of its fixed components.

        The standard rescales each move proportionally to the split amounts. A
        fixed component is consumed once per order - a backorder is a separate
        physical unit - so its demand is snapshotted before the split and put
        back on the original order and on each of its backorders.
        """
        fixed_qty_by_order = {
            production.id: {
                move.bom_line_id.id: move.product_uom_qty
                for move in production._tt_fixed_qty_moves()
            }
            for production in self
        }
        productions = super()._split_productions(
            amounts=amounts,
            cancel_remaining_qty=cancel_remaining_qty,
            set_consumed_qty=set_consumed_qty,
        )
        if not any(fixed_qty_by_order.values()):
            return productions

        # `_split_productions` returns [origin_1, its backorders..., origin_2, ...]
        # so the last order seen that belongs to `self` owns the ones that follow.
        origin_id = False
        for production in productions:
            if production in self:
                origin_id = production.id
            quantities = fixed_qty_by_order.get(origin_id) or {}
            for move in production._tt_fixed_qty_moves():
                qty = quantities.get(move.bom_line_id.id)
                if qty is None:
                    continue
                if float_compare(move.product_uom_qty, qty, precision_rounding=move.product_uom.rounding) != 0:
                    move.with_context(
                        do_not_unreserve=True, no_procurement=True,
                    ).product_uom_qty = qty
        return productions

    def _set_qty_producing(self, pick_manual_consumption_moves=True):
        """Consume a fixed component in full as soon as something is produced.

        The standard spreads the demand over the quantity being produced through
        `unit_factor`, which would give half a core for half a roll.
        """
        res = super()._set_qty_producing(pick_manual_consumption_moves)
        fixed_moves = self._tt_fixed_qty_moves()
        if not fixed_moves:
            return res

        # Guards mirrored from `mrp.production._set_qty_producing` in the `mrp`
        # module, so that a move the standard deliberately skipped stays
        # untouched. Review this block when upgrading Odoo.
        is_waiting = self.warehouse_id.manufacture_steps != 'mrp_one_step' and self.picking_ids.filtered(
            lambda p: p.picking_type_id == self.warehouse_id.pbm_type_id and p.state not in ('done', 'cancel'))
        remaining = self.qty_producing - self.qty_produced
        is_producing = float_compare(remaining, 0, precision_rounding=self.product_uom_id.rounding) > 0

        for move in fixed_moves:
            if is_waiting and move.product_id.tracking != 'none':
                continue
            # picked + manual means the user set the quantity himself
            if move.manual_consumption and move.picked:
                continue
            # sudo needed for portal users
            if move.sudo()._should_bypass_set_qty_producing():
                continue

            new_qty = move.product_uom_qty if is_producing else 0
            if float_compare(move.quantity, new_qty, precision_rounding=move.product_uom.rounding) != 0:
                move._set_quantity_done(new_qty)
            if (not move.manual_consumption or pick_manual_consumption_moves) and move.quantity:
                move.picked = True
        return res

    def _get_consumption_issues(self):
        """Do not report a fixed component as under-consumed on a partial production.

        The standard prorates the whole expectation by `qty_producing /
        product_qty`; the share it removed from the fixed components is given
        back before comparing again. A genuine over-consumption still shows up.
        """
        issues = super()._get_consumption_issues()
        if not issues:
            return issues

        corrected = []
        for order, product, consumed_qty, expected_qty in issues:
            rounding = product.uom_id.rounding
            fixed_moves = order.move_raw_ids.filtered(
                lambda m: m.product_id == product and m._tt_is_fixed_qty_move())
            if not fixed_moves or float_is_zero(order.product_qty, precision_rounding=order.product_uom_id.rounding):
                corrected.append((order, product, consumed_qty, expected_qty))
                continue

            ratio = order.qty_producing / order.product_qty
            expected_qty += sum(
                move.product_uom._compute_quantity(move.product_uom_qty, product.uom_id) * (1 - ratio)
                for move in fixed_moves
            )
            if float_compare(expected_qty, consumed_qty, precision_rounding=rounding) != 0:
                corrected.append((order, product, consumed_qty, expected_qty))
        return corrected
