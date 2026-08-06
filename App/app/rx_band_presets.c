#include "app/rx_band_presets.h"

#include <stddef.h>

#include "app/action.h"
#include "app/app.h"
#include "app/chFrScanner.h"
#ifdef ENABLE_FMRADIO
    #include "app/fm.h"
#endif
#include "audio.h"
#include "external/printf/printf.h"
#include "frequencies.h"
#include "misc.h"
#include "radio.h"
#include "settings.h"
#include "ui/helper.h"

const RX_BandPreset_t gRxBandPresets[RX_BAND_PRESET_COUNT] = {
    {"AIR VHF",   11800000u, 13700000u,  2500u, MODULATION_AM, BANDWIDTH_NARROW},
    {"AIR UHF",   22500000u, 40000000u, 10000u, MODULATION_AM, BANDWIDTH_NARROW},
    {"TOKUSHO",   42205000u, 42230000u,  1250u, MODULATION_FM, BANDWIDTH_NARROW},
    {"FIRE",      46635000u, 46655000u,  1250u, MODULATION_FM, BANDWIDTH_NARROW},
    {"140 HAM",   14400000u, 14600000u,  2000u, MODULATION_FM, BANDWIDTH_WIDE},
    {"430 HAM",   43000000u, 44000000u,  2000u, MODULATION_FM, BANDWIDTH_WIDE},
    {"MAR SHIP",  15602500u, 15742500u,  2500u, MODULATION_FM, BANDWIDTH_WIDE},
    {"MAR SHORE", 16062500u, 16202500u,  2500u, MODULATION_FM, BANDWIDTH_WIDE},
    {"18M HAM",    1806800u,  1816800u,   100u, MODULATION_USB, BANDWIDTH_WIDE},
    {"21M HAM",    2100000u,  2145000u,   100u, MODULATION_USB, BANDWIDTH_WIDE},
    {"24M HAM",    2489000u,  2499000u,   100u, MODULATION_USB, BANDWIDTH_WIDE},
    {"50M HAM",    5000000u,  5400000u,  2500u, MODULATION_FM, BANDWIDTH_WIDE},
    {"351 DIGI",  35125000u, 35131250u,  1250u, MODULATION_FM, BANDWIDTH_NARROW},
    {"FM BC",      7600000u,  9500000u, 10000u, MODULATION_FM, BANDWIDTH_WIDE},
    {"118 NAV",   11800000u,  12140000u, 2500u, MODULATION_AM, BANDWIDTH_NARROW},
    {"124 NAV",   12400000u,  13000000u, 2500u, MODULATION_AM, BANDWIDTH_NARROW},
};

static bool sOpen;
static bool sApplied;
static uint8_t sSelection;
static uint8_t sAppliedPreset;

static bool IsValid(const RX_BandPreset_t *preset)
{
    if (preset == NULL || preset->lower >= preset->upper || preset->step == 0 ||
        ((preset->upper - preset->lower) % preset->step) != 0)
        return false;

    /* Validate every candidate, not just the endpoints: BK4829 has a
     * hardware gap and a future preset must not scan through it. */
    for (uint32_t frequency = preset->lower;; frequency += preset->step)
    {
        if (RX_freq_check(frequency) != 0)
            return false;
        if (frequency == preset->upper)
            return true;
    }
}

static void Beep(const bool error)
{
    gBeepToPlay = error ? BEEP_500HZ_60MS_DOUBLE_BEEP_OPTIONAL : BEEP_1KHZ_60MS_OPTIONAL;
}

static void Close(void)
{
    sOpen = false;
    gUpdateDisplay = true;
}

