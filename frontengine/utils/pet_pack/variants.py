"""Bounded character-part choices shared by manifests and saved appearances."""
import re

_TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}')


def token(value):
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValueError('Invalid character variant identifier')
    return value


def checked_variants(value):
    if not isinstance(value, dict) or len(value) > 8:
        raise ValueError('At most eight character part selections')
    return {token(group): token(choice) for group, choice in value.items()}


def checked_groups(value):
    if not isinstance(value, dict) or len(value) > 8:
        raise ValueError('At most eight character part groups')
    result = {}
    for group, data in value.items():
        token(group)
        if not isinstance(data, dict) or set(data) != {'name', 'default', 'choices'}:
            raise ValueError('Invalid character part group')
        choices = data['choices']
        if not isinstance(choices, dict) or not 1 <= len(choices) <= 8:
            raise ValueError('Each character part needs 1..8 choices')
        for key in choices:
            token(key)
        token(data['default'])
        if data['default'] not in choices:
            raise ValueError('Unknown default character part')
        for label in (data['name'], *choices.values()):
            if (not isinstance(label, str) or not 1 <= len(label.strip()) <= 64
                    or len(label) > 64 or any(ord(char) < 32 for char in label)):
                raise ValueError('Invalid character part label')
        result[group] = {'name': data['name'], 'default': data['default'], 'choices': dict(choices)}
    return result
