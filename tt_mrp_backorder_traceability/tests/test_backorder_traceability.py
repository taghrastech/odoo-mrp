# -*- coding: utf-8 -*-

from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestSplitTraceability(TestMrpCommon):

    def _split(self, production, amounts):
        return production._split_productions({production: amounts})

    def _mo_with_tracked_component(self, qty_final, component_lots):
        """A confirmed MO whose single component is lot tracked and reserved.

        :param dict component_lots: lot name -> quantity to put in stock.
        :return: (production, lots recordset)
        """
        component = self.env['product.product'].create({
            'name': 'Tracked Component',
            'is_storable': True,
            'tracking': 'lot',
        })
        finished = self.env['product.product'].create({
            'name': 'Tracked Finished',
            'is_storable': True,
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {'product_id': component.id, 'product_qty': 1})],
        })
        production = self.env['mrp.production'].create({
            'product_id': finished.id,
            'bom_id': bom.id,
            'product_qty': qty_final,
        })
        production.action_confirm()

        lots = self.env['stock.lot']
        for lot_name, quantity in component_lots.items():
            lot = self.env['stock.lot'].create({
                'name': lot_name,
                'product_id': component.id,
            })
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': component.id,
                'lot_id': lot.id,
                'inventory_quantity': quantity,
                'location_id': production.location_src_id.id,
            })._apply_inventory()
            lots |= lot
        production.action_assign()
        return production, lots

    # ------------------------------------------------------------------
    # A - orders that must be linked
    # ------------------------------------------------------------------

    def test_split_three_ways(self):
        """A1: splitting in three links the original and both backorders."""
        production = self.generate_mo(qty_final=9)[0]
        productions = self._split(production, [3, 3, 3])
        self.assertEqual(len(productions), 3)

        self.assertEqual(production.tt_split_root_id, production,
                         "The original order must be its own root.")
        self.assertFalse(production.tt_split_parent_id,
                         "The original order has no parent.")
        for backorder in productions - production:
            self.assertEqual(backorder.tt_split_root_id, production)
            self.assertEqual(backorder.tt_split_parent_id, production)
        self.assertEqual(production.tt_split_origin, 'original')
        self.assertEqual((productions - production)[0].tt_split_origin, 'split',
                         "Quantities given upfront means a deliberate split.")
        self.assertEqual(production.tt_split_count, 2)
        self.assertEqual(production.tt_backorder_count, 0)

    def test_cascade_split_keeps_initial_root(self):
        """A11: splitting a backorder keeps the very first order as root."""
        production = self.generate_mo(qty_final=10)[0]
        first_level = self._split(production, [5, 5])
        backorder = (first_level - production)[0]

        second_level = self._split(backorder, [2, 3])
        grandchild = (second_level - backorder)[0]

        self.assertEqual(grandchild.tt_split_root_id, production,
                         "The root must stay the initial order, not the intermediate one.")
        self.assertEqual(grandchild.tt_split_parent_id, backorder,
                         "The parent must be the order it was actually split from.")

    def test_backorder_on_validation(self):
        """A3: producing less than planned links the generated backorder."""
        production = self.generate_mo(qty_final=5)[0]
        production_form = Form(production)
        production_form.qty_producing = 2
        production = production_form.save()

        action = production.button_mark_done()
        wizard = Form(self.env['mrp.production.backorder'].with_context(**action['context'])).save()
        wizard.action_backorder()

        backorder = self.env['mrp.production'].search(
            [('tt_split_parent_id', '=', production.id)])
        self.assertEqual(len(backorder), 1)
        self.assertEqual(backorder.tt_split_root_id, production)
        self.assertEqual(production.tt_split_root_id, production)
        self.assertEqual(backorder.tt_split_origin, 'backorder',
                         "Closing an order short creates a backorder, not a split.")
        self.assertEqual(production.tt_backorder_count, 1)
        self.assertEqual(production.tt_split_count, 0)

    def test_split_and_backorder_are_distinguished(self):
        """A chain mixing both kinds reports each of them separately."""
        production = self.generate_mo(qty_final=10)[0]
        split_family = self._split(production, [6, 4])
        self.assertEqual(production.tt_split_count, 1)
        self.assertEqual(production.tt_backorder_count, 0)

        # Close the first order short: its remainder becomes a backorder.
        production_form = Form(production)
        production_form.qty_producing = 2
        production = production_form.save()
        action = production.button_mark_done()
        wizard = Form(self.env['mrp.production.backorder'].with_context(**action['context'])).save()
        wizard.action_backorder()

        production.invalidate_recordset()
        self.assertEqual(production.tt_split_count, 1)
        self.assertEqual(production.tt_backorder_count, 1)
        self.assertEqual(production.tt_split_family_count, 3,
                         "The total counts the original plus everything derived.")
        self.assertEqual(
            production.tt_split_family_count,
            1 + production.tt_split_count + production.tt_backorder_count,
            "Total and breakdown must stay consistent.")
        origins = production.tt_split_family_ids.mapped('tt_split_origin')
        self.assertEqual(sorted(origins), ['backorder', 'original', 'split'])
        self.assertEqual(production.tt_split_family_ids & split_family, split_family,
                         "The earlier split stays part of the chain.")

    # ------------------------------------------------------------------
    # B - orders that must stay unlinked
    # ------------------------------------------------------------------

    def test_no_backorder_leaves_order_unlinked(self):
        """B2: closing without a backorder must not flag the order."""
        production = self.generate_mo(qty_final=5)[0]
        production_form = Form(production)
        production_form.qty_producing = 2
        production = production_form.save()

        action = production.button_mark_done()
        wizard = Form(self.env['mrp.production.backorder'].with_context(**action['context'])).save()
        wizard.action_close_mo()

        self.assertFalse(production.tt_split_root_id,
                         "No backorder was created, the order belongs to no family.")
        self.assertFalse(production.tt_split_parent_id)

    def test_shared_procurement_group_stays_unlinked(self):
        """B3: the bug this module fixes.

        Pull routes such as MTO propagate a single procurement group across
        unrelated manufacturing orders. Those orders must never be reported as
        belonging to the same split family.
        """
        first = self.generate_mo(qty_final=3)[0]
        second = self.generate_mo(qty_final=4)[0]
        second.procurement_group_id = first.procurement_group_id

        self.assertEqual(first.procurement_group_id, second.procurement_group_id)
        self.assertFalse(first.tt_split_root_id)
        self.assertFalse(second.tt_split_root_id)
        self.assertEqual(first.tt_split_family_count, 0)
        self.assertEqual(second.tt_split_family_count, 0)
        # The native counter, by contrast, does report them as related.
        self.assertEqual(first.mrp_production_backorder_count, 2)

    def test_duplicate_is_standalone(self):
        """B4: duplicating a split order must not join its family."""
        production = self.generate_mo(qty_final=6)[0]
        self._split(production, [3, 3])

        duplicate = production.copy()
        self.assertFalse(duplicate.tt_split_root_id)
        self.assertFalse(duplicate.tt_split_parent_id)

    # ------------------------------------------------------------------
    # Consolidated family data
    # ------------------------------------------------------------------

    def test_family_data_from_any_member(self):
        """The whole family and its totals are readable from any member."""
        production = self.generate_mo(qty_final=10)[0]
        productions = self._split(production, [4, 3, 3])
        backorder = (productions - production)[-1]

        for member in productions:
            self.assertEqual(member.tt_split_family_ids, productions)
            self.assertEqual(member.tt_split_family_count, 3)
            self.assertEqual(member.tt_split_family_qty_total, 10)

        self.assertEqual(backorder.tt_split_family_qty_produced, 0)
        self.assertEqual(backorder.tt_split_family_qty_remaining, 10)
        self.assertEqual(backorder.tt_split_family_qty_cancelled, 0)

    def test_family_totals_exclude_cancelled(self):
        """Cancelled members are reported apart from the active quantities."""
        production = self.generate_mo(qty_final=10)[0]
        productions = self._split(production, [4, 6])
        backorder = (productions - production)[0]
        backorder.action_cancel()

        self.assertEqual(production.tt_split_family_qty_total, 4)
        self.assertEqual(production.tt_split_family_qty_cancelled, 6)
        self.assertEqual(production.tt_split_family_count, 2,
                         "A cancelled order stays part of the family.")

    def test_family_list_is_editable(self):
        """The dialog opened from the consolidated tab must be editable.

        A computed relation is readonly for the web client unless declared
        otherwise, which would open the row dialog in readonly mode. The field is
        writable and the ORM applies the update command straight to the related
        order, so edits made in the dialog are saved.
        """
        field = self.env['mrp.production'].fields_get(['tt_split_family_ids'])
        self.assertFalse(field['tt_split_family_ids']['readonly'],
                         "A readonly relation would open the dialog in readonly mode.")

        production = self.generate_mo(qty_final=8)[0]
        productions = self._split(production, [4, 4])
        backorder = (productions - production)[0]

        production.write({
            'tt_split_family_ids': [(1, backorder.id, {'date_start': '2026-09-01 08:00:00'})],
        })
        backorder.invalidate_recordset()
        self.assertEqual(str(backorder.date_start), '2026-09-01 08:00:00')

    def test_family_list_forbids_adding_or_removing(self):
        """Chain membership is not something the user may edit by hand.

        Membership comes from Original MO on each order, never from this list, so
        linking or unlinking a row here would be meaningless. On a many2many those
        two controls are driven by ``link``/``unlink``, which default to enabled:
        ``create``/``delete`` on the list alone would leave both visible.
        """
        view = self.env.ref('mrp.mrp_production_form_view')
        arch = self.env['mrp.production'].get_view(view.id, 'form')['arch']
        self.assertIn("'link': False", arch)
        self.assertIn("'unlink': False", arch)

    def test_family_list_has_no_button_of_its_own(self):
        """Rows are opened by the standard x2many dialog, not by a custom button.

        That dialog is editable and carries the web client's expand-to-page button;
        an action dialog opened by a button of ours would lose it.
        """
        view = self.env.ref('mrp.mrp_production_form_view')
        arch = self.env['mrp.production'].get_view(view.id, 'form')['arch']
        self.assertNotIn('action_tt_open_mo', arch)

    # ------------------------------------------------------------------
    # Material traceability
    # ------------------------------------------------------------------

    def test_consumed_lots_are_reported(self):
        production, lots = self._mo_with_tracked_component(6, {'SRC-A': 10})
        self.assertEqual(production.tt_consumed_lot_ids, lots)

    def test_consumed_lots_ignore_cancelled_moves(self):
        production, lots = self._mo_with_tracked_component(6, {'SRC-A': 10})
        self.assertEqual(production.tt_consumed_lot_ids, lots)

        production.move_raw_ids._action_cancel()
        production.invalidate_recordset()
        self.assertFalse(production.tt_consumed_lot_ids,
                         "A cancelled component move carries no material.")

    def test_self_consuming_is_detected(self):
        """Cutting-like orders eat their own product; regular ones do not."""
        regular, dummy = self._mo_with_tracked_component(6, {'SRC-A': 10})
        self.assertFalse(regular.tt_is_self_consuming,
                         "Components are other products: nothing to highlight.")

        cutting = self.generate_mo(qty_final=6)[0]
        cutting.write({'move_raw_ids': [(0, 0, {
            'product_id': cutting.product_id.id,
            'product_uom': cutting.product_uom_id.id,
            'product_uom_qty': 6,
            'name': cutting.product_id.display_name,
            'location_id': cutting.location_src_id.id,
            'location_dest_id': cutting.production_location_id.id,
        })]})
        cutting.invalidate_recordset()
        self.assertTrue(cutting.tt_is_self_consuming,
                        "The order takes the very product it produces.")

    def test_self_consuming_ignores_cancelled_components(self):
        cutting = self.generate_mo(qty_final=6)[0]
        cutting.write({'move_raw_ids': [(0, 0, {
            'product_id': cutting.product_id.id,
            'product_uom': cutting.product_uom_id.id,
            'product_uom_qty': 6,
            'name': cutting.product_id.display_name,
            'location_id': cutting.location_src_id.id,
            'location_dest_id': cutting.production_location_id.id,
        })]})
        cutting.invalidate_recordset()
        self.assertTrue(cutting.tt_is_self_consuming)

        cutting.move_raw_ids.filtered(
            lambda m: m.product_id == cutting.product_id)._action_cancel()
        cutting.invalidate_recordset()
        self.assertFalse(cutting.tt_is_self_consuming,
                         "A cancelled component is no longer consumed.")

    def test_consumed_lots_empty_without_tracking(self):
        """The common case must stay untouched: no tracking, no lots, no noise."""
        production = self.generate_mo(qty_final=4)[0]
        self.assertFalse(production.tt_consumed_lot_ids)
        self.assertFalse(production.tt_chain_consumed_lot_ids)

    def test_chain_consumed_lots_aggregate_every_member(self):
        """Read from any member, the chain reports the material of them all."""
        production, lots = self._mo_with_tracked_component(6, {'SRC-A': 4, 'SRC-B': 4})
        self.assertEqual(len(production.tt_consumed_lot_ids), 2,
                         "The order consumes both source lots before the split.")

        productions = self._split(production, [3, 3])
        for member in productions:
            self.assertEqual(member.tt_chain_consumed_lot_ids, lots,
                             "The chain aggregates the lots of all its members.")

    # ------------------------------------------------------------------
    # Chain progress
    # ------------------------------------------------------------------

    def test_progress_of_a_fresh_chain_is_zero(self):
        production = self.generate_mo(qty_final=9)[0]
        self._split(production, [3, 3, 3])
        self.assertEqual(production.tt_split_family_progress, 0)

    def test_progress_never_divides_by_zero(self):
        """A fully cancelled chain has nothing left to produce."""
        production = self.generate_mo(qty_final=8)[0]
        productions = self._split(production, [4, 4])
        productions.action_cancel()
        production.invalidate_recordset()

        self.assertEqual(production.tt_split_family_qty_total, 0)
        self.assertEqual(production.tt_split_family_progress, 0)

    # ------------------------------------------------------------------
    # Source document
    # ------------------------------------------------------------------

    def test_source_document_is_groupable(self):
        """The native search view offers origin as a search field, not a grouping."""
        view = self.env.ref('mrp.view_mrp_production_filter')
        arch = self.env['mrp.production'].get_view(view.id, 'search')['arch']
        self.assertIn("'group_by': 'origin'", arch)

    def test_source_document_is_shared_by_the_chain(self):
        production = self.generate_mo(qty_final=6)[0]
        production.origin = 'SO-TEST-42'
        productions = self._split(production, [3, 3])

        self.assertEqual(productions.mapped('origin'), ['SO-TEST-42'] * 2,
                         "Backorders inherit the source document of the original.")

    # ------------------------------------------------------------------
    # C - edge cases
    # ------------------------------------------------------------------

    def test_root_deletion_promotes_new_root(self):
        """C1: deleting the root re-anchors the family instead of dissolving it."""
        production = self.generate_mo(qty_final=9)[0]
        productions = self._split(production, [3, 3, 3])
        backorders = productions - production

        production.action_cancel()
        production.unlink()

        new_root = backorders.sorted(lambda mo: (mo.backorder_sequence, mo.id))[0]
        self.assertEqual(new_root.tt_split_root_id, new_root)
        self.assertFalse(new_root.tt_split_parent_id)
        for backorder in backorders:
            self.assertEqual(backorder.tt_split_root_id, new_root)
        self.assertEqual(new_root.tt_split_family_count, 2)

    # ------------------------------------------------------------------
    # Backfill of pre-existing data
    # ------------------------------------------------------------------

    def test_backfill_rebuilds_families(self):
        production = self.generate_mo(qty_final=9)[0]
        productions = self._split(production, [3, 3, 3])
        productions.write({'tt_split_root_id': False, 'tt_split_parent_id': False,
                           'tt_split_origin': False})

        self.env['mrp.production']._tt_backfill_split_roots()

        for member in productions:
            self.assertEqual(member.tt_split_root_id, production)
        self.assertFalse(production.tt_split_parent_id,
                         "Parentage is not guessed on historical data.")
        self.assertEqual(production.tt_split_origin, 'original')
        self.assertEqual((productions - production).mapped('tt_split_origin'),
                         ['unknown', 'unknown'],
                         "Split vs backorder cannot be recovered from history.")

    def test_backfill_ignores_lookalike_reference(self):
        """A custom sequence ending in digits must never be split into a family.

        ``MO-2026-0018`` with a backorder sequence of 18 would yield the suffix
        ``-018``, which does not match the reference: the order must be left alone.
        """
        first = self.generate_mo(qty_final=3)[0]
        second = self.generate_mo(qty_final=3)[0]
        group = first.procurement_group_id
        second.procurement_group_id = group
        first.write({'name': 'MO-2026-0018', 'backorder_sequence': 18})
        second.write({'name': 'MO-2026-0019', 'backorder_sequence': 19})

        self.env['mrp.production']._tt_backfill_split_roots()

        self.assertFalse(first.tt_split_root_id)
        self.assertFalse(second.tt_split_root_id)

    def test_backfill_is_idempotent(self):
        production = self.generate_mo(qty_final=6)[0]
        productions = self._split(production, [3, 3])

        self.env['mrp.production']._tt_backfill_split_roots()

        for member in productions:
            self.assertEqual(member.tt_split_root_id, production)