static void Apply(const bool startScan)
{
    const RX_BandPreset_t *preset = &gRxBandPresets[sSelection];
    if (gEeprom.DUAL_WATCH != DUAL_WATCH_OFF ||
        gEeprom.CROSS_BAND_RX_TX != CROSS_BAND_OFF || !IsValid(preset))
    {
        Beep(true);
        Close();
        return;
    }

    RADIO_SelectVfos();
    gTxVfo->freq_config_RX.Frequency = preset->lower;
    gTxVfo->freq_config_TX.Frequency = preset->lower;
    gTxVfo->Band = FREQUENCY_GetBand(preset->lower);
    gTxVfo->Modulation = (ModulationMode_t)preset->modulation;
    gTxVfo->WIDE_PLUS = false;
    gTxVfo->CHANNEL_BANDWIDTH = preset->bandwidth;
    gTxVfo->STEP_SETTING = STEP_12_5kHz;
    for (uint8_t i = 0; i < STEP_N_ELEM; ++i)
        if (gStepFrequencyTable[i] == preset->step)
            gTxVfo->STEP_SETTING = (STEP_Setting_t)i;
    gTxVfo->StepFrequency = preset->step;

    gScanRangeStart = preset->lower;
    gScanRangeStop = preset->upper;
    sApplied = true;
    sAppliedPreset = sSelection;
    RADIO_ConfigureSquelchAndOutputPower(gTxVfo);
    RADIO_SetModulation(gTxVfo->Modulation);
    RADIO_SetupRegisters(true);
    Beep(false);
    Close();
    if (startScan)
        ACTION_Scan(false);
}

void RX_BAND_PRESETS_Open(void)
{
    if (!IS_FREQ_CHANNEL(gTxVfo->CHANNEL_SAVE) || gScanStateDir != SCAN_OFF ||
        gScanRangeStart != 0 || gTxVfo->FrequencyReverse ||
        gEeprom.DUAL_WATCH != DUAL_WATCH_OFF ||
        gEeprom.CROSS_BAND_RX_TX != CROSS_BAND_OFF
#ifdef ENABLE_FMRADIO
        || gFmRadioMode
#endif
    )
    {
        Beep(true);
        return;
    }

    sSelection = 0;
    sOpen = true;
    Beep(false);
    gUpdateDisplay = true;
}

void RX_BAND_PRESETS_Reset(void)
{
    sOpen = false;
    sApplied = false;
    gUpdateDisplay = true;
}

bool RX_BAND_PRESETS_IsOpen(void)
{
    return sOpen;
}

bool RX_BAND_PRESETS_IsApplied(void)
{
    return sApplied && gScanRangeStart != 0 && sAppliedPreset < RX_BAND_PRESET_COUNT &&
           gScanRangeStart == gRxBandPresets[sAppliedPreset].lower &&
           gScanRangeStop == gRxBandPresets[sAppliedPreset].upper;
}

bool RX_BAND_PRESETS_HandleKey(const KEY_Code_t key, const bool pressed, const bool held)
{
    if (!sOpen)
        return false;

    switch (key)
    {
        case KEY_UP:
            if (pressed)
                sSelection = (sSelection + 1u) % RX_BAND_PRESET_COUNT;
            break;
        case KEY_DOWN:
            if (pressed)
                sSelection = sSelection == 0 ? RX_BAND_PRESET_COUNT - 1u : sSelection - 1u;
            break;
        case KEY_MENU:
            if (!pressed && !held) Apply(false);
            return true;
        case KEY_STAR:
            if (!pressed && !held) Apply(true);
            return true;
        case KEY_EXIT:
            if (!pressed && !held) Close();
            return true;
        default:
            return true;
    }

    Beep(false);
    gUpdateDisplay = true;
    return true;
}

void RX_BAND_PRESETS_Draw(void)
{
    const RX_BandPreset_t *preset = &gRxBandPresets[sSelection];
    char range[22];
    char detail[22];

    UI_DisplayClear();
    UI_PrintStringSmallBold("RX BAND PRESET", 0, 0, 0);
    sprintf(range, "%3u.%05u-%3u.%05u", preset->lower / 100000u, preset->lower % 100000u,
            preset->upper / 100000u, preset->upper % 100000u);
    UI_PrintStringSmallBold(preset->name, 0, 0, 1);
    UI_PrintStringSmallNormal(range, 0, 0, 2);
    sprintf(detail, "%s %s STEP %u.%u", preset->modulation == MODULATION_AM ? "AM" :
            (preset->modulation == MODULATION_USB ? "USB" : "FM"),
            preset->bandwidth == BANDWIDTH_NARROW ? "NARROW" : "WIDE",
            preset->step / 100u, (preset->step / 10u) % 10u);
    UI_PrintStringSmallNormal(detail, 0, 0, 3);
    sprintf(detail, "%u/16 UP/DOWN SELECT", sSelection + 1u);
    UI_PrintStringSmallNormal(detail, 0, 0, 5);
    UI_PrintStringSmallNormal("M APPLY  * SCAN", 0, 0, 6);
    UI_PrintStringSmallNormal("EXIT CANCEL", 0, 0, 7);
}
