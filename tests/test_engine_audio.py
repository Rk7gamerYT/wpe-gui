import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtCore import QCoreApplication

from wpe_gui.engine import Engine
from wpe_gui.settings import Settings


class AudioSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(Path(self.temp.name) / 'settings.json')
        self.engine = Engine(self.settings, Mock())
        self.addCleanup(self.engine._reapply.stop)

    def test_audio_controls_restart_running_wallpapers_with_new_settings(self):
        for key, value in [('volume', 50), ('silent', True), ('autoMute', True), ('audioGain', 2)]:
            with self.subTest(key=key):
                self.engine._procs = {'DP-5': Mock()}
                self.engine._assignments = {'DP-5': '/wallpaper'}
                self.settings.set(key, value)
                self.assertTrue(self.engine._reapply.isActive())
                with patch.object(self.engine, '_stop_keys'), patch.object(self.engine, '_start') as start:
                    self.engine._reapply.stop()
                    self.engine._reapply_pending()
                start.assert_called_once_with('DP-5', '/wallpaper', planned={'DP-5'})
                self.assertEqual(self.settings.get(key), value)

    def test_unrelated_settings_do_not_restart_wallpapers(self):
        self.engine._procs = {'DP-5': Mock()}
        self.settings.set('startHidden', True)
        self.settings.set('assignments', {'DP-5': '/wallpaper'})
        self.assertFalse(self.engine._pending)
        self.assertFalse(self.engine._reapply.isActive())

    def test_audio_change_without_running_wallpaper_does_not_start_one(self):
        self.settings.set('volume', 25)
        self.assertFalse(self.engine._reapply.isActive())

    def test_reapply_preserves_power_saving_pause(self):
        self.engine._assignments = {'DP-5': '/wallpaper'}
        self.engine._power_paused = {'DP-5'}
        self.engine._paused = {'DP-5'}
        self.engine._pending = {'DP-5'}

        def stop(keys):
            self.engine._paused.difference_update(keys)
            self.engine._assignments.pop('DP-5')

        with patch.object(self.engine, '_stop_keys', side_effect=stop), \
             patch.object(self.engine, '_start'):
            self.engine._reapply_pending()
        self.assertEqual(self.engine._power_paused, {'DP-5'})
        self.engine._procs = {'DP-5': Mock()}
        with patch.object(self.engine, '_signal') as signal:
            self.engine._process_started('DP-5', self.engine._procs['DP-5'])
        self.assertTrue(signal.called)
        self.assertEqual(self.engine._paused, {'DP-5'})

    def test_each_monitor_uses_its_own_sound_options(self):
        from wpe_gui.properties import PropertiesStore
        props = PropertiesStore(Path(self.temp.name) / 'overrides.json')
        self.engine._properties = props
        screen = Mock()
        screen.name.return_value = 'DP-5'
        props.setEngineOption('/quiet', 'sound', 'muted')
        props.setEngineOption('/music', 'sound', 'enabled')
        props.setEngineOption('/music', 'volume', '0')
        self.settings.set('silent', True)
        with patch.object(self.engine, '_screens_by_name', return_value={'DP-5': screen}), \
             patch.object(self.engine, 'windowed', return_value=False), \
             patch('wpe_gui.engine.library.audio_responsive', return_value=False):
            muted = self.engine.build_args('/quiet', 'DP-5')
            audible = self.engine.build_args('/music', 'DP-5')
            self.assertIn('--silent', muted)
            self.assertNotIn('--silent', audible)
            self.assertEqual(audible[audible.index('--volume') + 1], '0')
            props.setEngineOption('/music', 'volume', '25')
            audible = self.engine.build_args('/music', 'DP-5')
            self.assertEqual(audible[audible.index('--volume') + 1], '25')
            props.setEngineOption('/music', 'sound', '')
            self.assertIn('--silent', self.engine.build_args('/music', 'DP-5'))

    def test_secondary_monitor_is_not_forced_silent(self):
        self.engine._properties.engine_options.return_value = {}
        self.engine._properties.engine_args.return_value = []
        screen = Mock()
        screen.name.return_value = 'DP-5'
        with patch('wpe_gui.engine.QProcess') as process, \
             patch.object(self.engine, '_screens_by_name', return_value={'DP-5': screen}), \
             patch.object(self.engine, 'windowed', return_value=False), \
             patch.object(self.engine, 'binary', return_value='/bin/true'), \
             patch('wpe_gui.engine.library.audio_responsive', return_value=True):
            self.engine._start('DP-5', '/music', planned={'HDMI-A-3', 'DP-5'})
            args = process.return_value.start.call_args.args[1]
            self.assertNotIn('--silent', args)
            env = process.return_value.setProcessEnvironment.call_args.args[0]
            self.assertEqual(env.value('WPE_AUDIO_PROCESSING'), '1')
        self.engine._procs.clear()

    def test_duplicate_wallpaper_has_only_one_audio_source(self):
        self.engine._properties.engine_options.return_value = {}
        self.engine._properties.engine_args.return_value = []
        screens = {}
        for name in ('HDMI-A-3', 'DP-5'):
            screen = Mock()
            screen.name.return_value = name
            screens[name] = screen
        with patch('wpe_gui.engine.QProcess') as process, \
             patch.object(self.engine, '_screens_by_name', return_value=screens), \
             patch.object(self.engine, 'windowed', return_value=False), \
             patch.object(self.engine, 'binary', return_value='/bin/true'), \
             patch('wpe_gui.engine.library.audio_responsive', return_value=True):
            first, second = Mock(), Mock()
            process.side_effect = [first, second]
            self.engine._start('HDMI-A-3', '/same-wallpaper')
            self.engine._start('DP-5', '/same-wallpaper')
            self.assertNotIn('--silent', first.start.call_args.args[1])
            self.assertIn('--silent', second.start.call_args.args[1])
            self.assertEqual(self.engine._audible_targets(), {'HDMI-A-3'})
            self.assertEqual(second.setProcessEnvironment.call_args.args[0].value('WPE_AUDIO_PROCESSING'), '1')
        self.engine._audio_sync.stop()
        self.engine._procs.clear()

    def test_different_wallpapers_keep_independent_audio(self):
        self.engine._procs = {'A': Mock(), 'B': Mock()}
        self.engine._assignments = {'A': '/one', 'B': '/two'}
        self.engine._audio_roles = {'A': True, 'B': True}
        self.assertEqual(self.engine._audible_targets(), {'A', 'B'})

    def test_audio_moves_to_unpaused_copy_and_stays_there_when_other_resumes(self):
        self.engine._procs = {'A': Mock(), 'B': Mock()}
        self.engine._assignments = {'A': '/same', 'B': '/same'}
        self.engine._audio_roles = {'A': True, 'B': False}
        self.engine._paused = {'A'}
        self.engine._power_paused = {'A'}
        self.assertEqual(self.engine._audible_targets(), {'B'})
        starts = []

        def stop(keys):
            for key in keys:
                self.engine._procs.pop(key)
                self.engine._assignments.pop(key)
                self.engine._audio_roles.pop(key)
                self.engine._paused.discard(key)

        def start(key, path, audio_owner):
            starts.append((key, audio_owner))
            self.engine._procs[key] = Mock()
            self.engine._assignments[key] = path
            self.engine._audio_roles[key] = audio_owner
            self.engine._update_pauses()

        with patch.object(self.engine, '_stop_keys', side_effect=stop), \
             patch.object(self.engine, '_start', side_effect=start), \
             patch.object(self.engine, '_signal'):
            self.engine._rebalance_audio()
        self.assertEqual(starts, [('A', False), ('B', True)])
        self.assertEqual(self.engine._paused, {'A'})
        self.engine._paused.clear()
        self.assertEqual(self.engine._audible_targets(), {'B'})

    def test_remaining_copy_takes_over_when_owner_stops(self):
        self.engine._procs = {'B': Mock()}
        self.engine._assignments = {'B': '/same'}
        self.engine._audio_roles = {'B': False}
        self.assertEqual(self.engine._audible_targets(), {'B'})

    def test_aliases_of_same_folder_are_deduplicated(self):
        real = Path(self.temp.name) / 'wallpaper'
        real.mkdir()
        alias = Path(self.temp.name) / 'alias'
        alias.symlink_to(real, target_is_directory=True)
        self.engine._procs = {'A': Mock(), 'B': Mock()}
        self.engine._assignments = {'A': str(real), 'B': str(alias)}
        self.assertEqual(len(self.engine._audible_targets()), 1)
