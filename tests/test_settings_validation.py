import importlib.util
import json
import os
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch


def _load_settings_module(env: dict[str, str], config_exists: bool = False, config_data: dict | None = None):
    spec = importlib.util.spec_from_file_location('settings_under_test', Path('settings.py'))
    if spec is None or spec.loader is None:
        raise AssertionError('failed to load settings.py')

    module = importlib.util.module_from_spec(spec)

    with patch.dict(os.environ, env, clear=True), patch('os.path.exists', return_value=config_exists):
        if config_exists:
            mocked_open = mock_open(read_data=json.dumps(config_data or {}))
            with patch('builtins.open', mocked_open):
                spec.loader.exec_module(module)
        else:
            spec.loader.exec_module(module)

    return module


class TestSettingsValidation(unittest.TestCase):
    def test_missing_discord_token_raises_clear_error(self):
        with self.assertRaisesRegex(RuntimeError, 'Missing Discord token'):
            _load_settings_module(
                {
                    'DB_USER': 'user',
                    'DB_PASSWORD': 'password',
                    'DB_NAME': 'kbo',
                }
            )

    def test_environment_settings_load_without_config_file(self):
        module = _load_settings_module(
            {
                'DISCORD_TOKEN': 'discord-token',
                'DB_USER': 'user',
                'DB_PASSWORD': 'password',
                'DB_NAME': 'kbo',
            }
        )

        self.assertEqual(module.DISCORD_TOKEN, 'discord-token')
        self.assertEqual(module.DB_HOST, '127.0.0.1')
        self.assertEqual(module.DB_USER, 'user')
        self.assertEqual(module.DB_PASSWORD, 'password')
        self.assertEqual(module.DB_NAME, 'kbo')


if __name__ == '__main__':
    unittest.main()
