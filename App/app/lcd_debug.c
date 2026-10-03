/* K1/K5 V3の表示経路から決定的にフレームを取得するデバッグ処理。 */

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "app/lcd_debug.h"
#include "app/uart.h"
#include "app/rx_band_presets.h"
#include "app/rx_feature_state.h"
#include "app/action.h"
#include "app/chFrScanner.h"
#include "app/dtmf.h"
#include "driver/st7565.h"
#include "driver/system.h"
#include "driver/uart.h"
#include "functions.h"
#include "helper/battery.h"
#include "japanese_font.h"
#include "misc.h"
#include "radio.h"
#include "settings.h"
#include "ui/main.h"
#include "ui/helper.h"
#include "ui/menu.h"
#include "ui/jp_text.h"
#include "ui/status.h"
#include "ui/ui.h"

typedef struct __attribute__((packed))
{
    uint8_t  Magic[4];
    uint8_t  Version;
    uint8_t  Event;
    uint8_t  Status;
    uint8_t  Flags;
    uint16_t FrameSize;
    uint16_t FrameCrc;
} LCD_DEBUG_FRAME_HEADER_t;

_Static_assert(sizeof(LCD_DEBUG_FRAME_HEADER_t) == 12u,
               "LCD debug frame header must stay 12 bytes");

static uint16_t LCD_DEBUG_Crc16(const uint8_t *data, size_t size)
{
    uint16_t crc = 0u;

    for (size_t i = 0u; i < size; i++)
    {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t bit = 0u; bit < 8u; bit++)
            crc = (crc & 0x8000u) != 0u
                ? (uint16_t)((crc << 1) ^ 0x1021u)
                : (uint16_t)(crc << 1);
    }

    return crc;
}

static void LCD_DEBUG_CopyFrame(uint8_t *frame)
{
    memcpy(frame, gStatusLine, LCD_WIDTH);
    memcpy(frame + LCD_WIDTH, gFrameBuffer, sizeof(gFrameBuffer));
}

static void LCD_DEBUG_SendFrame(const uint8_t event, const bool success)
{
    static uint8_t frame[LCD_DEBUG_FRAME_BYTES];
    LCD_DEBUG_FRAME_HEADER_t header = {
        .Magic = {'L', 'C', 'D', 'F'},
        .Version = LCD_DEBUG_PROTOCOL_VERSION,
        .Event = event,
        .Status = success ? 0u : 1u,
        .Flags = 0u,
        .FrameSize = LCD_DEBUG_FRAME_BYTES,
    };

    LCD_DEBUG_CopyFrame(frame);
    header.FrameCrc = LCD_DEBUG_Crc16(frame, sizeof(frame));

    UART_Send(&header, sizeof(header));
    UART_Send(frame, sizeof(frame));
}

static void LCD_DEBUG_SelectMenu(const uint8_t menu_id, const bool submenu,
                                 const int32_t selection)
{
#ifdef ENABLE_FEAT_F4HWN_MENU_CAT
    gMenuLevel = MENU_LEVEL_ITEMS;
    gMenuCategory = CAT_ALL;
#endif
    gF_LOCK = false;
    UI_MENU_BuildView();
    gMenuCursor = UI_MENU_GetViewPos(menu_id);
    gIsInSubMenu = submenu;
    gSubMenuSelection = selection;
    gAskForConfirmation = 0u;
    gCssBackgroundScan = false;
#ifdef ENABLE_FEAT_F4HWN_ACTION_PICKER
    gActionPickerKey = 0u;
#endif
}

static bool LCD_DEBUG_SelectCategory(const uint8_t category,
                                     const bool include_service)
{
#ifdef ENABLE_FEAT_F4HWN_MENU_CAT
    gMenuLevel = MENU_LEVEL_CAT;
    gMenuCategory = CAT_ALL;
#ifdef ENABLE_FEAT_F4HWN_ACTION_PICKER
    gActionPickerKey = 0u;
#endif
    gF_LOCK = include_service;
    UI_MENU_BuildCategoryScreen();
    gMenuCursor = 0u;

    for (uint8_t i = 0u; i < gMenuListCount; i++)
    {
        if (gCatOrder[i] == category)
        {
            gMenuCursor = i;
            return true;
        }
    }
    return false;
#else
    (void)category;
    (void)include_service;
    return false;
#endif
}

