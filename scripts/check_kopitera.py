"""Execute inside `odoo shell -d odoo_app --no-http` via stdin.

Checks use a single transaction; all test mutations are rolled back.
Requires setup_kopitera_demo.py to have created local test users.
"""
from datetime import timedelta
from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from psycopg2 import IntegrityError

passed = []

def user(key):
    return env['res.users'].search([('login', '=', key + '.kopitera')], limit=1)

def denied(label, fn):
    try:
        with env.cr.savepoint():
            fn()
    except (AccessError, UserError, ValidationError, IntegrityError):
        passed.append(label)
        return
    raise AssertionError('Action unexpectedly allowed: ' + label)

try:
    author = user('headbar')
    reviewer = user('reviewerbar')
    manager = user('manager')
    staff = user('stafbar')
    kitchen = user('stafkitchen')
    assert all([author, reviewer, manager, staff, kitchen])
    menu = env.ref('kopitera_master.menu_kopi_susu')
    old_current = menu.current_recipe_id
    Recipe = env['kopitera.recipe']
    action = menu.with_user(author).action_propose_recipe()
    proposal = Recipe.browse(action['res_id'])
    proposal.with_user(author).write({'reason': 'Transaction-only integration test'})
    denied('staff cannot create', lambda: Recipe.with_user(staff).create({'menu_id': menu.id}))
    denied('cannot forge publication', lambda: Recipe.with_user(author).create({'menu_id': menu.id, 'state': 'published'}))
    denied('cannot forge state via write', lambda: proposal.with_user(author).write({'state': 'published'}))
    denied('cannot forge division via write', lambda: proposal.with_user(author).write({'division': 'kitchen'}))
    forged = Recipe.with_user(author).with_context(default_state='published', default_version=99).create({'menu_id': menu.id})
    assert forged.state == 'draft' and forged.version == 0
    passed.append('RPC context cannot bypass workflow defaults')
    denied('context cannot attach lines to published recipe', lambda: env['kopitera.recipe.line'].with_user(author).with_context(default_recipe_id=old_current.id).create({'ingredient_id': env.ref('kopitera_master.ingredient_milk').id, 'quantity': 50}))
    denied('non-author cannot edit draft', lambda: proposal.with_user(reviewer).write({'reason': 'Changed'}))
    denied('zero quantity rejected', lambda: proposal.line_ids[:1].with_user(author).write({'quantity': 0}))
    assert not Recipe.with_user(staff).search_count([('id', '=', proposal.id)])
    assert not env['kopitera.recipe.line'].with_user(staff).search_count([('recipe_id', '=', proposal.id)])
    passed.append('draft and its lines hidden from staff')
    proposal.with_user(author).action_submit()
    denied('self-review rejected', lambda: proposal.with_user(author).action_review())
    denied('submitted recipe locked', lambda: proposal.with_user(author).write({'instructions': 'Changed'}))
    denied('submitted lines locked', lambda: proposal.line_ids[:1].with_user(author).write({'quantity': 50}))
    proposal.with_user(reviewer).write({'review_note': 'Revise first'})
    proposal.with_user(reviewer).action_return()
    assert proposal.state == 'revision'
    proposal.with_user(author).write({'instructions': 'Revised steps for transaction-only test'})
    proposal.with_user(author).action_submit()
    proposal.with_user(reviewer).write({'review_note': 'Checked'})
    proposal.with_user(reviewer).action_review()
    denied('head cannot approve', lambda: proposal.with_user(author).action_approve())
    denied('staff cannot release', lambda: proposal.with_user(staff).action_release())
    denied('approval requires decision and date', lambda: proposal.with_user(manager).action_approve())
    proposal.with_user(manager).write({'decision_note': 'Approved for test', 'release_date': fields.Date.today() + timedelta(days=2)})
    proposal.with_user(manager).action_approve()
    denied('future publication rejected', lambda: proposal.with_user(manager).action_release())
    assert menu.current_recipe_id == old_current
    passed.append('approval leaves current recipe unchanged')
    # Backdate only in the transaction-only test fixture; regular users cannot change an approved date.
    proposal.sudo()._transition({'release_date': fields.Date.today()})
    proposal.with_user(manager).action_release()
    assert proposal.state == 'published' and menu.current_recipe_id == proposal
    assert old_current.state == 'archived' and proposal.version == old_current.version + 1
    passed.append('release archives old version and activates next version')
    assert Recipe.with_user(staff).search_count([('id', '=', proposal.id)]) == 1
    assert not Recipe.with_user(staff).search_count([('id', '=', old_current.id)])
    assert not Recipe.with_user(kitchen).search_count([('id', '=', proposal.id)])
    denied('cross-division direct read denied', lambda: proposal.with_user(kitchen).read(['instructions']))
    passed.append('staff sees only current version in own division')
    denied('published recipe cannot be edited', lambda: proposal.with_user(author).write({'reason': 'Changed'}))
    denied('published lines cannot be deleted', lambda: proposal.line_ids[:1].with_user(manager).unlink())
    denied('repeat release rejected', lambda: proposal.with_user(manager).action_release())
    # Another proposal exercises final rejection and its mandatory reason.
    rejected = Recipe.browse(menu.with_user(author).action_propose_recipe()['res_id'])
    rejected.with_user(author).write({'reason': 'Rejection test'})
    rejected.with_user(author).action_submit()
    rejected.with_user(reviewer).write({'review_note': 'Checked'})
    rejected.with_user(reviewer).action_review()
    denied('rejection requires a reason', lambda: rejected.with_user(manager).action_reject())
    rejected.with_user(manager).write({'decision_note': 'Rejected for test'})
    rejected.with_user(manager).action_reject()
    assert rejected.state == 'rejected' and menu.current_recipe_id == proposal
    passed.append('rejection leaves published data unchanged')
    print('KOPITERA_CHECKS_PASSED=' + str(len(passed)))
    for label in passed:
        print('PASS ' + label)
finally:
    env.cr.rollback()
