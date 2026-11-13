"""Run through Odoo shell. All fixture changes are rolled back, including releases."""
from datetime import timedelta
from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError

passed = []

def expect(label, condition):
    assert condition, label
    passed.append(label)

def denied(label, fn):
    try:
        with env.cr.savepoint():
            fn()
    except (AccessError, UserError, ValidationError):
        passed.append(label)
        return
    raise AssertionError('Unexpected permission: ' + label)

def user(login):
    return env['res.users'].search([('login', '=', login + '.kopitera')], limit=1)

try:
    author, reviewer, manager, staff, kitchen_head = [user(key) for key in ('headbar', 'reviewerbar', 'manager', 'stafbar', 'headkitchen')]
    assert all([author, reviewer, manager, staff, kitchen_head])
    Change = env['kopitera.master.change']
    Recipe = env['kopitera.recipe']
    menu = env.ref('kopitera_master.menu_kopi_susu')
    milk = env.ref('kopitera_master.ingredient_milk')
    original = menu.current_recipe_id

    def proposal(kind='menu', operation='create', **vals):
        data = {'kind': kind, 'operation': operation, 'division': 'bar', 'reason': 'Transaction-only master data test',
                'proposed_name': 'Integration Test Menu', 'unit': 'ml', 'usage': 'bar'}
        if kind == 'menu':
            data.update(category='non_coffee', allergens='-', availability='available')
        data.update(vals)
        return Change.with_user(author).create(data)

    def approve(record, date=None):
        record.with_user(author).action_submit()
        record.with_user(reviewer).write({'review_note': 'Checked'})
        record.with_user(reviewer).action_review()
        record.with_user(manager).write({'decision_note': 'Approved for transaction-only test', 'release_date': date or fields.Date.today()})
        record.with_user(manager).action_approve()

    new = proposal()
    denied('staff cannot create master proposals', lambda: Change.with_user(staff).create({'kind': 'menu', 'division': 'bar'}))
    denied('staff cannot read master proposals', lambda: new.with_user(staff).read(['reason']))
    denied('cross-division proposal denied', lambda: proposal(division='kitchen'))
    denied('cross-division direct read denied', lambda: new.with_user(kitchen_head).read(['reason']))
    denied('cannot forge released state', lambda: proposal(state='released'))
    denied('cannot forge comparison snapshot', lambda: new.write({'before_data': {'name': 'Fake'}}))
    context_record = Change.with_user(author).with_context(default_state='released', default_result_menu_id=menu.id).create({'kind': 'menu', 'division': 'bar'})
    expect('context cannot fabricate release', context_record.state == 'draft' and not context_record.result_menu_id)
    denied('other user cannot change draft', lambda: new.with_user(reviewer).write({'reason': 'Changed'}))
    denied('empty submission rejected', lambda: context_record.action_submit())
    original_menu_count = env['kopitera.menu'].search_count([])
    new.action_submit()
    expect('submission does not create live menu', env['kopitera.menu'].search_count([]) == original_menu_count)
    denied('self review rejected', lambda: new.action_review())
    denied('manager cannot replace head reviewer', lambda: new.with_user(manager).action_review())
    expect('review activity targets head reviewer only', set(new.activity_ids.user_id.ids) == {reviewer.id})
    denied('submitted data locked', lambda: new.write({'proposed_name': 'Changed'}))
    new.with_user(reviewer).write({'review_note': 'Please improve description'})
    new.with_user(reviewer).action_return()
    new.write({'description': 'Improved test description'})
    approve(new, fields.Date.today() + timedelta(days=2))
    expect('approval does not create live menu', env['kopitera.menu'].search_count([]) == original_menu_count)
    denied('head cannot release master data', lambda: new.action_release())
    denied('future release rejected', lambda: new.with_user(manager).action_release())
    new.sudo()._transition({'release_date': fields.Date.today()})
    new.with_user(manager).action_release()
    live = new.result_menu_id
    expect('release creates live menu and audit snapshot', live.name == 'Integration Test Menu' and new.after_data['name'] == live.name and new.state == 'released')
    denied('release cannot run twice', lambda: new.with_user(manager).action_release())
    denied('released proposal cannot be edited', lambda: new.write({'description': 'Changed'}))
    denied('manager cannot directly edit master menu', lambda: menu.with_user(manager).write({'name': 'Bypass'}))

    # Two independently approved edits must not silently overwrite each other.
    first = proposal(operation='update', menu_id=live.id, proposed_name='First Release', description='First')
    stale = proposal(operation='update', menu_id=live.id, proposed_name='Second Release', description='Second')
    approve(first)
    approve(stale)
    first.with_user(manager).action_release()
    expect('old and new values retained', first.before_data['name'] == 'Integration Test Menu' and first.after_data['name'] == 'First Release')
    denied('stale approved change cannot overwrite new data', lambda: stale.with_user(manager).action_release())
    stale.with_user(manager).action_request_update()
    approve(stale)
    stale.with_user(manager).action_release()
    expect('stale change can be reviewed and approved again', live.name == 'Second Release' and stale.before_data['name'] == 'First Release')

    rejected = proposal()
    rejected.action_submit()
    rejected.with_user(reviewer).write({'review_note': 'Checked'})
    rejected.with_user(reviewer).action_review()
    denied('rejection requires reason', lambda: rejected.with_user(manager).action_reject())
    rejected.with_user(manager).write({'decision_note': 'Not suitable'})
    rejected.with_user(manager).action_reject()
    expect('rejection creates no live master data', rejected.state == 'rejected' and not rejected.result_menu_id)

    ingr = proposal('ingredient', proposed_name='Unused Syrup')
    approve(ingr)
    ingr.with_user(manager).action_release()
    ingredient = ingr.result_ingredient_id
    expect('ingredient release creates correct unit and area', ingredient.unit == 'ml' and ingredient.division == 'bar')
    edit_ingr = proposal('ingredient', 'update', ingredient_id=ingredient.id, proposed_name='Renamed Syrup', unit='g')
    approve(edit_ingr)
    edit_ingr.with_user(manager).action_release()
    expect('unused ingredient name and unit may be changed', ingredient.name == 'Renamed Syrup' and ingredient.unit == 'g')
    in_use = proposal('ingredient', 'deactivate', ingredient_id=milk.id)
    denied('active recipe ingredient cannot be deactivated', lambda: in_use.action_submit())
    unit_change = proposal('ingredient', 'update', ingredient_id=milk.id, proposed_name=milk.name, usage='shared', unit='g')
    denied('referenced unit cannot change meaning of gramasi', lambda: unit_change.action_submit())

    # An ingredient can become used after deactivation was approved: recheck at release.
    deactivate = proposal('ingredient', 'deactivate', ingredient_id=ingredient.id)
    approve(deactivate)
    recipe = Recipe.with_user(author).create({
        'menu_id': live.id, 'reason': 'Ingredient dependency test', 'instructions': 'Example preparation',
        'line_ids': [(0, 0, {'ingredient_id': ingredient.id, 'quantity': 10})],
    })
    recipe.action_submit()
    recipe.with_user(reviewer).write({'review_note': 'Checked'})
    recipe.with_user(reviewer).action_review()
    recipe.with_user(manager).write({'decision_note': 'Approved', 'release_date': fields.Date.today()})
    recipe.with_user(manager).action_approve()
    recipe.with_user(manager).action_release()
    denied('ingredient usage is checked again at release', lambda: deactivate.with_user(manager).action_release())
    expect('blocked deactivation preserves live ingredient', ingredient.active and deactivate.state == 'approved')

    # Inactive menus disappear from staff even with active_test=False; recipes remain archived.
    pending_recipe = Recipe.browse(live.with_user(author).action_propose_recipe()['res_id'])
    pending_recipe.with_user(author).write({'reason': 'Pending while menu is removed'})
    deactivate_menu = proposal(operation='deactivate', menu_id=live.id)
    approve(deactivate_menu)
    deactivate_menu.with_user(manager).action_release()
    expect('menu deactivation archives current recipe', not live.active and not live.current_recipe_id and recipe.state == 'archived')
    denied('staff cannot read inactive menu even with explicit context', lambda: live.with_user(staff).with_context(active_test=False).read(['name']))
    denied('recipe cannot be submitted for inactive menu', lambda: pending_recipe.with_user(author).action_submit())
    deactivate.with_user(manager).action_release()
    expect('unused ingredient deactivation retains historical references', not ingredient.active and recipe.line_ids.ingredient_id == ingredient)

    # A pending recipe cannot introduce an ingredient that was deactivated after approval.
    extra = proposal('ingredient', proposed_name='Temporary Test Syrup')
    approve(extra)
    extra.with_user(manager).action_release()
    extra_ingr = extra.result_ingredient_id
    pending = Recipe.browse(menu.with_user(author).action_propose_recipe()['res_id'])
    pending.with_user(author).write({'reason': 'Live reference recheck', 'line_ids': [(0, 0, {'ingredient_id': extra_ingr.id, 'quantity': 5})]})
    pending.with_user(author).action_submit()
    denied('recipe review also limited to head roles', lambda: pending.with_user(manager).write({'review_note': 'Bypass'}))
    pending.with_user(reviewer).write({'review_note': 'Checked'})
    pending.with_user(reviewer).action_review()
    pending.with_user(manager).write({'decision_note': 'Approved', 'release_date': fields.Date.today()})
    pending.with_user(manager).action_approve()
    extra_deactivate = proposal('ingredient', 'deactivate', ingredient_id=extra_ingr.id)
    approve(extra_deactivate)
    extra_deactivate.with_user(manager).action_release()
    denied('approved recipe cannot publish inactive ingredient', lambda: pending.with_user(manager).action_release())
    pending.with_user(manager).action_request_update()
    expect('blocked recipe can return for revision', pending.state == 'revision' and menu.current_recipe_id == original)

    # Cross-division constraints for shared ingredients are checked with complete usage visibility.
    kitchen_menu = env.ref('kopitera_master.menu_nasi_goreng')
    kitchen_review = user('reviewerkitchen')
    kr = Recipe.browse(kitchen_menu.with_user(kitchen_head).action_propose_recipe()['res_id'])
    kr.with_user(kitchen_head).write({'reason': 'Shared ingredient fixture', 'line_ids': [(0, 0, {'ingredient_id': milk.id, 'quantity': 5})]})
    kr.with_user(kitchen_head).action_submit()
    kr.with_user(kitchen_review).write({'review_note': 'Checked'})
    kr.with_user(kitchen_review).action_review()
    kr.with_user(manager).write({'decision_note': 'Approved', 'release_date': fields.Date.today()})
    kr.with_user(manager).action_approve()
    kr.with_user(manager).action_release()
    narrow = proposal('ingredient', 'update', ingredient_id=milk.id, proposed_name=milk.name, unit='ml', usage='bar')
    denied('shared ingredient cannot exclude another active division', lambda: narrow.action_submit())
    for actor in (author, manager, staff):
        for model in ('kopitera.menu', 'kopitera.ingredient', 'kopitera.recipe'):
            env[model].with_user(actor).get_views([(False, 'form'), (False, 'tree')])
        if actor != staff:
            Change.with_user(actor).get_views([(False, 'form'), (False, 'tree'), (False, 'search')])
    passed.append('forms and lists load for author manager and staff')
    print('KOPITERA_MASTER_CHECKS_PASSED=' + str(len(passed)))
    for label in passed:
        print('PASS ' + label)
finally:
    env.cr.rollback()