static void LCD_DEBUG_PrepareReceive(const uint8_t display_mode,
                                     const uint8_t font_mode,
                                     const bool dual)
{
#ifdef ENABLE_JAPANESE
    JPFONT_DebugClearChannelNames();
#endif
    RADIO_InitInfo(&gEeprom.VfoInfo[0], MR_CHANNEL_FIRST, 14550000u);
    RADIO_InitInfo(&gEeprom.VfoInfo[1], MR_CHANNEL_FIRST + 1u, 43350000u);
    gEeprom.ScreenChannel[0] = MR_CHANNEL_FIRST;
    gEeprom.ScreenChannel[1] = MR_CHANNEL_FIRST + 1u;
    gEeprom.TX_VFO = 0u;
    gEeprom.RX_VFO = 0u;
    gEeprom.DUAL_WATCH = dual ? DUAL_WATCH_CHAN_A : DUAL_WATCH_OFF;
    gEeprom.CROSS_BAND_RX_TX = CROSS_BAND_OFF;
    gEeprom.CHANNEL_DISPLAY_MODE = display_mode;
#ifdef ENABLE_JAPANESE
    gSetting_japanese_main_font = font_mode;
#else
    (void)font_mode;
#endif
    gCurrentFunction = FUNCTION_RECEIVE;
    gScanStateDir = SCAN_OFF;
#ifdef ENABLE_SCAN_RANGES
    gScanRangeStart = 0u;
    gScanRangeStop = 0u;
#endif
    gCssBackgroundScan = false;
    gLowBattery = false;
    gLowBatteryConfirmed = true;
    gKeypadLocked = 0u;
    gMonitor = false;
    gDTMF_InputMode = false;
    gDTMF_InputBox[0] = '\0';
    gDTMF_InputBox_Index = 0u;
#ifdef ENABLE_RX_ONLY
    for (uint8_t vfo = 0u; vfo < 2u; vfo++)
    {
        ChannelAttributes_t *att =
            MR_GetChannelAttributes(gEeprom.ScreenChannel[vfo]);
        if (att != NULL)
        {
            att->exclude = false;
            att->scanlist = 0u;
        }
    }
#endif
#ifdef ENABLE_FEAT_F4HWN
    gBackLight = false;
    gMute = false;
#endif
    gEeprom.KEY_LOCK = false;
    gScreenToDisplay = DISPLAY_MAIN;
#ifdef ENABLE_FEAT_F4HWN_ACTION_PICKER
    gActionPickerKey = 0u;
#endif
    RADIO_SelectVfos();
}

static void LCD_DEBUG_RenderReceive(const uint8_t display_mode,
                                    const uint8_t font_mode,
                                    const bool dual)
{
    LCD_DEBUG_PrepareReceive(display_mode, font_mode, dual);
    UI_DisplayMain();
}

static void LCD_DEBUG_RenderJapaneseName(const uint8_t display_mode,
                                         const uint8_t font_mode,
                                         const bool dual)
{
    LCD_DEBUG_PrepareReceive(display_mode, font_mode, dual);
    JPFONT_DebugSetChannelName(MR_CHANNEL_FIRST, "東京空港");
    if (dual)
        JPFONT_DebugSetChannelName(MR_CHANNEL_FIRST + 1u, "羽田AIR");
    UI_DisplayMain();
}

#ifdef ENABLE_FEAT_F4HWN_AUDIO_SCOPE
static void LCD_DEBUG_RenderAudioScope(const bool dual,
                                       const uint16_t *samples,
                                       const size_t count)
{
    LCD_DEBUG_PrepareReceive(MDF_NAME_FREQ, JAPANESE_MAIN_FONT_8X8, dual);
    RX_FEATURE_STATE_SetEnabled(true);
    gScreenToDisplay = DISPLAY_MAIN;
    JPFONT_DebugSetChannelName(MR_CHANNEL_FIRST, "東京空港");
    if (dual)
        JPFONT_DebugSetChannelName(MR_CHANNEL_FIRST + 1u, "羽田AIR");

    UI_MAIN_DebugResetAudioScope();
    UI_DisplayMain();
    for (size_t i = 0u; i < count; i++)
    {
        UI_MAIN_DebugSetAudioScopeAmplitude(samples[i]);
        UI_DisplayAudioScope();
    }
    UI_DisplayStatus();
}

