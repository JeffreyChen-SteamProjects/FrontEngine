from datetime import datetime
from types import SimpleNamespace

from frontengine.ui.main_ui import FrontEngineMainUI
from frontengine.utils.actions.action_registry import Action, ActionRegistry
from frontengine.utils.rules.rule_engine import RuleEngineService, RuleTracker, normalize_rule, normalize_rules


def _rule(label, priority=0, cooldown=0, **extra):
    return {'label': label, 'action': 'hide_all', 'when': {'apps': 'code'},
            'priority': priority, 'cooldown': cooldown, **extra}


def test_priorities_preserve_ties_and_cooldown_never_delays_consumed_edges():
    clock = [0.0]
    tracker = RuleTracker(clock=lambda: clock[0])
    rules = [_rule('High', 10, 100), _rule('Low', -10), _rule('Tie', -10)]
    context = {'app': 'code'}
    assert [row['label'] for row in tracker.tick(rules, context)] == ['Low', 'Tie', 'High']
    assert tracker.tick(rules, context) == []
    tracker.tick(rules, {'app': 'other'})
    clock[0] = 29
    assert [row['label'] for row in tracker.tick(rules, context)] == ['Low', 'Tie']
    assert tracker.decisions[-1]['status'] == 'cooldown'
    assert tracker.decisions[-1]['remaining'] == 71
    clock[0] = 101
    assert tracker.tick(rules, context) == [], 'cooldown expiry must not overwrite manual changes'
    tracker.tick(rules, {'app': 'other'})
    assert [row['label'] for row in tracker.tick(rules, context)] == ['Low', 'Tie', 'High']


def test_identity_normalization_bounds_and_duplicate_labels():
    rule = normalize_rule(_rule('Same', id='1' * 32))
    assert normalize_rule(rule) == rule
    assert normalize_rule(_rule('Bad', cooldown=-1)) is None
    assert normalize_rule(_rule('Bad', priority=True)) is None
    assert normalize_rule(_rule('Bad', cooldown=86401)) is None
    rules = [rule, normalize_rule(_rule('Same', id='2' * 32))]
    tracker = RuleTracker()
    assert len(tracker.tick(rules, {'app': 'code'})) == 2
    assert len(normalize_rules(rules + [rules[0]])) == 2
    assert len(normalize_rules([_rule(str(index)) for index in range(205)])) == 200


def test_preview_does_not_consume_edges_and_failed_actions_get_receipts():
    rules = [_rule('Fails'), _rule('Next', priority=1)]
    service = RuleEngineService(lambda: rules, lambda: {'app': 'code', 'now': datetime(2026, 10, 7, 19, 30)})
    registry = ActionRegistry()
    registry.register(Action('hide_all', 'label', 'Hide', lambda _value: False))
    window = SimpleNamespace(action_registry=registry, rule_engine_service=service)
    service.rule_fired.connect(lambda rule: FrontEngineMainUI._on_rule_fired(window, rule))
    assert all(row['matches'] and not row['active'] for row in service.preview())
    assert not service.history and not service.tracker.active('Fails')
    assert len(service.poll_once()) == 2
    assert [record['status'] for record in service.history] == ['failed', 'failed']
    assert all(record['context']['app'] == 'code' for record in service.history)
    assert service.preview()[0]['active']
    assert service.poll_once() == []


def test_dialog_round_trip_preserves_identity_hidden_conditions_and_priority(monkeypatch):
    from frontengine.ui.dialog import rules_dialog as module
    monkeypatch.setattr(module, 'current_rules', lambda: [])
    service = RuleEngineService(context_provider=lambda: {'app': 'code'})
    dialog = module.RulesDialog()
    dialog.service = service
    entry = normalize_rule(_rule('Work', priority=3, cooldown=60,
                                  when={'apps': 'code', 'from': '09:00', 'to': '17:00',
                                        'fullscreen': False, 'battery': True, 'idle_minutes': 5}))
    dialog.add_row(entry)
    assert dialog.rules() == [entry]
    dialog.preview_conditions()
    assert not service.history and not service.tracker.active('Work')
    assert 'Work' in dialog.diagnostics.toPlainText()
    dialog.table.item(0, module._COLUMN_COOLDOWN).setText('invalid')
    dialog.accept()
    assert dialog.status.text()
    dialog.close()


def test_nested_dispatch_receipts_and_history_capacity():
    context = {'app': 'code'}
    service = RuleEngineService(lambda: [_rule('Nested')], lambda: context)

    def execute(rule):
        if rule['_receipt'] == 1:
            context['app'] = 'other'
            service.poll_once()
            context['app'] = 'code'
            service.poll_once()
            service.record_execution(rule, True)
        else:
            service.record_execution(rule, False, 'second dispatch')

    service.rule_fired.connect(execute)
    service.poll_once()
    assert [entry['status'] for entry in service.history] == ['executed', 'failed']
    for _ in range(205):
        context['app'] = 'other'
        service.poll_once()
        context['app'] = 'code'
        service.poll_once()
    assert len(service.history) == 200


def test_dialog_failed_save_restores_original_settings(monkeypatch):
    from frontengine.ui.dialog import rules_dialog as module
    original = [_rule('Original')]
    monkeypatch.setitem(module.user_setting_dict, module.SETTING_KEY, original)
    monkeypatch.setattr(module, 'current_rules', lambda: [])
    monkeypatch.setattr(module, 'write_user_setting',
                        lambda: (_ for _ in ()).throw(OSError('disk full')))
    dialog = module.RulesDialog()
    dialog.add_row(normalize_rule(_rule('New')))
    dialog.accept()
    assert module.user_setting_dict[module.SETTING_KEY] is original
    assert 'disk full' in dialog.status.text()
    dialog.close()
