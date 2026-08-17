import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class K1ReceiveOnlyStaticTests(unittest.TestCase):
    def test_added_receive_features_have_persistent_master_switch_with_legacy_on_default(self):
        header = source("App/app/rx_feature_state.h")
        state = source("App/app/rx_feature_state.c")
        self.assertIn("RX_FEATURE_STATE_IsEnabled", header)
        self.assertIn("RX_FEATURE_STATE_SetEnabled", header)
        self.assertIn("RX_FEATURE_FLAG_ENABLED", state)
        self.assertIn("#define RX_FEATURE_VERSION           2u", state)
        self.assertIn("RX_FEATURE_LEGACY_VERSION", state)
        self.assertIn("sFlags = RX_FEATURE_FLAG_ENABLED", state)
        self.assertIn("block[2] == RX_FEATURE_LEGACY_VERSION", state)

    def test_master_switch_is_exposed_in_radio_menu_and_resets_active_scan_range(self):
        menu_header = source("App/ui/menu.h")
        menu_ui = source("App/ui/menu.c")
        menu_text = source("App/ui/menu_text.h")
        menu = source("App/app/menu.c")
        self.assertIn("MENU_RX_EXT", menu_header)
        self.assertIn("WRX_MENU_LABEL_RX_EXT", menu_ui)
        self.assertIn('"RXExt"', menu_text)
        self.assertIn("MENU_RX_EXT", menu_ui)
        self.assertIn("case MENU_RX_EXT", menu)
        self.assertIn("RX_FEATURE_STATE_SetEnabled", menu)
        self.assertIn("RX_BAND_PRESETS_Reset();", menu)
        self.assertIn("gScanRangeStart = 0", menu)
        self.assertIn("gScanRangeStop = 0", menu)

    def test_master_switch_gates_all_added_feature_runtime_seams(self):
        state = source("App/app/rx_feature_state.c")
        presets = source("App/app/rx_band_presets.c")
        skips = source("App/app/rx_scan_skip.c")
        radio = source("App/radio.c")
        action = source("App/app/action.c")
        ui = source("App/ui/main.c")
        self.assertIn("RX_FEATURE_STATE_IsEnabled()", state)
        self.assertIn("RX_FEATURE_STATE_IsEnabled()", presets)
        self.assertIn("RX_FEATURE_STATE_IsEnabled()", skips)
        self.assertIn("RADIO_BandwidthToFilter", action)
        self.assertNotIn("RX_FEATURE_STATE_IsEnabled() && vfoInfo->WIDE_PLUS", ui)

    def test_build_outputs_use_project_names(self):
        cmake = source("CMakePresets.json")
        lists = source("CMakeLists.txt")

        self.assertIn('"TARGET": "wrx-jp"', cmake)
        self.assertNotIn('"name": "Custom"', cmake)
        self.assertNotIn('"TARGET": "uv-k1-custom"', cmake)
        self.assertNotIn('set(EDITION_STRING "Custom")', lists)
        self.assertNotIn('"TARGET": "f4hwn.', cmake)
        self.assertIn("set(CMAKE_PROJECT_NAME wrx-jp)", lists)
        self.assertNotIn("Development build", lists)
        for preset in ("default", "Bandscope", "Broadcast", "Basic", "RescueOps", "Game", "Fusion"):
            self.assertNotIn(f'"name": "{preset}"', cmake)

    def test_dedicated_preset_keeps_rx_only_and_japanese_flags(self):
        cmake = source("CMakePresets.json")
        self.assertIn('"name": "JpRxOnly"', cmake)
        for flag in (
            '"ENABLE_RX_ONLY": true',
            '"ENABLE_JAPANESE": true',
            '"ENABLE_FMRADIO": true',
            '"ENABLE_TX1750": false',
            '"ENABLE_AIRCOPY": false',
            '"ENABLE_DTMF_CALLING": false',
        ):
            self.assertIn(flag, cmake)
        self.assertIn('"VERSION_STRING_2": "v5.8.0J5"', cmake)
        self.assertIn('"EDITION_STRING": "JP-RX-Only"', cmake)
        for flag in (
            '"ENABLE_FEAT_F4HWN_SCAN_PROGRESS": true',
            '"ENABLE_FEAT_F4HWN_SCAN_FASTER": true',
            '"ENABLE_FEAT_F4HWN_SCAN_RSSI": true',
            '"ENABLE_FEAT_F4HWN_SCAN_SUBAUDIBLE": true',
            '"ENABLE_FEAT_F4HWN_AUDIO": true',
            '"ENABLE_FEAT_F4HWN_SPECTRUM": false',
            '"ENABLE_FEAT_F4HWN_CA": false',
        ):
            self.assertIn(flag, cmake)

    def test_rx_only_policy_is_enforced_at_cmake_boundary(self):
        root = source("CMakeLists.txt")
        app = source("App/CMakeLists.txt")

        self.assertIn("set(ENABLE_RX_ONLY ON CACHE BOOL", root)
        for feature in (
            "ENABLE_AIRCOPY",
            "ENABLE_ALARM",
            "ENABLE_DTMF_CALLING",
            "ENABLE_FEAT_F4HWN_BEAM",
            "ENABLE_FEAT_F4HWN_FOXHUNT",
            "ENABLE_FEAT_F4HWN_RXTX_LOG",
            "ENABLE_FEAT_F4HWN_RX_TX_TIMER",
            "ENABLE_FEAT_F4HWN_SPECTRUM",
            "ENABLE_FEAT_F4HWN_GAME",
            "ENABLE_FEAT_F4HWN_K5VIEWER",
            "ENABLE_FEAT_F4HWN_CA",
            "ENABLE_NOAA",
            "ENABLE_VOICE",
            "ENABLE_REDUCE_LOW_MID_TX_POWER",
            "ENABLE_TX1750",
            "ENABLE_TX_WHEN_AM",
            "ENABLE_VOX",
        ):
            self.assertIn(feature, root)

        for source_file in (
            "app/aircopy.c",
            "ui/aircopy.c",
            "app/beam.c",
            "app/foxhunt.c",
            "app/rxtx_log.c",
        ):
            self.assertNotIn(source_file, app)

    def test_rx_driver_guards_rf_tx_primitives(self):
        driver = source("App/driver/bk4829.c")
        guarded = (
            "BK4819_PlaySingleTone",
            "BK4819_PrepareTransmit",
            "BK4819_TxOn_Beep",
            "BK4819_EnterDTMF_TX",
            "BK4819_ExitDTMF_TX",
            "BK4819_EnableTXLink",
            "BK4819_PlayDTMF",
            "BK4819_PlayDTMFString",
            "BK4819_TransmitTone",
            "BK4819_PlayCDCSSTail",
            "BK4819_PlayCTCSSTail",
            "BK4819_SendFSKData",
            "BK4819_PlayRoger",
            "BK4819_Enable_AfDac_DiscMode_TxDsp",
            "BK4819_PlayDTMFEx",
        )
        for name in guarded:
            start = driver.index(f"void {name}(")
            end = driver.find("\nvoid ", start + 1)
            body = driver[start:] if end < 0 else driver[start:end]
            self.assertIn("#ifdef ENABLE_RX_ONLY", body, name)

    def test_fm_radio_is_fixed_to_domestic_receive_range(self):
        driver = source("App/driver/bk1080.c")
        settings = source("App/settings.c")
        fm = source("App/app/fm.c")
        self.assertIn("band = 1;", driver)
        self.assertIn("return 760;", driver)
        self.assertIn("return 950;", driver)
        self.assertIn("gEeprom.FM_Band = 1;", settings)
        self.assertIn("one fixed 76-95 MHz receive band", fm)

    def test_k1_receive_bandwidth_has_three_modes_and_preserves_step_choices(self):
        ui = source("App/ui/main.c")
        action = source("App/app/action.c")
        radio = source("App/radio.c")
        menu = source("App/ui/menu.c")
        settings = source("App/settings.c")
        frequencies = source("App/frequencies.c")
        self.assertIn('"W", "N", "N-"', ui)
        self.assertIn('"W",\n    "N",\n    "N-"', menu)
        self.assertIn("BANDWIDTH_NARROWER", action)
        self.assertIn("RADIO_BandwidthToFilter", radio)
        self.assertIn("RADIO_BANDWIDTH_EXT_MARKER", settings)
        self.assertIn("[STEP_6_25kHz]  = 625", frequencies)
        self.assertIn("[STEP_20kHz]    = 2000", frequencies)

    def test_auto_squelch_recalibrates_after_fm_configuration(self):
        radio = source("App/radio.c")
        self.assertIn(
            "if (RX_FEATURE_STATE_IsAutoSquelch() && pInfo->Modulation == MODULATION_FM)",
            radio,
        )
        self.assertIn("RX_FEATURE_STATE_RequestAutoSquelch();", radio)

    def test_scan_paths_include_harmonic_verification_and_fm_css_guard(self):
        scanner = source("App/app/scanner.c")
        main = source("App/app/main.c")

        self.assertIn("SCANNER_ShouldVerifyVhfSecondHarmonic", scanner)
        self.assertIn("SCANNER_HandleFrequencyVerification", scanner)
        self.assertIn("scanVerifyFundamentalRssi - harmonicRssi >= margin", scanner)
        self.assertIn("gRxVfo->Modulation != MODULATION_FM", main)
        self.assertLess(main.index("gRxVfo->Modulation != MODULATION_FM"), main.index("SCANNER_Start(true)"))

    def test_fm_gain_and_trimmed_squelch_use_driver_seams(self):
        state = source("App/app/rx_feature_state.c")
        driver = source("App/driver/bk4829.c")
        header = source("App/driver/bk4819.h")

        self.assertIn("BK4819_SetAGCFixedIndex", header)
        self.assertIn("BK4819_SetAGCFixedIndex", driver)
        self.assertIn("BK4819_SetAGCFixedIndex(-4)", state)
        self.assertIn("BK4819_SetAGCFixedIndex(-3)", state)
        self.assertIn("rssiMin", state)
        self.assertIn("noiseMax", state)
        self.assertIn("glitchMin", state)
        self.assertIn("/ 6u", state)

    def test_audio_scope_scan_watch_and_menu_help_are_receive_only_additions(self):
        cmake = source("CMakePresets.json")
        ui = source("App/ui/main.c")
        app = source("App/app/app.c")
        scanner = source("App/app/chFrScanner.c")
        menu = source("App/ui/menu.c")
        menu_text = source("App/ui/menu_text.h")

        self.assertIn('"ENABLE_FEAT_F4HWN_AUDIO_SCOPE": true', cmake)
        self.assertIn("REG_64", ui)
        self.assertIn("not an FFT", ui)
        self.assertIn("RX_FEATURE_STATE_IsEnabled()", app)
        self.assertIn("watchChannel", scanner)
        self.assertIn("UI_MENU_GetRxHelp", menu)
        self.assertIn('#define WRX_MENU_HELP_SQL              "AUTO=measure noise"', menu_text)

    def test_band_state_uses_k1_external_flash_map(self):
        state = source("App/app/rx_feature_state.c")
        self.assertIn("RX_FEATURE_GLOBAL_BASE       0x00B000u", state)
        self.assertIn("RX_FEATURE_BANK_BASE         0x00B100u", state)
        self.assertIn("RX_FEATURE_WIDE_PLUS_BASE   0x00B500u", state)
        self.assertIn("MR_CHANNELS_MAX", state)
        self.assertIn("PY25Q16_WriteBuffer", state)
        self.assertIn("if (channel >= MR_CHANNELS_MAX)", state)

    def test_presets_cover_k1_extended_receive_use_cases(self):
        presets = source("App/app/rx_band_presets.c")
        for name in (
            '"18M HAM"',
            '"21M HAM"',
            '"24M HAM"',
            '"50M HAM"',
            '"351 DIGI"',
            '"FM BC"',
            '"118 NAV"',
            '"124 NAV"',
        ):
            self.assertIn(name, presets)
        self.assertIn('{"18M HAM",    1806800u,  1816800u', presets)
        self.assertIn('{"21M HAM",    2100000u,  2145000u', presets)
        self.assertIn('{"24M HAM",    2489000u,  2499000u', presets)
        self.assertIn('{"50M HAM",    5000000u,  5400000u', presets)
        self.assertIn('{"FM BC",      7600000u,  9500000u', presets)
        self.assertIn('{"118 NAV",   11800000u,  12140000u', presets)
        self.assertIn('{"124 NAV",   12400000u,  13000000u', presets)
        self.assertIn("RX_BAND_PRESET_COUNT", presets)
        self.assertIn("for (uint32_t frequency = preset->lower;; frequency += preset->step)", presets)
        self.assertIn("gTxVfo->freq_config_TX.Frequency = preset->lower", presets)

    def test_japanese_renderer_and_menu_labels_are_wired(self):
        font = source("App/japanese_font.c")
        helper = source("App/ui/helper.c")
        menu = source("App/ui/menu.c")
        menu_text = source("App/ui/menu_text.h")
        menu_header = source("App/ui/menu.h")
        self.assertIn("gFontBigJapanese", font)
        self.assertIn("gFontSmallJapanese", font)
        self.assertIn("gFontBigJapanese[code - 0x7F]", helper)
        self.assertIn("gFontSmallJapanese[code - 0x7F]", helper)
        self.assertIn("0x80, 0x81, 'D', 'C', 'S'", menu_text)
        self.assertIn("0x95, 0x96", menu_text)
        self.assertIn("0xD8, 0xBD, 0xC4", menu_text)
        self.assertIn("gSubMenu_RXMode[3]", menu_header)

    def test_extended_japanese_font_covers_large_long_vowel_and_added_terms(self):
        font_header = source("App/font.h")
        font = source("App/japanese_font.c")
        helper = source("App/ui/helper.c")
        self.assertIn("#define FONT_CODE_MAX 0xFF", font_header)
        self.assertIn("[0xE0 - 0x7F]", font)
        self.assertIn("// ー", font)
        self.assertIn(
            "[0xE0 - 0x7F] = {0x80,0x80,0x80,0x80,0x80,0x80,0x80,0x00,0x00,0x00,0x00,0x00,0x00,0x00}",
            font,
        )
        self.assertIn("glyph data itself decides which rows are lit", helper)
        self.assertNotIn("FONT_BIG_JAPANESE_RENDER_SHIFT", helper)
        self.assertIn("[0xFF - 0x7F]", font)
        self.assertIn("code <= FONT_CODE_MAX", helper)

    def test_rx_only_menu_uses_expanded_japanese_labels(self):
        menu = source("App/ui/menu.c")
        menu_text = source("App/ui/menu_text.h")
        self.assertIn("0x80, 0x81, 0xE1, 0xE2", menu_text)
        self.assertIn("0xEE, 0xFF", menu_text)
        self.assertIn("0xE3, 0xE4", menu_text)
        self.assertIn("0xE5, 0xE6", menu_text)
        self.assertIn("0xE7, 0xE8", menu_text)
        self.assertIn("0xE9, 0xEA", menu_text)
        self.assertIn("0xEB, 0xEC", menu_text)
        self.assertIn("0x93, 0x94", menu_text)
        menu_list = menu.split("const t_menu_item MenuList[]", 1)[1].split("};", 1)[0]
        self.assertIn("#ifndef ENABLE_RX_ONLY", menu_list)
        self.assertIn("MENU_BATCAL", menu_list)
        self.assertIn("FIRST_HIDDEN_MENU_ITEM = MENU_BATCAL", menu)

    def test_status_messages_keep_safety_text_and_localize_battery_labels(self):
        main = source("App/ui/main.c")
        self.assertIn('[VFO_STATE_BAT_LOW]="\\x8F\\xF7 LOW"', main)
        self.assertIn('[VFO_STATE_TX_DISABLE]="TX DISABLE"', main)
        self.assertIn('[VFO_STATE_VOLTAGE_HIGH]="\\x8F\\x92 HIGH"', main)

    def test_ptt_is_monitor_and_single_vfo_is_enforced(self):
        generic = source("App/app/generic.c")
        common = source("App/app/common.c")
        functions = source("App/functions.c")
        menu = source("App/ui/menu.c")
        self.assertIn("ACTION_Monitor()", generic)
        self.assertIn("COMMON_SwitchVFOs", common)
        self.assertIn("return;", common)
        self.assertIn("RADIO_SetVfoState(VFO_STATE_TX_DISABLE);", functions)
        self.assertIn('"SINGLE"', menu)
        self.assertIn("const char auto_name[] = {0xEB, 0xEC, 0};", menu)


if __name__ == "__main__":
    unittest.main()