static void LCD_DEBUG_RenderAudioPattern(const uint8_t event)
{
    uint16_t samples[43];
    const bool dual = event == LCD_DEBUG_EVENT_RECEIVE_AUDIO_DUAL;

    for (uint8_t i = 0u; i < ARRAY_SIZE(samples); i++)
        samples[i] = 200u;

    switch (event)
    {
        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_LOW:
            for (uint8_t i = 0u; i < ARRAY_SIZE(samples); i++)
                samples[i] = (uint16_t)(200u + (i % 6u) * 8u);
            break;

        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_SPEECH:
        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_MAIN:
        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_DUAL:
        {
            static const uint8_t shape[] = {
                0, 1, 2, 5, 3, 7, 4, 2, 1, 0, 2, 6, 5, 3, 1,
                2, 4, 7, 5, 3, 2, 0, 1, 3, 6, 4, 2, 1, 5, 7,
                4, 2, 0, 1, 3, 5, 4, 2, 1, 0, 2, 4, 3,
            };
            for (uint8_t i = 0u; i < ARRAY_SIZE(samples); i++)
                samples[i] = (uint16_t)(200u + shape[i] * 500u);
            break;
        }

        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_STRONG:
        {
            static const uint16_t levels[] = {200u, 1200u, 4000u, 9000u,
                                                18000u, 9000u, 3000u, 600u};
            for (uint8_t i = 0u; i < ARRAY_SIZE(samples); i++)
                samples[i] = levels[i % ARRAY_SIZE(levels)];
            break;
        }

        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_ALTERNATING:
            for (uint8_t i = 0u; i < ARRAY_SIZE(samples); i++)
                samples[i] = (i & 1u) != 0u ? 16000u : 200u;
            break;

        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_IMPULSE:
            samples[0] = 30000u;
            samples[ARRAY_SIZE(samples) - 1u] = 28000u;
            break;

        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_STAIRCASE:
            for (uint8_t i = 0u; i < ARRAY_SIZE(samples); i++)
            {
                const uint8_t distance = i <= 21u ? i : (uint8_t)(42u - i);
                samples[i] = (uint16_t)(200u + distance * 600u);
            }
            break;

        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_CLIPPING:
            for (uint8_t i = 0u; i < ARRAY_SIZE(samples); i++)
                samples[i] = (i % 4u) == 0u ? 200u :
                             (i % 4u) == 1u ? 32767u :
                             (i % 4u) == 2u ? 32000u : 28000u;
            break;

        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_SILENCE:
        default:
            break;
    }

    LCD_DEBUG_RenderAudioScope(dual, samples, ARRAY_SIZE(samples));
}
#endif

static void LCD_DEBUG_RenderMainWithStatus(void)
{
    UI_DisplayMain();
    UI_DisplayStatus();
}

static void LCD_DEBUG_RenderReceiveState(const ModulationMode_t modulation,
                                         const DCS_CodeType_t code_type,
                                         const uint8_t bandwidth,
                                         const bool dual,
                                         const bool monitor)
{
    LCD_DEBUG_PrepareReceive(MDF_FREQUENCY, 0u, dual);
    RX_FEATURE_STATE_SetEnabled(true);
    gRxVfo->Modulation = modulation;
    gRxVfo->CHANNEL_BANDWIDTH = bandwidth;
#ifdef ENABLE_RX_ONLY
    gRxVfo->WIDE_PLUS = bandwidth == BANDWIDTH_WIDE_PLUS;
#endif
    gRxVfo->pRX->CodeType = code_type;
    gRxVfo->pRX->Code = 10u;
    gMonitor = monitor;
    LCD_DEBUG_RenderMainWithStatus();
}

