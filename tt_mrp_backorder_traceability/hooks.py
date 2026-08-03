# -*- coding: utf-8 -*-


def post_init_hook(env):
    env['mrp.production']._tt_backfill_split_roots()
