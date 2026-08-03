# -*- coding: utf-8 -*-

import logging
import math

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.addons.mrp.models.mrp_production import SIZE_BACK_ORDER_NUMERING

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    tt_split_root_id = fields.Many2one(
        'mrp.production', string="Original MO",
        copy=False, readonly=True, index='btree_not_null', check_company=True,
        help="Manufacturing order this one originates from, at the root of the whole "
             "chain of splits and backorders. It is set on the original order itself, "
             "so that grouping by this field keeps the original order together with "
             "everything derived from it. Empty when nothing was ever derived from "
             "the order.")
    tt_split_parent_id = fields.Many2one(
        'mrp.production', string="Derived From",
        copy=False, readonly=True, index='btree_not_null', check_company=True,
        help="Manufacturing order this one was directly derived from, by a split or "
             "as a backorder. Empty on the original order.")
    tt_split_child_ids = fields.One2many(
        'mrp.production', 'tt_split_parent_id', string="Derived MOs", readonly=True)
    tt_split_origin = fields.Selection(
        [('original', "Original"), ('split', "Split"),
         ('backorder', "Backorder"), ('unknown', "Undetermined")],
        string="Origin", copy=False, readonly=True, index='btree_not_null',
        help="How this manufacturing order came to be:\n"
             "- Original: the order the chain started from.\n"
             "- Split: created by deliberately splitting a planned quantity.\n"
             "- Backorder: created automatically for the quantity left to produce "
             "when an order was closed short.\n"
             "- Undetermined: derived from another order before this module was "
             "installed, when the distinction can no longer be recovered.")

    tt_split_family_ids = fields.Many2many(
        'mrp.production', string="Related MOs",
        compute='_compute_tt_split_family', readonly=False,
        help="Every manufacturing order of the same chain, the original one included.")
    tt_split_family_count = fields.Integer(
        string="Related MOs", compute='_compute_tt_split_family')
    tt_split_count = fields.Integer(
        string="Splits", compute='_compute_tt_split_family',
        help="Number of orders of the chain created by a split.")
    tt_backorder_count = fields.Integer(
        string="Backorders", compute='_compute_tt_split_family',
        help="Number of orders of the chain created as a backorder.")
    tt_split_family_qty_total = fields.Float(
        string="Total To Produce", compute='_compute_tt_split_family',
        digits='Product Unit of Measure',
        help="Quantity to produce over the whole chain, cancelled orders excluded.")
    tt_split_family_qty_produced = fields.Float(
        string="Total Produced", compute='_compute_tt_split_family',
        digits='Product Unit of Measure')
    tt_split_family_qty_remaining = fields.Float(
        string="Total Remaining", compute='_compute_tt_split_family',
        digits='Product Unit of Measure')
    tt_split_family_qty_cancelled = fields.Float(
        string="Total Cancelled", compute='_compute_tt_split_family',
        digits='Product Unit of Measure',
        help="Quantity carried by the cancelled orders of the chain.")
    tt_split_family_progress = fields.Float(
        string="Progress", compute='_compute_tt_split_family',
        help="Share of the chain already produced, cancelled orders excluded.")

    tt_consumed_lot_ids = fields.Many2many(
        'stock.lot', string="Consumed Lots", compute='_compute_tt_consumed_lot_ids',
        help="Lots and serial numbers this order consumes as components. Empty when "
             "none of the components are tracked.")
    tt_chain_consumed_lot_ids = fields.Many2many(
        'stock.lot', string="Chain Consumed Lots", compute='_compute_tt_split_family',
        help="Every lot and serial number consumed by the whole chain.")
    tt_is_self_consuming = fields.Boolean(
        string="Consumes Its Own Product", compute='_compute_tt_consumed_lot_ids',
        help="The order takes the very product it produces as a component, the way a "
             "cutting or portioning operation does. The consumed lots then describe "
             "where the produced material comes from, which is why they are only worth "
             "showing in that case: on a regular order they belong to other products.")

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    @api.depends('tt_split_root_id')
    def _compute_tt_split_family(self):
        # The family and its totals are computed together: making the totals depend
        # on ``tt_split_family_ids`` instead would force that field to be searchable,
        # which a non-stored computed relation cannot be.
        # Every order of a split chain shares the same product and unit of measure,
        # so the quantities can safely be summed as-is.
        for production in self:
            root = production.tt_split_root_id
            family = self.search(
                [('tt_split_root_id', '=', root.id)], order='backorder_sequence, id'
            ) if root.id else self.browse()
            cancelled = family.filtered(lambda mo: mo.state == 'cancel')
            active = family - cancelled
            qty_total = sum(active.mapped('product_qty'))
            qty_produced = sum(active.mapped('qty_produced'))
            production.tt_split_family_ids = family
            production.tt_split_family_count = len(family)
            production.tt_split_count = len(
                family.filtered(lambda mo: mo.tt_split_origin == 'split'))
            production.tt_backorder_count = len(
                family.filtered(lambda mo: mo.tt_split_origin == 'backorder'))
            production.tt_split_family_qty_total = qty_total
            production.tt_split_family_qty_produced = qty_produced
            production.tt_split_family_qty_remaining = max(qty_total - qty_produced, 0)
            production.tt_split_family_qty_cancelled = sum(cancelled.mapped('product_qty'))
            # A fully cancelled chain has nothing to produce: report no progress
            # rather than dividing by zero.
            production.tt_split_family_progress = (
                min(qty_produced / qty_total * 100, 100) if qty_total else 0)
            production.tt_chain_consumed_lot_ids = family._tt_get_consumed_lots()

    @api.depends('product_id', 'move_raw_ids.product_id', 'move_raw_ids.move_line_ids.lot_id')
    def _compute_tt_consumed_lot_ids(self):
        for production in self:
            components = production.move_raw_ids.filtered(lambda move: move.state != 'cancel')
            production.tt_consumed_lot_ids = components.move_line_ids.lot_id
            production.tt_is_self_consuming = production.product_id in components.product_id

    def _tt_get_consumed_lots(self):
        """Lots and serial numbers taken from the components of these orders.

        Cancelled component moves are left out: they carry no material.
        """
        return self.move_raw_ids.filtered(
            lambda move: move.state != 'cancel').move_line_ids.lot_id

    # ------------------------------------------------------------------
    # Split / backorder tracking
    # ------------------------------------------------------------------

    def _get_backorder_mo_vals(self):
        """Stamp the split links on every backorder generated from this order.

        The returned dictionary is used as the base values for all the backorders
        of ``self``, whichever code path triggered the split: split wizard,
        backorder wizard on validation, mass production by lot/serial number,
        subcontracting or the Shop Floor.
        """
        vals = super()._get_backorder_mo_vals()
        vals['tt_split_parent_id'] = self.id
        # Splitting an order that is already derived keeps the original root.
        vals['tt_split_root_id'] = self.tt_split_root_id.id or self.id
        vals['tt_split_origin'] = self.env.context.get('tt_split_origin', 'split')
        return vals

    def _split_productions(self, amounts=False, cancel_remaining_qty=False, set_consumed_qty=False):
        # Quantities given upfront means the split was deliberate: split wizard,
        # mass production by lot/serial number, one order per subcontracted line.
        # No quantity means the remainder of an order closed short, which is a
        # backorder: validation wizard, Shop Floor, subcontracting recording.
        origin = 'split' if amounts else 'backorder'
        productions = super(
            MrpProduction, self.with_context(tt_split_origin=origin)
        )._split_productions(
            amounts=amounts,
            cancel_remaining_qty=cancel_remaining_qty,
            set_consumed_qty=set_consumed_qty,
        )
        # Flag the original orders as the root of their own chain, so that grouping
        # by "Original MO" keeps them with everything derived from them. Only orders
        # that actually produced a new order are flagged: splitting with the
        # remaining quantity cancelled creates nothing at all.
        for production in self:
            if production.tt_split_root_id:
                continue
            if productions.filtered(lambda mo: mo.tt_split_parent_id == production):
                production.tt_split_root_id = production
                production.tt_split_origin = 'original'
        return productions

    def unlink(self):
        for production in self:
            children = self.search([
                ('tt_split_parent_id', '=', production.id),
                ('id', 'not in', self.ids),
            ])
            if production.tt_split_root_id != production:
                # Not a root: attach the orphans to the deleted order's own parent.
                children.tt_split_parent_id = production.tt_split_parent_id
                continue
            members = self.search([
                ('tt_split_root_id', '=', production.id),
                ('id', 'not in', self.ids),
            ], order='backorder_sequence, id')
            if not members:
                continue
            # Promote the oldest remaining member rather than dissolving the chain.
            new_root = members[0]
            members.tt_split_root_id = new_root
            children.tt_split_parent_id = new_root
            new_root.tt_split_parent_id = False
            new_root.tt_split_origin = 'original'
        return super().unlink()

    # ------------------------------------------------------------------
    # Backfill of orders split before this module was installed
    # ------------------------------------------------------------------

    @api.model
    def _tt_expected_backorder_suffix(self, sequence):
        """Rebuild the exact suffix ``mrp`` appends for a given backorder sequence.

        Mirrors ``_get_name_backorder``. Comparing the whole suffix as a string,
        rather than parsing trailing digits, is what makes the backfill safe: an
        order named ``MO-2026-0018`` coming from a custom sequence never matches
        the ``-018`` suffix a backorder sequence of 18 would have produced.
        """
        padding = max(SIZE_BACK_ORDER_NUMERING - 1 - int(math.log10(sequence)), 0)
        return "-" + "0" * padding + str(sequence)

    @api.model
    def _tt_backfill_split_roots(self):
        """Rebuild ``tt_split_root_id`` on orders split before install.

        Only the root is rebuilt. ``backorder_sequence`` is a flat counter that does
        not encode which order was split from which, nor whether an order came from
        a deliberate split or from a backorder: ``tt_split_parent_id`` is left empty
        and the origin is reported as ``unknown`` on historical data rather than
        guessed.

        Idempotent, and safe to run again: only orders with an empty root are
        considered.
        """
        productions = self.with_context(active_test=False).search([
            ('backorder_sequence', '>', 0),
            ('tt_split_root_id', '=', False),
        ])
        if not productions:
            return

        families = defaultdict(lambda: self.browse())
        unmatched = self.browse()
        for production in productions:
            suffix = self._tt_expected_backorder_suffix(production.backorder_sequence)
            if not production.name or not production.name.endswith(suffix):
                unmatched |= production
                continue
            base_name = production.name[:-len(suffix)]
            # Keying on the base name on top of the procurement group is what
            # neutralises the MTO pollution: unrelated orders sharing a procurement
            # group have different base names, so they never land in the same family.
            key = (production.procurement_group_id.id, base_name, production.product_id.id)
            families[key] |= production

        linked = 0
        for members in families.values():
            root = members.sorted(lambda mo: (mo.backorder_sequence, mo.id))[0]
            members.write({'tt_split_root_id': root.id, 'tt_split_origin': 'unknown'})
            root.write({'tt_split_origin': 'original'})
            linked += len(members)

        _logger.info(
            "tt_mrp_backorder_traceability: %s manufacturing orders linked into %s "
            "split families.", linked, len(families))
        if unmatched:
            _logger.warning(
                "tt_mrp_backorder_traceability: %s manufacturing orders carry a "
                "backorder sequence but their reference does not match the expected "
                "suffix (renamed manually?) and were left unlinked: %s",
                len(unmatched), ", ".join(unmatched.mapped('name')[:20]))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_tt_view_split_family(self):
        """Open the whole chain in a standalone list.

        Not wired to a smart button: the consolidated tab already shows the chain
        in place. Kept as an entry point for custom menus and server actions.
        """
        self.ensure_one()
        root = self.tt_split_root_id or self
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'name': _("Splits and backorders of %s", root.display_name),
            'domain': [('tt_split_root_id', '=', root.id)],
            'view_mode': 'list,form',
            'context': {'create': False},
        }