static void LCD_DEBUG_RenderStatus(const uint8_t event)
{
    LCD_DEBUG_PrepareReceive(MDF_FREQUENCY, 0u, false);
    gEeprom.SCAN_LIST_DEFAULT = 1u;
    gEeprom.SCAN_LIST_ENABLED = true;
    gNextMrChannel = MR_CHANNEL_FIRST;

    switch (event)
    {
        case LCD_DEBUG_EVENT_STATUS_SCAN:
            gScanStateDir = SCAN_FWD;
            break;
        case LCD_DEBUG_EVENT_STATUS_DUAL:
            gEeprom.DUAL_WATCH = DUAL_WATCH_CHAN_A;
            RADIO_SelectVfos();
            break;
        case LCD_DEBUG_EVENT_STATUS_KEY_LOCK:
            gEeprom.KEY_LOCK = true;
            gKeypadLocked = 4u;
            break;
        case LCD_DEBUG_EVENT_STATUS_BACKLIGHT:
            gBackLight = true;
            gEeprom.BACKLIGHT_TIME = 1u;
            break;
        case LCD_DEBUG_EVENT_STATUS_MUTE:
            gMute = true;
            break;
        case LCD_DEBUG_EVENT_STATUS_NORMAL:
        default:
            break;
    }

    LCD_DEBUG_RenderMainWithStatus();
}

static bool LCD_DEBUG_RenderEvent(const uint8_t event)
{
    UI_StatusClear();
#ifdef ENABLE_FEAT_F4HWN_ACTION_PICKER
    gActionPickerKey = 0u;
#endif

    switch (event)
    {
        case LCD_DEBUG_EVENT_MENU:
            LCD_DEBUG_SelectMenu(MENU_R_DCS, false, 0);
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_HELP:
            LCD_DEBUG_SelectMenu(MENU_R_CTCS, false, 0);
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_PRESET_BANK:
            UI_DisplayClear();
            RX_BAND_PRESETS_Draw();
            ST7565_BlitFullScreen();
            return true;

        case LCD_DEBUG_EVENT_SCAN_LIST_NAME:
        case LCD_DEBUG_EVENT_SCAN_MEMORY:
        case LCD_DEBUG_EVENT_SCAN_DUAL:
        case LCD_DEBUG_EVENT_SCAN_RANGE:
            UI_MAIN_DebugRenderScanProgress(event);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_MAIN:
            LCD_DEBUG_RenderReceive(MDF_FREQUENCY, 0u, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_DUAL:
            LCD_DEBUG_RenderReceive(MDF_FREQUENCY, 0u, true);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_SCANLIST_PRESENT:
#ifdef ENABLE_RX_ONLY
        {
            LCD_DEBUG_PrepareReceive(MDF_FREQUENCY, 0u, false);
            ChannelAttributes_t *att =
                MR_GetChannelAttributes(MR_CHANNEL_FIRST);
            if (att == NULL)
                return false;
            att->exclude = false;
            att->scanlist = 1u;
            memcpy(gListName[0], "LST", sizeof("LST"));
            LCD_DEBUG_RenderMainWithStatus();
            return true;
        }
#else
            return false;
#endif

        case LCD_DEBUG_EVENT_MENU_CAT_CHANNELS:
            if (!LCD_DEBUG_SelectCategory(CAT_CHANNELS, false))
                return false;
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_CAT_SCAN:
            if (!LCD_DEBUG_SelectCategory(CAT_SCAN, false))
                return false;
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_CAT_KEYS:
            if (!LCD_DEBUG_SelectCategory(CAT_KEYS, false))
                return false;
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_CAT_POWER:
            if (!LCD_DEBUG_SelectCategory(CAT_POWER, false))
                return false;
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_CAT_DISPLAY:
            if (!LCD_DEBUG_SelectCategory(CAT_DISPLAY, false))
                return false;
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_CAT_TIMERS:
            if (!LCD_DEBUG_SelectCategory(CAT_TIMERS, false))
                return false;
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_CAT_AUDIO:
            if (!LCD_DEBUG_SelectCategory(CAT_AUDIO, false))
                return false;
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_CAT_RADIO:
            if (!LCD_DEBUG_SelectCategory(CAT_RADIO, false))
                return false;
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_CAT_DTMF:
            if (!LCD_DEBUG_SelectCategory(CAT_DTMF, false))
                return false;
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_CAT_SERVICE:
            if (!LCD_DEBUG_SelectCategory(CAT_SERVICE, true))
                return false;
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_CAT_ALL:
            if (!LCD_DEBUG_SelectCategory(CAT_ALL, false))
                return false;
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_ITEM_DCS_OFF:
            LCD_DEBUG_SelectMenu(MENU_R_DCS, false, 0);
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_ITEM_DCS_FORWARD:
            LCD_DEBUG_SelectMenu(MENU_R_DCS, false, 104);
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_ITEM_DCS_REVERSE:
            LCD_DEBUG_SelectMenu(MENU_R_DCS, false, 208);
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_ITEM_CTCS_FORWARD:
            LCD_DEBUG_SelectMenu(MENU_R_CTCS, false, 50);
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_ITEM_CTCS_REVERSE:
            LCD_DEBUG_SelectMenu(MENU_R_CTCS, false, 100);
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_ITEM_W_N:
            LCD_DEBUG_SelectMenu(MENU_W_N, false, 3);
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_ITEM_LONG:
            LCD_DEBUG_SelectMenu(MENU_RX_BANK_SET, false, 8);
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_ITEM_CONFIRM:
            LCD_DEBUG_SelectMenu(MENU_RESET, false, 0);
            gAskForConfirmation = 1u;
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_ITEM_CSS_SCAN:
            LCD_DEBUG_SelectMenu(MENU_R_DCS, false, 208);
            gCssBackgroundScan = true;
            UI_DisplayMenu();
            return true;

        case LCD_DEBUG_EVENT_MENU_ITEM_FONT_16:
        case LCD_DEBUG_EVENT_MENU_ITEM_FONT_8:
        case LCD_DEBUG_EVENT_MENU_ITEM_FONT_ASCII:
        case LCD_DEBUG_EVENT_MENU_ITEM_FONT_14:
#ifdef ENABLE_JAPANESE
            LCD_DEBUG_SelectMenu(MENU_SET_MAIN_FONT, false,
                event == LCD_DEBUG_EVENT_MENU_ITEM_FONT_16 ? JAPANESE_MAIN_FONT_16X16 :
                event == LCD_DEBUG_EVENT_MENU_ITEM_FONT_8 ? JAPANESE_MAIN_FONT_8X8 :
                event == LCD_DEBUG_EVENT_MENU_ITEM_FONT_ASCII ? JAPANESE_MAIN_FONT_ASCII :
                JAPANESE_MAIN_FONT_14X14);
            UI_DisplayMenu();
            return true;
#else
            return false;
#endif

        case LCD_DEBUG_EVENT_MENU_ITEM_ACTION:
#ifdef ENABLE_FEAT_F4HWN_ACTION_PICKER
            gActionPickerKey = 1u;
            gActionPickerSelection[0] = gSubMenu_SIDEFUNCTIONS_size > 2u
                ? (uint8_t)(gSubMenu_SIDEFUNCTIONS_size - 1u) : 1u;
            gCurrentFunction = FUNCTION_FOREGROUND;
            UI_DisplayMain();
            return true;
#else
            return false;
#endif

        case LCD_DEBUG_EVENT_WARNING_RX_ONLY:
            UI_DisplayUnavailable(WRX_UI_TEXT_VFO_TX_DISABLED);
            return true;

        case LCD_DEBUG_EVENT_WARNING_FM_ONLY:
            UI_DisplayUnavailable(WRX_UI_TEXT_FM_ONLY);
            return true;

        case LCD_DEBUG_EVENT_WARNING_RX_EXT_OFF:
            UI_DisplayUnavailable(WRX_UI_TEXT_RX_EXT_OFF);
            return true;

        case LCD_DEBUG_EVENT_WARNING_PRESET_FAIL:
            UI_DisplayUnavailable(WRX_UI_TEXT_PRESET_ERROR);
            return true;

        case LCD_DEBUG_EVENT_WARNING_SCAN_ACTIVE:
            UI_DisplayUnavailable(WRX_UI_TEXT_SCAN_ACTIVE);
            return true;

        case LCD_DEBUG_EVENT_WARNING_SCAN_COMPLETE:
            UI_DisplayUnavailable(WRX_UI_TEXT_SCAN_COMPLETE);
            return true;

        case LCD_DEBUG_EVENT_WARNING_SCAN_FAILED:
            UI_DisplayUnavailable(WRX_UI_TEXT_SCAN_FAILED);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_FREQUENCY:
            LCD_DEBUG_RenderReceive(MDF_FREQUENCY, 0u, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_CHANNEL:
            LCD_DEBUG_RenderReceive(MDF_CHANNEL, 0u, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_NAME_16:
            LCD_DEBUG_RenderReceive(MDF_NAME, 0u, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_NAME_FREQ:
            LCD_DEBUG_RenderReceive(MDF_NAME_FREQ, 0u, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_NAME_8:
            LCD_DEBUG_RenderReceive(MDF_NAME, 1u, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_NAME_14:
            LCD_DEBUG_RenderReceive(MDF_NAME, 3u, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_NAME_ASCII:
            LCD_DEBUG_RenderReceive(MDF_NAME, 2u, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_DUAL_NAME:
            LCD_DEBUG_RenderReceive(MDF_NAME_FREQ, 0u, true);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_JP_NAME_16:
            LCD_DEBUG_RenderJapaneseName(MDF_NAME, JAPANESE_MAIN_FONT_16X16, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_JP_NAME_14:
            LCD_DEBUG_RenderJapaneseName(MDF_NAME, JAPANESE_MAIN_FONT_14X14, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_JP_NAME_8:
            LCD_DEBUG_RenderJapaneseName(MDF_NAME, JAPANESE_MAIN_FONT_8X8, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_JP_NAME_FREQ:
            LCD_DEBUG_RenderJapaneseName(MDF_NAME_FREQ, JAPANESE_MAIN_FONT_16X16, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_JP_DUAL_NAME:
            LCD_DEBUG_RenderJapaneseName(MDF_NAME_FREQ, JAPANESE_MAIN_FONT_8X8, true);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_SILENCE:
        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_LOW:
        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_SPEECH:
        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_STRONG:
        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_ALTERNATING:
        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_IMPULSE:
        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_STAIRCASE:
        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_CLIPPING:
        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_MAIN:
        case LCD_DEBUG_EVENT_RECEIVE_AUDIO_DUAL:
#ifdef ENABLE_FEAT_F4HWN_AUDIO_SCOPE
            LCD_DEBUG_RenderAudioPattern(event);
            return true;
#else
            return false;
#endif

        case LCD_DEBUG_EVENT_RECEIVE_AM:
            LCD_DEBUG_RenderReceiveState(MODULATION_AM, CODE_TYPE_OFF,
                                          BANDWIDTH_NARROW, false, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_USB:
            LCD_DEBUG_RenderReceiveState(MODULATION_USB, CODE_TYPE_OFF,
                                          BANDWIDTH_WIDE, false, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_CTCSS:
            LCD_DEBUG_RenderReceiveState(MODULATION_FM, CODE_TYPE_CONTINUOUS_TONE,
                                          BANDWIDTH_NARROW, false, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_CTCSS_REVERSE:
            LCD_DEBUG_RenderReceiveState(MODULATION_FM,
                                          CODE_TYPE_REVERSE_CONTINUOUS_TONE,
                                          BANDWIDTH_NARROW, false, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_DCS:
            LCD_DEBUG_RenderReceiveState(MODULATION_FM, CODE_TYPE_DIGITAL,
                                          BANDWIDTH_NARROW, false, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_DCS_REVERSE:
            LCD_DEBUG_RenderReceiveState(MODULATION_FM, CODE_TYPE_REVERSE_DIGITAL,
                                          BANDWIDTH_NARROW, false, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_BANDWIDTH_WIDE_PLUS:
            LCD_DEBUG_RenderReceiveState(MODULATION_FM, CODE_TYPE_OFF,
                                          BANDWIDTH_WIDE_PLUS, false, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_BANDWIDTH_WIDE:
            LCD_DEBUG_RenderReceiveState(MODULATION_FM, CODE_TYPE_OFF,
                                          BANDWIDTH_WIDE, false, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_BANDWIDTH_NARROW:
            LCD_DEBUG_RenderReceiveState(MODULATION_FM, CODE_TYPE_OFF,
                                          BANDWIDTH_NARROW, false, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_BANDWIDTH_NARROWER:
            LCD_DEBUG_RenderReceiveState(MODULATION_FM, CODE_TYPE_OFF,
                                          BANDWIDTH_NARROWER, false, false);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_MONITOR:
            LCD_DEBUG_RenderReceiveState(MODULATION_FM, CODE_TYPE_OFF,
                                          BANDWIDTH_NARROW, false, true);
            return true;

        case LCD_DEBUG_EVENT_RECEIVE_DUAL_B:
            LCD_DEBUG_PrepareReceive(MDF_NAME_FREQ, JAPANESE_MAIN_FONT_8X8, true);
            gEeprom.DUAL_WATCH = DUAL_WATCH_CHAN_B;
            RADIO_SelectVfos();
            JPFONT_DebugSetChannelName(MR_CHANNEL_FIRST, "東京空港");
            JPFONT_DebugSetChannelName(MR_CHANNEL_FIRST + 1u, "羽田AIR");
            LCD_DEBUG_RenderMainWithStatus();
            return true;

        case LCD_DEBUG_EVENT_MAIN_LOW_BATTERY:
            LCD_DEBUG_PrepareReceive(MDF_FREQUENCY, 0u, false);
            gLowBattery = true;
            gLowBatteryConfirmed = false;
            UI_DisplayMain();
            UI_DisplayStatus();
            return true;

        case LCD_DEBUG_EVENT_MAIN_KEYPAD_LOCK:
            LCD_DEBUG_PrepareReceive(MDF_FREQUENCY, 0u, false);
            gEeprom.KEY_LOCK = true;
            gKeypadLocked = 4u;
            LCD_DEBUG_RenderMainWithStatus();
            return true;

        case LCD_DEBUG_EVENT_STATUS_NORMAL:
        case LCD_DEBUG_EVENT_STATUS_SCAN:
        case LCD_DEBUG_EVENT_STATUS_DUAL:
        case LCD_DEBUG_EVENT_STATUS_KEY_LOCK:
        case LCD_DEBUG_EVENT_STATUS_BACKLIGHT:
        case LCD_DEBUG_EVENT_STATUS_MUTE:
            LCD_DEBUG_RenderStatus(event);
            return true;

        case LCD_DEBUG_EVENT_MAIN_DTMF:
            LCD_DEBUG_PrepareReceive(MDF_FREQUENCY, 0u, false);
            strcpy(gDTMF_InputBox, "123#");
            gDTMF_InputBox_Index = 4u;
            gDTMF_InputMode = true;
            LCD_DEBUG_RenderMainWithStatus();
            return true;

        case LCD_DEBUG_EVENT_MAIN_SCAN_RANGE:
            LCD_DEBUG_PrepareReceive(MDF_FREQUENCY, 0u, false);
            gEeprom.ScreenChannel[0] = FREQ_CHANNEL_FIRST + BAND3_137MHz;
            gScanRangeStart = 14550000u;
            gScanRangeStop = 14560000u;
            LCD_DEBUG_RenderMainWithStatus();
            return true;

        default:
            return false;
    }
}

void LCD_DEBUG_HandleCommand(uint32_t port, const uint8_t *buffer)
{
    (void)port;

    if (buffer == NULL)
        return;

    const uint16_t command = (uint16_t)buffer[0] |
                             ((uint16_t)buffer[1] << 8);
    const uint16_t size = (uint16_t)buffer[2] |
                          ((uint16_t)buffer[3] << 8);

    if (command != LCD_DEBUG_COMMAND_ID || size != 2u || buffer[5] != 0u)
        return;

    const uint8_t event = buffer[4];
    LCD_DEBUG_SendFrame(event, LCD_DEBUG_RenderEvent(event));
}

void LCD_DEBUG_Run(void)
{
    /* 設定値は表示入力としてだけ読み込み、RF初期化は行わない。 */
    SETTINGS_InitEEPROM();
#ifdef ENABLE_RX_ONLY
    RX_FEATURE_STATE_Init();
#endif
    gEeprom.TX_VFO = 0u;
    gEeprom.RX_VFO = 0u;
    gEeprom.DUAL_WATCH = DUAL_WATCH_OFF;
    gEeprom.CROSS_BAND_RX_TX = CROSS_BAND_OFF;
    RADIO_SelectVfos();

    LCD_DEBUG_SelectMenu(MENU_R_DCS, false, 0);
    UI_DisplayMenu();

    while (true)
    {
        UART_ServiceCommands();
        SYSTEM_DelayMs(1u);
    }
}
