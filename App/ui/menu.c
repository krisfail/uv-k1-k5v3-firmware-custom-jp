/* Copyright 2023 Dual Tachyon
 * https://github.com/DualTachyon
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *     Unless required by applicable law or agreed to in writing, software
 *     distributed under the License is distributed on an "AS IS" BASIS,
 *     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *     See the License for the specific language governing permissions and
 *     limitations under the License.
 */

#include <string.h>
#include <stdlib.h>

#include "../app/dtmf.h"
#include "../app/menu.h"
#include "../bitmaps.h"
#include "../board.h"
#include "../dcs.h"
#include "../driver/backlight.h"
#include "../driver/bk4819.h"
#include "../driver/eeprom.h"
#include "../driver/st7565.h"
#include "../external/printf/printf.h"
#include "../font.h"
#include "../frequencies.h"
#include "../helper/battery.h"
#include "../misc.h"
#include "../settings.h"
#ifdef ENABLE_RX_ONLY
    #include "../app/rx_feature_state.h"
#endif

#ifdef ENABLE_FEAT_F4HWN
    #include "../version.h"
#endif

#include "helper.h"
#include "jp_text.h"
#include "inputbox.h"
#include "menu.h"
#include "menu_text.h"
#include "ui.h"
#include "welcome.h"

#ifdef ENABLE_JAPANESE
static void UI_MENU_PrintString(const char *text, uint8_t start, uint8_t end,
                                uint8_t line, uint8_t width)
{
    if (!UI_PrintStringJapaneseExternal(text, start, end, line))
        UI_PrintString(text, start, end, line, width);
}

#ifdef ENABLE_CUSTOM_MENU_LAYOUT
static void UI_MENU_PrintStringClipped(const char *text, uint8_t start,
                                       uint8_t end, uint8_t line, uint8_t width)
{
    if (!UI_PrintStringJapaneseExternal(text, start, end, line))
        UI_PrintStringClipped(text, start, end, line, width);
}
#endif
#else
#define UI_MENU_PrintString UI_PrintString
#ifdef ENABLE_CUSTOM_MENU_LAYOUT
#define UI_MENU_PrintStringClipped UI_PrintStringClipped
#endif
#endif


const t_menu_item MenuList[] =
{
//   text,          menu ID
    {WRX_MENU_LABEL_STEP, MENU_STEP},
 #ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_POWER, MENU_TXP},
 #endif
    {WRX_MENU_LABEL_RX_DCS, MENU_R_DCS},
    {WRX_MENU_LABEL_RX_CTCS, MENU_R_CTCS},
 #ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_TX_DCS, MENU_T_DCS},
    {WRX_MENU_LABEL_TX_CTCS, MENU_T_CTCS},
    {WRX_MENU_LABEL_TX_OFFSET_DIR, MENU_SFT_D},
    {WRX_MENU_LABEL_TX_OFFSET, MENU_OFFSET},
 #endif
    {WRX_MENU_LABEL_W_N, MENU_W_N},
#ifdef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_RX_EXT, MENU_RX_EXT},
    {WRX_MENU_LABEL_RX_BANK, MENU_RX_BANK},
    {WRX_MENU_LABEL_RX_BANK_SET, MENU_RX_BANK_SET},
#endif
#ifndef ENABLE_FEAT_F4HWN
    {WRX_MENU_LABEL_SCRAMBLER, MENU_SCR},
#endif
 #ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_BUSY_CANCEL, MENU_BCL},
 #endif
    {WRX_MENU_LABEL_COMPANDER, MENU_COMPAND},
    {WRX_MENU_LABEL_MODULATION, MENU_AM},
    {WRX_MENU_LABEL_CHANNEL_LIST, MENU_LIST_CH},
    {WRX_MENU_LABEL_SAVE_CHANNEL, MENU_MEM_CH},
    {WRX_MENU_LABEL_DELETE_CHANNEL, MENU_DEL_CH},
    {WRX_MENU_LABEL_CHANNEL_NAME, MENU_MEM_NAME},

    {WRX_MENU_LABEL_SCAN_LIST, MENU_S_LIST},
    {WRX_MENU_LABEL_PRIORITY, MENU_S_PRI},
    {WRX_MENU_LABEL_PRIORITY1, MENU_S_PRI_CH_1},
    {WRX_MENU_LABEL_PRIORITY2, MENU_S_PRI_CH_2},
    {WRX_MENU_LABEL_SCAN_REVERSE, MENU_SC_REV},
#ifndef ENABLE_FEAT_F4HWN
    #ifdef ENABLE_NOAA
        {WRX_MENU_LABEL_NOAA_SCAN, MENU_NOAA_S},
    #endif
#endif
    {WRX_MENU_LABEL_F1_SHORT, MENU_F1SHRT},
    {WRX_MENU_LABEL_F1_LONG, MENU_F1LONG},
    {WRX_MENU_LABEL_F2_SHORT, MENU_F2SHRT},
    {WRX_MENU_LABEL_F2_LONG, MENU_F2LONG},
    {WRX_MENU_LABEL_M_LONG, MENU_MLONG},

    {WRX_MENU_LABEL_KEY_LOCK, MENU_AUTOLK},
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_TX_TIMEOUT, MENU_TOT},
#endif
    {WRX_MENU_LABEL_BATTERY_SAVE, MENU_SAVE},
    {WRX_MENU_LABEL_BATTERY_TEXT, MENU_BAT_TXT},
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_MIC, MENU_MIC},
    {WRX_MENU_LABEL_MIC_BAR, MENU_MIC_BAR},
#endif
    {WRX_MENU_LABEL_CHANNEL_DISPLAY, MENU_MDF},
    {WRX_MENU_LABEL_POWER_ON, MENU_PONMSG},
    {WRX_MENU_LABEL_BACKLIGHT, MENU_ABR},
    {WRX_MENU_LABEL_BACKLIGHT_MIN, MENU_ABR_MIN},
    {WRX_MENU_LABEL_BACKLIGHT_MAX, MENU_ABR_MAX},
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_BACKLIGHT_TXRX, MENU_ABR_ON_TX_RX},
#endif
    {WRX_MENU_LABEL_BEEP, MENU_BEEP},
#ifdef ENABLE_VOICE
    {WRX_MENU_LABEL_VOICE, MENU_VOICE},
#endif
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_ROGER, MENU_ROGER},
    {WRX_MENU_LABEL_STE, MENU_STE},
    {WRX_MENU_LABEL_RP_STE, MENU_RP_STE},
    {WRX_MENU_LABEL_CALL1, MENU_1_CALL},
#endif
#ifdef ENABLE_ALARM
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_ALARM, MENU_AL_MOD},
#endif
#endif
#ifdef ENABLE_DTMF_CALLING
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_ANI, MENU_ANI_ID},
#endif
#endif
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_UP_CODE, MENU_UPCODE},
    {WRX_MENU_LABEL_DOWN_CODE, MENU_DWCODE},
    {WRX_MENU_LABEL_PTT_ID, MENU_PTT_ID},
    {WRX_MENU_LABEL_DTMF_ST, MENU_D_ST},
#endif
#ifdef ENABLE_DTMF_CALLING
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_DTMF_RESPONSE, MENU_D_RSP},
    {WRX_MENU_LABEL_DTMF_HOLD, MENU_D_HOLD},
#endif
#endif
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_DTMF_PRE, MENU_D_PRE},
#endif
#ifdef ENABLE_DTMF_CALLING
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_DTMF_DECODE, MENU_D_DCD},
    {WRX_MENU_LABEL_DTMF_LIST, MENU_D_LIST},
#endif
#endif
    {WRX_MENU_LABEL_DTMF_LIVE, MENU_D_LIVE_DEC},
#ifndef ENABLE_FEAT_F4HWN
    #ifdef ENABLE_AM_FIX
        {WRX_MENU_LABEL_AM_FIX, MENU_AM_FIX},
#endif
#endif
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_VOX, MENU_VOX},
#endif
#ifdef ENABLE_FEAT_F4HWN
 #ifdef ENABLE_JAPANESE
    {WRX_MENU_LABEL_INFO, MENU_VOL},
 #else
    {WRX_MENU_LABEL_INFO, MENU_VOL},
 #endif
#else
#ifdef ENABLE_JAPANESE
    {WRX_MENU_LABEL_INFO, MENU_VOL},
#else
    {WRX_MENU_LABEL_BATTERY_VOLTAGE, MENU_VOL},
#endif
#endif
 #ifdef ENABLE_JAPANESE
    {WRX_MENU_LABEL_RX_MODE, MENU_TDR},
    {WRX_MENU_LABEL_SQUELCH, MENU_SQL},
 #else
    {WRX_MENU_LABEL_RX_MODE, MENU_TDR},
    {WRX_MENU_LABEL_SQUELCH, MENU_SQL},
 #endif
#ifdef ENABLE_FEAT_F4HWN
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_SET_POWER, MENU_SET_PWR},
    {WRX_MENU_LABEL_SET_PTT, MENU_SET_PTT},
    {WRX_MENU_LABEL_SET_TOT, MENU_SET_TOT},
    {WRX_MENU_LABEL_SET_EOT, MENU_SET_EOT},
#endif
    {WRX_MENU_LABEL_SET_CONTRAST, MENU_SET_CTR},
    {WRX_MENU_LABEL_SET_INV, MENU_SET_INV},
    {WRX_MENU_LABEL_SET_MENU_LOCK, MENU_SET_LCK},
    {WRX_MENU_LABEL_SET_METER, MENU_SET_MET},
    {WRX_MENU_LABEL_SET_GUI, MENU_SET_GUI},
#ifdef ENABLE_FEAT_F4HWN_AUDIO    
    {WRX_MENU_LABEL_SET_AUDIO, MENU_SET_AUD},
#endif
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_SET_TIMER, MENU_SET_TMR},
#endif
#ifdef ENABLE_FEAT_F4HWN_SLEEP
    {WRX_MENU_LABEL_SET_SLEEP, MENU_SET_OFF},
#endif
#ifdef ENABLE_FEAT_F4HWN_NARROWER
    {WRX_MENU_LABEL_SET_NFM, MENU_SET_NFM},
#endif
#ifdef ENABLE_FEAT_F4HWN_VOL
    {WRX_MENU_LABEL_SET_VOLUME, MENU_SET_VOL},
#endif
#ifdef ENABLE_FEAT_F4HWN_RESCUE_OPS
    {WRX_MENU_LABEL_SET_KEY, MENU_SET_KEY},
#endif
#ifdef ENABLE_NOAA
    {WRX_MENU_LABEL_SET_NWR, MENU_NOAA_S},
#endif
#ifdef ENABLE_FEAT_F4HWN_SCAN_FASTER
    {WRX_MENU_LABEL_SET_SCAN, MENU_SET_SCN},
#endif
#ifdef ENABLE_FEAT_F4HWN_LOGO_SAV
    {WRX_MENU_LABEL_SET_SAVE, MENU_SET_SAV},
#endif
#endif
    // hidden menu items from here on
    // enabled if pressing both the PTT and upper side button at power-on
#ifndef ENABLE_RX_ONLY
    {WRX_MENU_LABEL_F_LOCK, MENU_F_LOCK},
#endif
#ifndef ENABLE_RX_ONLY
#ifndef ENABLE_FEAT_F4HWN
    {WRX_MENU_LABEL_TX_200, MENU_200TX},
    {WRX_MENU_LABEL_TX_350, MENU_350TX},
    {WRX_MENU_LABEL_TX_500, MENU_500TX},
#endif
    {WRX_MENU_LABEL_350_ENABLE, MENU_350EN},
#endif
#ifndef ENABLE_FEAT_F4HWN
    {WRX_MENU_LABEL_SCRAMBLER_EN, MENU_SCREN},
#endif
#ifdef ENABLE_F_CAL_MENU
    {WRX_MENU_LABEL_FREQ_CAL, MENU_F_CALI},
#endif
    {WRX_MENU_LABEL_BATTERY_CAL, MENU_BATCAL},
    {WRX_MENU_LABEL_BATTERY_TYPE, MENU_BATTYP},
    {WRX_MENU_LABEL_SET_NAV, MENU_SET_NAV},
    {WRX_MENU_LABEL_RESET, MENU_RESET},

    {"",                              0xff               }  // end of list - DO NOT delete or move this this
};

#ifdef ENABLE_RX_ONLY
// Keep the hidden-menu boot path available for EEPROM initialization and
// battery calibration.  TX-related entries remain excluded above.
const uint8_t FIRST_HIDDEN_MENU_ITEM = MENU_BATCAL;
#else
const uint8_t FIRST_HIDDEN_MENU_ITEM = MENU_F_LOCK;
#endif

const char* const gSubMenu_TXP[] =
{
    "USER",
    "LOW 1",
    "LOW 2",
    "LOW 3",
    "LOW 4",
    "LOW 5",
    "MID",
    "HIGH"
};

const char* const gSubMenu_SFT_D[] =
{
    "OFF",
    "+",
    "-"
};

const char* const gSubMenu_W_N[] =
{
#ifdef ENABLE_RX_ONLY
    "W+",
    "W",
    "N",
    "N-"
#else
    "WIDE",
    "NARROW"
#endif
};

#ifdef ENABLE_RX_ONLY
const char* const gSubMenu_RX_BANK[] =
{
    "ALL", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8"
};

const char* const gSubMenu_RX_BANK_SET[] =
{
#ifdef ENABLE_JAPANESE
    "\x97", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8"
#else
    "NONE", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8"
#endif
};
#endif

const char* const gSubMenu_OFF_ON[] =
{
    "OFF",
    "ON"
};

const char* gSubMenu_NA = "N/A";

const char* const gSubMenu_RXMode[] =
{
#ifdef ENABLE_RX_ONLY
    "\x80\x81",
    "DUAL RX",
    "SINGLE",
#else
    "MAIN\nONLY",       // TX and RX on main only
    "DUAL RX\nRESPOND", // Watch both and respond
    "CROSS\nBAND",      // TX on main, RX on secondary
    "MAIN TX\nDUAL RX"  // always TX on main, but RX on both
#endif
};

#ifdef ENABLE_VOICE
    const char* const gSubMenu_VOICE[] =
    {
        "OFF",
        "CHI",
        "ENG"
    };
#endif

const char* const gSubMenu_MDF[] =
{
#ifdef ENABLE_JAPANESE
    "\xF2\xF3\xF4",
    "CH",
    "\x8A",
    "\x8A\n+\n\xF2\xF3\xF4"
#else
    "FREQ",
    "CHANNEL\nNUMBER",
    "NAME",
    "NAME\n+\nFREQ"
#endif
};

#ifdef ENABLE_ALARM
    const char* const gSubMenu_AL_MOD[] =
    {
        "SITE",
        "TONE"
    };
#endif

#ifdef ENABLE_DTMF_CALLING
const char* const gSubMenu_D_RSP[] =
{
    "DO\nNOTHING",
    "RING",
    "REPLY",
    "BOTH"
};
#endif

const char* const gSubMenu_PTT_ID[] =
{
    "OFF",
    "UP CODE",
    "DOWN CODE",
    "UP+DOWN\nCODE",
    "APOLLO\nQUINDAR"
};

const char* const gSubMenu_PONMSG[] =
{
#ifdef ENABLE_FEAT_F4HWN
    "ALL",
    "SOUND",
#else
    "FULL",
#endif
    "MESSAGE",
    "VOLTAGE",
#ifdef ENABLE_FEAT_F4HWN_LOGO
    "LOGO",
    "LOGO+MSG",
    "LOGO+ALL",
#endif
    "NONE"
};

#if defined(ENABLE_FEAT_F4HWN) && defined(ENABLE_FEAT_F4HWN_LOGO_SAV)
const char* const gSubMenu_SET_SAV[] =
{
    "OFF",
    "LOGO",
    "LOGO+",
    "MATRIX"
};
#endif

const char* const gSubMenu_ROGER[] =
{
    "OFF",
    "ROGER",
    "MDC"
};

const char* const gSubMenu_RESET[] =
{
    "VFO",
#ifdef ENABLE_JAPANESE
    "\xF8\xF9\xFA"
#else
    "ALL"
#endif
};

const char* const gSubMenu_F_LOCK[] =
{
    "DEFAULT+\n137-174\n400-470",
    "FCC HAM\n144-148\n420-450",
#ifdef ENABLE_FEAT_F4HWN_CA
    "CA HAM\n144-148\n430-450",
#endif
    "CE HAM\n144-146\n430-440",
    "GB HAM\n144-148\n430-440",
    "137-174\n400-430",
    "137-174\n400-438",
#ifdef ENABLE_FEAT_F4HWN_PMR
    "PMR 446",
#endif
#ifdef ENABLE_FEAT_F4HWN_GMRS_FRS_MURS
    "GMRS\nFRS\nMURS",
#endif
    "DISABLE\nALL",
    "UNLOCK\nALL",
};

const char* const gSubMenu_RX_TX[] =
{
    "OFF",
    "TX",
    "RX",
    "TX/RX"
};

const char* const gSubMenu_BAT_TXT[] =
{
#ifdef ENABLE_JAPANESE
    "\x97",
    "\x8F\x92",
    "%"
#else
    "NONE",
    "VOLTAGE",
    "PERCENT"
#endif
};

const char* const gSubMenu_BATTYP[] =
{
    "1600mAh K5",
    "2200mAh K5",
    "3500mAh K5",
    "1400mAh K1",
    "2500mAh K1"
};

const char* const gSubMenu_SET_NAV[] =
{
    "LEFT\nRIGHT\nUV-K1",
    "UP\nDOWN\nUV-K5(8)",
};

#ifndef ENABLE_FEAT_F4HWN
const char* const gSubMenu_SCRAMBLER[] =
{
    "OFF",
    "2600Hz",
    "2700Hz",
    "2800Hz",
    "2900Hz",
    "3000Hz",
    "3100Hz",
    "3200Hz",
    "3300Hz",
    "3400Hz",
    "3500Hz"
};
#endif

#ifdef ENABLE_FEAT_F4HWN
    const char* const gSubMenu_SET_PWR[] =
    {
        "< 20m",
        "125m",
        "250m",
        "500m",
        "1",
        "2",
        "5"
    };

    const char* const gSubMenu_SET_PTT[] =
    {
        "CLASSIC",
        "ONEPUSH"
    };

    const char* const gSubMenu_SET_TOT[] =  
    {
        "OFF",
        "SOUND",
        "VISUAL",
        "ALL"
    };

    const char* const gSubMenu_SET_LCK[] =
    {
#ifdef ENABLE_JAPANESE
        "\xB7\xE0",
        "\xB7\xE0\nACT",
        "\xB7\xE0\nPTT",
        "\xB7\xE0\nACT\nPTT"
#else
        "KEYS",
        "KEYS\nACTIONS",
        "KEYS\nPTT",
        "KEYS\nACTIONS\nPTT"
#endif
    };

    const char* const gSubMenu_SET_MET[] =
    {
        "TINY",
        "CLASSIC"
    };

    #ifdef ENABLE_FEAT_F4HWN_SCAN_FASTER
        const char* const gSubMenu_SET_SCN[] =
        {
            "NORMAL",
            "FAST"
        };
    #endif

    #ifdef ENABLE_FEAT_F4HWN_AUDIO
        const char* const gSubMenu_SET_AUD_FM[] =
        {
            "FLAT",
            "CLEAN",
            "MID",
            "BOOST",
            "MAX"
        };

        const char* const gSubMenu_SET_AUD_AM[] =
        {
            "SHARP",
            "STOCK",
            "OPEN"
        };
    #endif

    #ifdef ENABLE_FEAT_F4HWN_NARROWER
        const char* const gSubMenu_SET_NFM[] =
        {
#ifdef ENABLE_JAPANESE
            "\xED\xEE",
            "\xED\xEE+"
#else
            "NARROW",
            "NARROWER"
#endif
        };
    #endif

    #ifdef ENABLE_FEAT_F4HWN_RESCUE_OPS
        const char* const gSubMenu_SET_KEY[] =
        {
            "KEY_MENU",
            "KEY_UP",
            "KEY_DOWN",
            "KEY_EXIT",
            "KEY_STAR"
        };
    #endif
#endif

const t_sidefunction gSubMenu_SIDEFUNCTIONS[] =
{
    {WRX_ACTION_NONE,            ACTION_OPT_NONE},
#ifdef ENABLE_FLASHLIGHT
    {WRX_ACTION_FLASHLIGHT,    ACTION_OPT_FLASHLIGHT},
#endif
#ifndef ENABLE_RX_ONLY
    {"POWER",           ACTION_OPT_POWER},
#endif
    {WRX_ACTION_MONITOR,         ACTION_OPT_MONITOR},
    {WRX_ACTION_SCAN,            ACTION_OPT_SCAN},
#ifdef ENABLE_VOX
    {"VOX",             ACTION_OPT_VOX},
#endif
#ifdef ENABLE_ALARM
    {"ALARM",           ACTION_OPT_ALARM},
#endif
#ifdef ENABLE_FMRADIO
    {WRX_ACTION_FM,        ACTION_OPT_FM},
#endif
#ifdef ENABLE_TX1750
    {"1750Hz",          ACTION_OPT_1750},
#endif
    {WRX_ACTION_LOCK_KEYPAD,    ACTION_OPT_KEYLOCK},
    {WRX_ACTION_VFO_A_B,    ACTION_OPT_A_B},
    {WRX_ACTION_VFO_MEM,        ACTION_OPT_VFO_MR},
    {WRX_ACTION_MODE,            ACTION_OPT_SWITCH_DEMODUL},
#ifdef ENABLE_BLMIN_TMP_OFF
    {"BLMIN\nTMP OFF",  ACTION_OPT_BLMIN_TMP_OFF},      //BackLight Minimum Temporary OFF
#endif
#ifdef ENABLE_FEAT_F4HWN
    {WRX_ACTION_RX_MODE,         ACTION_OPT_RXMODE},
    {WRX_ACTION_MAIN_ONLY,       ACTION_OPT_MAINONLY},
#ifndef ENABLE_RX_ONLY
    {"PTT",             ACTION_OPT_PTT},
#endif
    {WRX_ACTION_WIDE_NARROW,    ACTION_OPT_WN},
    {WRX_ACTION_MUTE,            ACTION_OPT_MUTE},
    #ifdef ENABLE_FEAT_F4HWN_AUDIO
        {"RxA",            ACTION_OPT_RXA},
    #endif
    #ifdef ENABLE_FEAT_F4HWN_RESCUE_OPS
        {"POWER\nHIGH",    ACTION_OPT_POWER_HIGH},
        {"REMOVE\nOFFSET",  ACTION_OPT_REMOVE_OFFSET},
    #endif
    #ifdef ENABLE_FEAT_F4HWN_BEAM
        {"BEAM",            ACTION_OPT_BEAM},
    #endif
    #ifdef ENABLE_FEAT_F4HWN_RXTX_LOG
        {"RF LOG",          ACTION_OPT_RXTX_LOG},
    #endif
    #ifdef ENABLE_FEAT_F4HWN_FOXHUNT
        {"FOX HUNT\nBEACON", ACTION_OPT_FOXHUNT},
    #endif
#endif
};

const uint8_t gSubMenu_SIDEFUNCTIONS_size = ARRAY_SIZE(gSubMenu_SIDEFUNCTIONS);

bool    gIsInSubMenu;
uint8_t gMenuCursor;
uint8_t gMenuIndices[ARRAY_SIZE(MenuList)]; // Etape 1: table position affichee -> index MenuList (vue courante)

int UI_MENU_GetCurrentMenuId() {
#ifdef ENABLE_FEAT_F4HWN_MENU_CAT
    if (gMenuLevel == MENU_LEVEL_CAT)
        return 0xFF;   // pas d'item courant au niveau categories
#endif
    if(gMenuCursor < gMenuListCount)
        return MenuList[gMenuIndices[gMenuCursor]].menu_id;

    return MenuList[ARRAY_SIZE(MenuList)-1].menu_id;
}

uint8_t UI_MENU_GetMenuIdx(uint8_t id)
{
    for(uint8_t i = 0; i < ARRAY_SIZE(MenuList); i++)
        if(MenuList[i].menu_id == id)
            return i;
    return 0;
}

// Position dans la vue courante (gMenuIndices) du menu_id, ou gMenuCursor si absent.
// En vue All (identite) equivaut a UI_MENU_GetMenuIdx ; en vue categorie, donne la
// position filtree correcte.
uint8_t UI_MENU_GetViewPos(uint8_t id)
{
    for (uint8_t i = 0; i < gMenuListCount; i++)
        if (MenuList[gMenuIndices[i]].menu_id == id)
            return i;
    return gMenuCursor;
}

#ifdef ENABLE_FEAT_F4HWN_MENU_CAT
// --- Etape 2a : donnee du classement par categorie (cible Fusion) ---
// Chaque liste = les menu_id d'une categorie, DANS l'ordre d'affichage voulu
// (ex. SetPwr colle a Power). CAT_ALL n'a pas de liste : il reprend MenuList
// tel quel, donc ordre et numeros d'origine preserves.
const char *const CategoryNames[CAT_COUNT] = {
    [CAT_CHANNELS] = WRX_MENU_CATEGORY_CHANNELS,
    [CAT_SCAN]     = WRX_MENU_CATEGORY_SCAN,
    [CAT_KEYS]     = WRX_MENU_CATEGORY_KEYS,
    [CAT_POWER]    = WRX_MENU_CATEGORY_POWER,
    [CAT_DISPLAY]  = WRX_MENU_CATEGORY_DISPLAY,
    [CAT_TIMERS]   = WRX_MENU_CATEGORY_TIMERS,
    [CAT_AUDIO]    = WRX_MENU_CATEGORY_AUDIO,
    [CAT_RADIO]    = WRX_MENU_CATEGORY_RADIO,
    [CAT_DTMF]     = WRX_MENU_CATEGORY_DTMF,
    [CAT_SERVICE]  = WRX_MENU_CATEGORY_SERVICE,
    [CAT_ALL]      = WRX_MENU_CATEGORY_ALL,
};

// Les menu_id de sous-features optionnelles sont gardes exactement comme dans
// l'enum (menu.h) : sur un preset qui ne les compile pas, ils ne sont pas
// references (sinon build KO, ex. preset Custom). Les autres MENU_SET_* sont
// sous ENABLE_FEAT_F4HWN, garanti par la dependance CMake (App/CMakeLists.txt).
static const uint8_t CatChannels[] = {
    MENU_STEP, MENU_R_DCS, MENU_R_CTCS, MENU_W_N,
#ifdef ENABLE_RX_ONLY
    MENU_RX_EXT, MENU_RX_BANK, MENU_RX_BANK_SET,
#else
    MENU_TXP, MENU_SET_PWR, MENU_T_DCS, MENU_T_CTCS, MENU_SFT_D, MENU_OFFSET,
#endif
#ifdef ENABLE_FEAT_F4HWN_NARROWER
    MENU_SET_NFM,
#endif
    MENU_COMPAND, MENU_AM, MENU_LIST_CH,
    MENU_MEM_CH, MENU_DEL_CH, MENU_MEM_NAME,
};
static const uint8_t CatScan[]    = {
    MENU_S_LIST, MENU_S_PRI, MENU_S_PRI_CH_1, MENU_S_PRI_CH_2, MENU_SC_REV,
#ifdef ENABLE_FEAT_F4HWN_SCAN_FASTER
    MENU_SET_SCN,
#endif
};
static const uint8_t CatKeys[]    = {
    MENU_F1SHRT, MENU_F1LONG, MENU_F2SHRT, MENU_F2LONG, MENU_MLONG, MENU_AUTOLK, MENU_SET_LCK,
#ifdef ENABLE_FEAT_F4HWN_RESCUE_OPS
    MENU_SET_KEY,
#endif
#ifndef ENABLE_RX_ONLY
    MENU_SET_PTT, MENU_1_CALL,
#endif
};
static const uint8_t CatPower[]   = {
    MENU_SAVE, MENU_BAT_TXT,
#ifdef ENABLE_FEAT_F4HWN_SLEEP
    MENU_SET_OFF,
#endif
#ifdef ENABLE_FEAT_F4HWN_LOGO_SAV
    MENU_SET_SAV,
#endif
};
static const uint8_t CatDisplay[] = { MENU_MDF, MENU_PONMSG, MENU_ABR, MENU_ABR_MIN, MENU_ABR_MAX, MENU_ABR_ON_TX_RX, MENU_SET_CTR, MENU_SET_INV, MENU_SET_MET, MENU_SET_GUI, MENU_VOL };
static const uint8_t CatTimers[]  = { MENU_TOT, MENU_SET_TOT, MENU_SET_EOT, MENU_SET_TMR };
static const uint8_t CatAudio[]   = {
    MENU_MIC, MENU_MIC_BAR, MENU_BEEP,
#ifdef ENABLE_FEAT_F4HWN_VOL
    MENU_SET_VOL,
#endif
#ifdef ENABLE_FEAT_F4HWN_AUDIO
    MENU_SET_AUD,
#endif
};
static const uint8_t CatRadio[]   = { MENU_SQL, MENU_STE, MENU_RP_STE, MENU_ROGER, MENU_VOX, MENU_TDR };
static const uint8_t CatDtmf[]    = { MENU_UPCODE, MENU_DWCODE, MENU_D_ST, MENU_D_PRE, MENU_D_LIVE_DEC };
static const uint8_t CatService[] = { MENU_F_LOCK, MENU_350EN, MENU_BATCAL, MENU_BATTYP, MENU_SET_NAV, MENU_RESET };

typedef struct { const uint8_t *ids; uint8_t len; } cat_list_t;

static const cat_list_t CategoryLists[CAT_COUNT] = {
    [CAT_CHANNELS] = { CatChannels, ARRAY_SIZE(CatChannels) },
    [CAT_SCAN]     = { CatScan,     ARRAY_SIZE(CatScan)     },
    [CAT_KEYS]     = { CatKeys,     ARRAY_SIZE(CatKeys)     },
    [CAT_POWER]    = { CatPower,    ARRAY_SIZE(CatPower)    },
    [CAT_DISPLAY]  = { CatDisplay,  ARRAY_SIZE(CatDisplay)  },
    [CAT_TIMERS]   = { CatTimers,   ARRAY_SIZE(CatTimers)   },
    [CAT_AUDIO]    = { CatAudio,    ARRAY_SIZE(CatAudio)    },
    [CAT_RADIO]    = { CatRadio,    ARRAY_SIZE(CatRadio)    },
    [CAT_DTMF]     = { CatDtmf,     ARRAY_SIZE(CatDtmf)     },
    [CAT_SERVICE]  = { CatService,  ARRAY_SIZE(CatService)  },
    [CAT_ALL]      = { NULL, 0 },
};

uint8_t gMenuCategory = CAT_ALL;

// Index de 'id' dans MenuList, ou 0xFF si absent (item non compile).
static uint8_t menu_find_idx(uint8_t id)
{
    for (uint8_t i = 0; MenuList[i].name[0] != '\0'; i++)
        if (MenuList[i].menu_id == id)
            return i;
    return 0xFF;
}

uint8_t gMenuLevel     = MENU_LEVEL_CAT;
uint8_t gCatOrder[CAT_COUNT];
uint8_t gMenuCatCursor = 0;
uint8_t gCatLastPos[CAT_COUNT];   // derniere position du curseur item, par categorie

// Nombre d'items presents (compiles) dans une categorie.
uint8_t UI_MENU_CategoryItemCount(uint8_t cat)
{
    uint8_t n = 0;

    if (cat == CAT_ALL)
    {
        for (uint8_t i = 0; MenuList[i].name[0] != '\0'; i++)
        {
            if (!gF_LOCK && MenuList[i].menu_id == FIRST_HIDDEN_MENU_ITEM)
                break;
            n++;
        }
        return n;
    }

    const cat_list_t *cl = &CategoryLists[cat];
    for (uint8_t k = 0; k < cl->len; k++)
        if (menu_find_idx(cl->ids[k]) != 0xFF)
            n++;
    return n;
}

// Construit l'ecran niveau categories : gCatOrder = categories visibles,
// gMenuListCount = leur nombre. Service n'apparait que si gF_LOCK.
void UI_MENU_BuildCategoryScreen(void)
{
    gMenuListCount = 0;
    for (uint8_t c = 0; c < CAT_COUNT; c++)
    {
        if (c == CAT_SERVICE && !gF_LOCK)
            continue;
        if (UI_MENU_CategoryItemCount(c) == 0)
            continue;
        gCatOrder[gMenuListCount++] = c;
    }
}

// Rendu de l'ecran des categories (niveau 1).
static void UI_MENU_DrawCategories(void)
{
    char str[16];
    const unsigned int sep = 64;          // separateur decale a droite : noms longs (ex. "Channels")
    const unsigned int x1  = sep + 2;
    const unsigned int x2  = LCD_WIDTH - 1;

    UI_DisplayClear();

    UI_DrawLineBuffer(gFrameBuffer, sep, 0, sep, 55, 1);
    for (uint8_t i = 0; i < sep; i += 2)
        gFrameBuffer[5][i] = 0x40;

    const int count = gMenuListCount;
    const int cur   = gMenuCursor;

    int prev = cur - 1; if (prev < 0)      prev = count - 1;
    int next = cur + 1; if (next >= count) next = 0;

    if (count > 1)
        UI_PrintStringSmallNormal(CategoryNames[gCatOrder[prev]], 0, 0, 1);
    UI_MENU_PrintString(CategoryNames[gCatOrder[cur]], 0, 0, 2, 8);
    if (count > 1)
        UI_PrintStringSmallNormal(CategoryNames[gCatOrder[next]], 0, 0, 4);

    sprintf(str, "%02u/%02u", 1 + cur, count);
    UI_PrintStringSmallNormal(str, 6, 0, 6);

    sprintf(str, "%02u", UI_MENU_CategoryItemCount(gCatOrder[cur]));
    UI_MENU_PrintString(str, x1, x2, 1, 8);
    UI_PrintStringSmallNormal(WRX_UI_TEXT_ITEMS, x1, x2, 5);

    ST7565_BlitFullScreen();
}
#endif

// Construit la "vue" courante = table position affichee -> index MenuList.
// Unique endroit qui fixe gMenuListCount + gMenuIndices.
// CAT_ALL (defaut) = liste plate, identite -> ordre/numeros d'origine preserves.
void UI_MENU_BuildView(void)
{
    gMenuListCount = 0;

#ifdef ENABLE_FEAT_F4HWN_MENU_CAT
    if (gMenuCategory != CAT_ALL)
    {
        const cat_list_t *cl = &CategoryLists[gMenuCategory];
        for (uint8_t k = 0; k < cl->len; k++)
        {
            uint8_t idx = menu_find_idx(cl->ids[k]);
            if (idx != 0xFF)
                gMenuIndices[gMenuListCount++] = idx;
        }
        return;
    }
#endif

    for (uint8_t i = 0; MenuList[i].name[0] != '\0'; i++)
    {
        if (!gF_LOCK && MenuList[i].menu_id == FIRST_HIDDEN_MENU_ITEM)
            break;

        gMenuIndices[gMenuListCount++] = i;
    }
}

int32_t gSubMenuSelection;

// edit box
char    edit_original[17]; // a copy of the text before editing so that we can easily test for changes/difference
char    edit[17];
int     edit_index;
bool    edit_is_uppercase = false;

static const char *UI_MENU_GetRxHelp(const int menuId)
{
    switch (menuId)
    {
        case MENU_SQL:         return WRX_MENU_HELP_SQL;
        case MENU_W_N:         return WRX_MENU_HELP_W_N;
        case MENU_LIST_CH:     return WRX_MENU_HELP_CHANNEL_LIST;
        case MENU_R_CTCS:      return WRX_MENU_HELP_CTCS;
#ifdef ENABLE_RX_ONLY
        case MENU_RX_EXT:      return WRX_MENU_HELP_RX_EXT;
        case MENU_RX_BANK:     return WRX_MENU_HELP_RX_BANK;
        case MENU_RX_BANK_SET: return WRX_MENU_HELP_RX_BANK_SET;
#endif
        default:               return NULL;
    }
}

#define UI_MENU_HELP_WIDTH 15u

static uint8_t gMenuHelpOffset;

static void UI_MENU_DrawRxHelp(const char *help)
{
    char visible[UI_MENU_HELP_WIDTH + 1u] = {0};
    const size_t length = strlen(help);

    // The menu number occupies the left edge of this row.  Clear the rest
    // before drawing so an old, longer help line cannot remain on screen.
    memset(gFrameBuffer[6] + 18, 0, LCD_WIDTH - 18);

    if (length > UI_MENU_HELP_WIDTH)
    {
        const size_t cycle = length + 1u; // one blank separator
        for (size_t i = 0; i < UI_MENU_HELP_WIDTH; i++)
        {
            const size_t position = (gMenuHelpOffset + i) % cycle;
            visible[i] = (position < length) ? help[position] : ' ';
        }
    }
    else
    {
        strncpy(visible, help, UI_MENU_HELP_WIDTH);
    }

    // End == 0 disables centering and keeps the 15-character window inside
    // the 128-pixel display (18 + 15 * 7 <= 127).
    UI_PrintStringSmallNormal(visible, 18, 0, 6);
}

void UI_MENU_TimeSlice500ms(void)
{
    const char *help = UI_MENU_GetRxHelp(UI_MENU_GetCurrentMenuId());
    const size_t length = (help == NULL) ? 0u : strlen(help);

    if (gScreenToDisplay != DISPLAY_MENU || length <= UI_MENU_HELP_WIDTH)
    {
        if (gMenuHelpOffset != 0)
        {
            gMenuHelpOffset = 0;
            gUpdateDisplay = true;
        }
        return;
    }

    gMenuHelpOffset = (gMenuHelpOffset + 1u) % (length + 1u);
    gUpdateDisplay = true;
}

static void UI_MENU_DrawTopRightRoundedBadge(const char *text, const uint8_t line, const bool center_in_area, const uint8_t area_x1, const uint8_t area_x2)
{
    const size_t length = strlen(text);
    const size_t char_pitch = ARRAY_SIZE(gFontSmall[0]) + 1u;
    const size_t text_width = length * char_pitch;
    const size_t capsule_span = text_width + 1u; // matches UI_PrintStringSmallNormalInverse x_end computation
    uint8_t text_x;

    if (length == 0 || line == 0 || line >= FRAME_LINES) {
        return;
    }

    if (center_in_area && area_x2 > area_x1 + 2u) {
        const uint8_t min_x = area_x1 + 1u;
        uint8_t max_x;
        const uint8_t area_width = area_x2 - area_x1 + 1u;

        if (capsule_span >= area_width) {
            text_x = min_x;
        } else {
            text_x = (uint8_t)(area_x1 + ((area_width - capsule_span) / 2u));
        }

        if (area_x2 > capsule_span) {
            max_x = (uint8_t)(area_x2 - capsule_span);
        } else {
            max_x = min_x;
        }

        if (max_x < min_x) {
            max_x = min_x;
        }
        if (text_x < min_x) {
            text_x = min_x;
        } else if (text_x > max_x) {
            text_x = max_x;
        }
    } else {
        if (capsule_span >= (LCD_WIDTH - 3u)) {
            text_x = 1u;
        } else {
            const uint8_t global_shift_right = 1u;
            const uint8_t base_text_x = (uint8_t)(LCD_WIDTH - capsule_span - 3u);
            const uint8_t max_text_x  = (uint8_t)(LCD_WIDTH - capsule_span - 1u);
            const uint16_t shifted_x = (uint16_t)base_text_x + global_shift_right;

            if (shifted_x > max_text_x) {
                text_x = max_text_x;
            } else {
                text_x = (uint8_t)shifted_x;
            }
        }
    }

    UI_PrintStringSmallNormalInverse(text, text_x, 0, line);
}

void UI_DisplayMenu(void)
{
    const unsigned int menu_list_width = 6; // max no. of characters on the menu list (left side)
    const unsigned int menu_item_x1    = (8 * menu_list_width) + 2;
    const unsigned int menu_item_x2    = LCD_WIDTH - 1;
    unsigned int       i;
    char               String[64];  // bigger cuz we can now do multi-line in one string (use '\n' char)
    char               top_right_badge[16];

#ifdef ENABLE_FEAT_F4HWN_MENU_CAT
    if (gMenuLevel == MENU_LEVEL_CAT)
    {
        UI_MENU_DrawCategories();
        return;
    }
#endif

    const int m = UI_MENU_GetCurrentMenuId();

#ifdef ENABLE_DTMF_CALLING
    char               Contact[16];
#endif

    UI_DisplayClear();

#ifdef ENABLE_FEAT_F4HWN
    UI_DrawLineBuffer(gFrameBuffer, 48, 0, 48, 55, 1); // Be ware, status zone = 8 lines, the rest = 56 ->total 64
    //UI_DrawLineDottedBuffer(gFrameBuffer, 0, 46, 50, 46, 1);

    for (uint8_t i = 0; i < 48; i += 2)
    {
        gFrameBuffer[5][i] = 0x40;
    }
#endif

#ifndef ENABLE_CUSTOM_MENU_LAYOUT
        // original menu layout
    for (i = 0; i < 3; i++)
        if (gMenuCursor > 0 || i > 0)
            if ((gMenuListCount - 1) != gMenuCursor || i != 2)
                UI_MENU_PrintString(MenuList[gMenuIndices[gMenuCursor + i - 1]].name,
                                    0, 0, i * 2, 8);

    // invert the current menu list item pixels
    for (i = 0; i < (8 * menu_list_width); i++)
    {
        gFrameBuffer[2][i] ^= 0xFF;
        gFrameBuffer[3][i] ^= 0xFF;
    }

    // draw vertical separating dotted line
    for (i = 0; i < 7; i++)
        gFrameBuffer[i][(8 * menu_list_width) + 1] = 0xAA;

    // draw the little sub-menu triangle marker
    if (gIsInSubMenu)
        memcpy(gFrameBuffer[0] + (8 * menu_list_width) + 1, BITMAP_CurrentIndicator, sizeof(BITMAP_CurrentIndicator));

    // draw the menu index number/count
    sprintf(String, "%2u.%u", 1 + gMenuCursor, gMenuListCount);

    UI_PrintStringSmallNormal(String, 2, 0, 6);

#else
    {   // new menu layout .. experimental & unfinished
        const int menu_index = gMenuCursor;  // current selected menu item
        const int menu_count = (int)gMenuListCount;

        if (menu_index >= 0 && menu_index < menu_count) 
        {
            if (!gIsInSubMenu) 
            {
                // leading menu items - small text
                int prev_index = menu_index - 1;
                if (prev_index < 0) {
                    prev_index = menu_count - 1;
                }
                UI_PrintStringSmallNormalClipped(MenuList[gMenuIndices[prev_index]].name, 0, 47, 1);

                // current menu item - keep big n fat
                UI_MENU_PrintStringClipped(
                    MenuList[gMenuIndices[menu_index]].name, 0, 47, 2, 8);

                // trailing menu item - small text
                int next_index = menu_index + 1;
                if (next_index >= menu_count) {
                    next_index = 0;
                }
                UI_PrintStringSmallNormalClipped(MenuList[gMenuIndices[next_index]].name, 0, 47, 4);


                // draw the menu index number/count
    #ifndef ENABLE_FEAT_F4HWN
                sprintf(String, "%2u.%u", 1 + menu_index, menu_count);
                UI_PrintStringSmallNormal(String, 2, 0, 6);
    #endif
            }
            else
            {   
                // current menu item
//              strcat(String, ":");
                UI_MENU_PrintStringClipped(
                    MenuList[gMenuIndices[menu_index]].name, 0, 47, 0, 8);
//              UI_PrintStringSmallNormal(String, 0, 0, 0);
            }

    #ifdef ENABLE_FEAT_F4HWN
            sprintf(String, "%02u/%02u", 1 + menu_index, menu_count);
            UI_PrintStringSmallNormal(String, 6, 0, 6);
    #endif
        }
    }
#endif

    // **************

    String[0] = '\0';
    top_right_badge[0] = '\0';

    bool already_printed = false;

    /* Brightness is set to max in some entries of this menu. Return it to the configured brightness
       level the "next" time we enter here.I.e., when we move from one menu to another.
       It also has to be set back to max when pressing the Exit key. */

    BACKLIGHT_TurnOn();

    //#if !defined(ENABLE_SPECTRUM) || !defined(ENABLE_FMRADIO)
        uint8_t gaugeLine = 0;
        uint8_t gaugeMin = 0;
        uint8_t gaugeMax = 0;
    //#endif

    switch (m)
    {
        case MENU_SQL:
#ifdef ENABLE_RX_ONLY
            if (gSubMenuSelection == 10)
 #ifdef ENABLE_JAPANESE
            {
                const char auto_name[] = {0xEB, 0xEC, 0}; // 自動
                strcpy(String, auto_name);
            }
 #else
                strcpy(String, "AUTO");
 #endif
            else
                sprintf(String, "%d", gSubMenuSelection);
#else
            sprintf(String, "%d", gSubMenuSelection);
#endif
            break;

        case MENU_MIC:
            {   // display the mic gain in actual dB rather than just an index number
                const uint8_t mic = gMicGain_dB2[gSubMenuSelection];
                sprintf(String, "+%u.%udB", mic / 2, (mic % 2) * 5);

                gaugeLine = 4;
                gaugeMin = 0;
                gaugeMax = 8;
            }
            break;

        case MENU_MIC_BAR:
            #ifdef ENABLE_AUDIO_BAR
                strcpy(String, gSubMenu_OFF_ON[gSubMenuSelection]);
            #else
                strcpy(String, gSubMenu_NA);
            #endif
            break;

        case MENU_STEP: {
            uint16_t step = gStepFrequencyTable[FREQUENCY_GetStepIdxFromSortedIdx(gSubMenuSelection)];
            sprintf(String, "%d.%02ukHz", step / 100, step % 100);
            break;
        }

        case MENU_TXP:
            if(gSubMenuSelection == 0)
            {
                strcpy(String, gSubMenu_TXP[gSubMenuSelection]);
            }
            else
            {
                sprintf(String, "%s\n%sW", gSubMenu_TXP[gSubMenuSelection], gSubMenu_SET_PWR[gSubMenuSelection - 1]);
            }
            break;

        case MENU_R_DCS:
        case MENU_T_DCS:
            if (gSubMenuSelection == 0)
                strcpy(String, gSubMenu_OFF_ON[0]);
            else if (gSubMenuSelection < 105)
                sprintf(String, "D%03oN", DCS_Options[gSubMenuSelection -   1]);
            else
                sprintf(String, "D%03oI", DCS_Options[gSubMenuSelection - 105]);
            break;

        case MENU_R_CTCS:
        case MENU_T_CTCS:
        {
            if (gSubMenuSelection == 0)
                strcpy(String, gSubMenu_OFF_ON[0]);
            else if (gSubMenuSelection <= (int32_t)ARRAY_SIZE(CTCSS_Options))
                sprintf(String, "%u.%uHz", CTCSS_Options[gSubMenuSelection - 1] / 10, CTCSS_Options[gSubMenuSelection - 1] % 10);
            else
                sprintf(String, "R%u.%uHz", CTCSS_Options[gSubMenuSelection - ARRAY_SIZE(CTCSS_Options) - 1] / 10, CTCSS_Options[gSubMenuSelection - ARRAY_SIZE(CTCSS_Options) - 1] % 10);
            break;
        }

        case MENU_SFT_D:
            strcpy(String, gSubMenu_SFT_D[gSubMenuSelection]);
            break;

        case MENU_OFFSET:
            if (!gIsInSubMenu || gInputBoxIndex == 0)
            {
                sprintf(String, "%3d.%05u", gSubMenuSelection / 100000, abs(gSubMenuSelection) % 100000);
            }
            else
            {
                const char * ascii = INPUTBOX_GetAscii();
                sprintf(String, "%.3s.%.3s  ",ascii, ascii + 3);
            }

            UI_MENU_PrintString(String, menu_item_x1, menu_item_x2, 1, 8);
            UI_MENU_PrintString("MHz",  menu_item_x1, menu_item_x2, 3, 8);

            already_printed = true;
            break;

        case MENU_W_N:
            strcpy(String, gSubMenu_W_N[gSubMenuSelection]);
            break;

#ifdef ENABLE_RX_ONLY
        case MENU_RX_EXT:
            strcpy(String, gSubMenu_OFF_ON[gSubMenuSelection]);
            break;
#endif

#ifndef ENABLE_FEAT_F4HWN
        case MENU_SCR:
            strcpy(String, gSubMenu_SCRAMBLER[gSubMenuSelection]);
            #if 1
                if (gSubMenuSelection > 0 && gSetting_ScrambleEnable)
                    BK4819_EnableScramble(gSubMenuSelection - 1);
                else
                    BK4819_DisableScramble();
            #endif
            break;
#endif

        case MENU_VOX:
            #ifdef ENABLE_VOX
                sprintf(String, gSubMenuSelection == 0 ? gSubMenu_OFF_ON[0] : "%u", gSubMenuSelection);
            #else
                strcpy(String, gSubMenu_NA);
            #endif
            break;

        case MENU_ABR:
            if(gSubMenuSelection == 0)
            {
                strcpy(String, gSubMenu_OFF_ON[0]);
            }
            else if(gSubMenuSelection < 61)
            {
                sprintf(String, "%02dm:%02ds", (((gSubMenuSelection) * 5) / 60), (((gSubMenuSelection) * 5) % 60));
                //#if !defined(ENABLE_SPECTRUM) || !defined(ENABLE_FMRADIO)
                //ST7565_Gauge(4, 1, 60, gSubMenuSelection);
                gaugeLine = 4;
                gaugeMin = 1;
                gaugeMax = 60;
                //#endif
            }
            else
            {
                strcpy(String, "ON");
            }

            // Obsolete ???
            //if(BACKLIGHT_GetBrightness() < 4)
            //    BACKLIGHT_SetBrightness(4);
            break;

        case MENU_ABR_MIN:
        case MENU_ABR_MAX:
            sprintf(String, "%d", gSubMenuSelection);
            if(gIsInSubMenu)
                BACKLIGHT_SetBrightness(gSubMenuSelection);
            // Obsolete ???
            //else if(BACKLIGHT_GetBrightness() < 4)
            //    BACKLIGHT_SetBrightness(4);
            break;

        case MENU_AM:
            strcpy(String, gModulationStr[gSubMenuSelection]);
            break;

        case MENU_AUTOLK:
            if (gSubMenuSelection == 0)
                strcpy(String, gSubMenu_OFF_ON[0]);
            else
            {
                sprintf(String, "%02dm:%02ds", ((gSubMenuSelection * 15) / 60), ((gSubMenuSelection * 15) % 60));
                //#if !defined(ENABLE_SPECTRUM) || !defined(ENABLE_FMRADIO)
                //ST7565_Gauge(4, 1, 40, gSubMenuSelection);
                gaugeLine = 4;
                gaugeMin = 1;
                gaugeMax = 40;
                //#endif
            }
            break;

        case MENU_COMPAND:
        case MENU_ABR_ON_TX_RX:
            strcpy(String, gSubMenu_RX_TX[gSubMenuSelection]);
            break;

        #ifndef ENABLE_FEAT_F4HWN
            #ifdef ENABLE_AM_FIX
                case MENU_AM_FIX:
            #endif
        #endif
        case MENU_BCL:
        case MENU_BEEP:
        case MENU_STE:
        case MENU_D_ST:
#ifdef ENABLE_DTMF_CALLING
        case MENU_D_DCD:
#endif
        case MENU_D_LIVE_DEC:
        #ifdef ENABLE_NOAA
            case MENU_NOAA_S:
        #endif
#ifndef ENABLE_FEAT_F4HWN
        case MENU_350TX:
        case MENU_200TX:
        case MENU_500TX:
#endif
        case MENU_350EN:
#ifndef ENABLE_FEAT_F4HWN
        case MENU_SCREN:
#endif
#ifdef ENABLE_FEAT_F4HWN
        case MENU_SET_TMR:
        case MENU_S_PRI:
#endif
            strcpy(String, gSubMenu_OFF_ON[gSubMenuSelection]);
            break;

#if defined(ENABLE_FEAT_F4HWN) && defined(ENABLE_FEAT_F4HWN_LOGO_SAV)
        case MENU_SET_SAV:
            strcpy(String, gSubMenu_SET_SAV[gSubMenuSelection]);
            break;
#endif

        case MENU_MEM_CH:
        case MENU_1_CALL:
        case MENU_DEL_CH:
        case MENU_S_PRI_CH_1:
        case MENU_S_PRI_CH_2:
        {
            if(gSubMenuSelection == MR_CHANNELS_MAX)
            {
                UI_MENU_PrintString(WRX_UI_TEXT_NONE, menu_item_x1, menu_item_x2, 2, 8);
                already_printed = true;
                break;
            }
            else
            {
                const bool valid = RADIO_CheckValidChannel(gSubMenuSelection, false, 0);

                UI_GenerateChannelStringEx(String, valid, gSubMenuSelection);
                UI_MENU_PrintString(String, menu_item_x1, menu_item_x2, 0, 8);

                if (valid && !gAskForConfirmation)
                {   // show the frequency so that the user knows the channels frequency
                    const uint32_t frequency = SETTINGS_FetchChannelFrequency(gSubMenuSelection);
                    sprintf(String, "%u.%05u", frequency / 100000, frequency % 100000);
                    UI_MENU_PrintString(String, menu_item_x1, menu_item_x2, 5, 8);
                }

#ifdef ENABLE_JAPANESE
                if (!UI_PrintJapaneseChannelName(gSubMenuSelection,
                                                 menu_item_x1, menu_item_x2, 2))
#endif
                {
                    SETTINGS_FetchChannelName(String, gSubMenuSelection);
                    UI_MENU_PrintString(String[0] ? String : "--", menu_item_x1, menu_item_x2, 2, 8);
                }
                already_printed = true;
                break;
            }
        }

        case MENU_MEM_NAME:
        {
            const bool valid = RADIO_CheckValidChannel(gSubMenuSelection, false, 0);

            UI_GenerateChannelStringEx(String, valid, gSubMenuSelection);
            UI_MENU_PrintString(String, menu_item_x1, menu_item_x2, 0, 8);

            if (valid)
            {
                const uint32_t frequency = SETTINGS_FetchChannelFrequency(gSubMenuSelection);

                //if (!gIsInSubMenu || edit_index < 0)
                if (!gIsInSubMenu)
                    edit_index = -1;
                if (edit_index < 0)
                {   // show the channel name
#ifdef ENABLE_JAPANESE
                    if (!UI_PrintJapaneseChannelName(gSubMenuSelection,
                                                     menu_item_x1, menu_item_x2, 2))
#endif
                    {
                        SETTINGS_FetchChannelName(String, gSubMenuSelection);
                        char *pPrintStr = String[0] ? String : "--";
                        UI_MENU_PrintString(pPrintStr, menu_item_x1, menu_item_x2, 2, 8);
                    }
                }
                else
                {   // show the channel name being edited
                    //UI_PrintString(edit, menu_item_x1, 0, 2, 8);
                    UI_MENU_PrintString(edit, menu_item_x1, menu_item_x2, 2, 8);
                    if (edit_index < 10) {
                        // UI_PrintString("^", menu_item_x1 - 1 + (8 * edit_index),0, 4, 8); // show the cursor
                        uint8_t x = menu_item_x1 - 1;
                        for (uint8_t i = 0; i < 10; i++) 
                        {
                            if (i != edit_index) 
                            {
                                if (edit[i] != 'g' && edit[i] != 'j')
                                {
                                    UI_DrawLineBuffer(gFrameBuffer, x, 29, x + 6, 29, 1);
                                }
                            }
                            else 
                            {
                                UI_DrawLineBuffer(gFrameBuffer, x + 2, 30, x + 4, 30, 1);
                                UI_DrawPixelBuffer(gFrameBuffer, x + 3, 29, 1);
                            }
                            x += 8;
                        }
                        
                        UI_PrintStringSmallNormal(edit_is_uppercase ? "ABC" : "abc", 77, 0, 4);
                    }
                }

                if (!gAskForConfirmation)
                {   // show the frequency so that the user knows the channels frequency
                    sprintf(String, "%u.%05u", frequency / 100000, frequency % 100000);
                    UI_MENU_PrintString(String, menu_item_x1, menu_item_x2, 5, 8);
                }
            }

            already_printed = true;
            break;
        }

        case MENU_SAVE:
            sprintf(String, gSubMenuSelection == 0 ? gSubMenu_OFF_ON[0] : "1:%u", gSubMenuSelection);
            break;

        case MENU_TDR:
            strcpy(String, gSubMenu_RXMode[gSubMenuSelection]);
            break;

        case MENU_TOT:
            sprintf(String, "%02dm:%02ds", (((gSubMenuSelection + 1) * 5) / 60), (((gSubMenuSelection + 1) * 5) % 60));
            //#if !defined(ENABLE_SPECTRUM) || !defined(ENABLE_FMRADIO)
            //ST7565_Gauge(4, 5, 179, gSubMenuSelection);
            gaugeLine = 4;
            gaugeMin = 5;
            gaugeMax = 179;
            //#endif
            break;

        #ifdef ENABLE_VOICE
            case MENU_VOICE:
                strcpy(String, gSubMenu_VOICE[gSubMenuSelection]);
                break;
        #endif

        case MENU_SC_REV:
            if(gSubMenuSelection == 0)
            {
                strcpy(String, WRX_UI_TEXT_SCAN_STOP);
            }
            else if(gSubMenuSelection < 81)
            {
                sprintf(String, "%s\n%02ds:%03dms", WRX_UI_TEXT_SCAN_CARRIER,
                        ((gSubMenuSelection * 250) / 1000),
                        ((gSubMenuSelection * 250) % 1000));
                //#if !defined(ENABLE_SPECTRUM) || !defined(ENABLE_FMRADIO)
                //ST7565_Gauge(5, 1, 80, gSubMenuSelection);
                gaugeLine = 5;
                gaugeMin = 1;
                gaugeMax = 80;
                //#endif
            }
            else
            {
                sprintf(String, "%s\n%02dm:%02ds", WRX_UI_TEXT_SCAN_TIMEOUT,
                        (((gSubMenuSelection - 80) * 5) / 60),
                        (((gSubMenuSelection - 80) * 5) % 60));
                //#if !defined(ENABLE_SPECTRUM) || !defined(ENABLE_FMRADIO)
                //ST7565_Gauge(5, 80, 104, gSubMenuSelection);
                gaugeLine = 5;
                gaugeMin = 80;
                gaugeMax = 104;
                //#endif
            }
            break;

        case MENU_MDF:
            strcpy(String, gSubMenu_MDF[gSubMenuSelection]);
            break;

        case MENU_RP_STE:
            sprintf(String, gSubMenuSelection == 0 ? gSubMenu_OFF_ON[0] : "%u*100ms", gSubMenuSelection);
            break;

        case MENU_LIST_CH:
        case MENU_S_LIST:
            if (gSubMenuSelection == MR_CHANNELS_LIST + 1)
                strcpy(String, "ALL");
            else if (gSubMenuSelection == 0 && m == MENU_LIST_CH)
                strcpy(String, "OFF");
            else {
                const char *name = gListName[gSubMenuSelection - 1];
                
                // If first character is empty/invalid, display "N/A"
                if (IsEmptyName(name, sizeof(gListName[0])))
                    sprintf(String, "%02u", gSubMenuSelection);
                else
                    sprintf(String, "%02u (%.3s)", gSubMenuSelection, name);
            }
            break;
            
        #ifdef ENABLE_ALARM
            case MENU_AL_MOD:
                sprintf(String, gSubMenu_AL_MOD[gSubMenuSelection]);
                break;
        #endif

#ifdef ENABLE_DTMF_CALLING
        case MENU_ANI_ID:
            strcpy(String, gEeprom.ANI_DTMF_ID);
            break;
#endif
        case MENU_UPCODE:
            if (gEeprom.DTMF_UP_CODE[8] != '\0' && gEeprom.DTMF_UP_CODE[8] != 0xFF) {
                sprintf(String, "%.8s\n%.8s", gEeprom.DTMF_UP_CODE, gEeprom.DTMF_UP_CODE + 8);
            } else {
                sprintf(String, "%.8s", gEeprom.DTMF_UP_CODE);
            }
            break;

        case MENU_DWCODE:
            if (gEeprom.DTMF_DOWN_CODE[8] != '\0' && gEeprom.DTMF_DOWN_CODE[8] != 0xFF) {
                sprintf(String, "%.8s\n%.8s", gEeprom.DTMF_DOWN_CODE, gEeprom.DTMF_DOWN_CODE + 8);
            } else {
                sprintf(String, "%.8s", gEeprom.DTMF_DOWN_CODE);
            }
            break;

#ifdef ENABLE_DTMF_CALLING
        case MENU_D_RSP:
            strcpy(String, gSubMenu_D_RSP[gSubMenuSelection]);
            break;

        case MENU_D_HOLD:
            sprintf(String, "%ds", gSubMenuSelection);
            break;
#endif
        case MENU_D_PRE:
            sprintf(String, "%d*10ms", gSubMenuSelection);
            break;

        case MENU_PTT_ID:
            strcpy(String, gSubMenu_PTT_ID[gSubMenuSelection]);
            break;

        case MENU_BAT_TXT:
            strcpy(String, gSubMenu_BAT_TXT[gSubMenuSelection]);
            break;

#ifdef ENABLE_DTMF_CALLING
        case MENU_D_LIST:
            gIsDtmfContactValid = DTMF_GetContact((int)gSubMenuSelection - 1, Contact);
            if (!gIsDtmfContactValid)
                strcpy(String, "NULL");
            else
                memcpy(String, Contact, 8);
            break;
#endif

        case MENU_PONMSG:
            strcpy(String, gSubMenu_PONMSG[gSubMenuSelection]);
            break;

        case MENU_ROGER:
            strcpy(String, gSubMenu_ROGER[gSubMenuSelection]);
            break;

        case MENU_VOL: {
            // SysInf is paginated. Pages appear in this order, only when their
            // feature flag is enabled:
            //   0          -> identity
            //   next       -> Build date/time         (ENABLE_FEAT_F4HWN)
            //   next       -> Battery                 (ENABLE_FEAT_F4HWN)
            //   next       -> Flash / SRAM usage      (ENABLE_FEAT_F4HWN_MEM)
            //   next, +1   -> CODE / WIKI QR codes    (ENABLE_FEAT_F4HWN_QRCODE)
            // In non-F4HWN builds, page 0 keeps the old battery-voltage display.
            const uint8_t page = (uint8_t)gSubMenuSelection;
            uint8_t       p    = 0;

            if (page == p++) {
                // Page 0: firmware identity.
#ifdef ENABLE_FEAT_F4HWN
                sprintf(String, "%s\n%s", AUTHOR_STRING_2, DISPLAY_VERSION_STRING_2);
                UI_PrintStringSmallNormal(Edition, menu_item_x1 - 1, menu_item_x2, 6);
#else
                sprintf(String, "%u.%02uV\n%u%%",
                    gBatteryVoltageAverage / 100, gBatteryVoltageAverage % 100,
                    BATTERY_VoltsToPercent(gBatteryVoltageAverage));
#endif
                break;
            }
#ifdef ENABLE_FEAT_F4HWN
            if (page == p++) {
                strcpy(top_right_badge, "BUILD");
                UI_PrintStringSmallNormal(BuildDate, menu_item_x1 - 1, menu_item_x2, 3);
                UI_PrintStringSmallNormal(BuildTime, menu_item_x1 - 1, menu_item_x2, 4);
                UI_PrintStringSmallNormal(BuildCommit, menu_item_x1 - 1, menu_item_x2, 6);

                already_printed = true;
                break;
            }

            if (page == p++) {
                char val[16];

 #ifdef ENABLE_JAPANESE
                {
                    const char battery_name[] = {0x8F, 0xF7, 0}; // 電池
                    strcpy(top_right_badge, battery_name);
                }
 #else
                strcpy(top_right_badge, "BATTERY");
 #endif

                sprintf(val, "%u.%02uV %u%%",
                    gBatteryVoltageAverage / 100, gBatteryVoltageAverage % 100,
                    BATTERY_VoltsToPercent(gBatteryVoltageAverage));
                UI_PrintStringSmallNormal(val, menu_item_x1 - 1, menu_item_x2, 3);

                UI_PrintStringSmallNormal(gSubMenu_BATTYP[gEeprom.BATTERY_TYPE], menu_item_x1 - 1, menu_item_x2, 5);

                already_printed = true;
                break;
            }
#endif
#ifdef ENABLE_FEAT_F4HWN_MEM
            if (page == p++) {
                uint16_t flash_pct = 0;
                uint16_t ram_pct   = 0;
                UI_GetMemPercents(&flash_pct, &ram_pct);

                char val[16];

                // MEMORY title capsule centered in right zone, fb line 1.
                strcpy(top_right_badge, "MEMORY");

                // Flash + SRAM values stacked below, normal small font, with a fb-line of breathing space.
                sprintf(val, "FLASH %u.%u%%",
                        (unsigned)(flash_pct / 100), (unsigned)((flash_pct / 10) % 10));
                UI_PrintStringSmallNormal(val, menu_item_x1 - 1, menu_item_x2, 3);

                sprintf(val, "SRAM  %u.%u%%",
                        (unsigned)(ram_pct / 100), (unsigned)((ram_pct / 10) % 10));
                UI_PrintStringSmallNormal(val, menu_item_x1 - 1, menu_item_x2, 5);

                already_printed = true;
                break;
            }
#endif
#ifdef ENABLE_FEAT_F4HWN_QRCODE
            // Right zone: x=49..127 (79 px). QR centered at x=72..104.
            // Capsule label above QR (small-font Inverse style at fb line 1).
            if (page == p || page == p + 1) {
                const bool is_wiki = (page == (p + 1));

                strcpy(top_right_badge, is_wiki ? "WIKI" : "CODE");
                UI_DrawQRCode(is_wiki, 72, 28);
                
                already_printed = true;
                break;
            }

            p += 2; 
#endif
            break;
        }

        case MENU_RESET:
            strcpy(String, gSubMenu_RESET[gSubMenuSelection]);
            break;

        case MENU_F_LOCK:
#ifdef ENABLE_FEAT_F4HWN
            if(!gIsInSubMenu && gUnlockAllTxConfCnt>0 && gUnlockAllTxConfCnt<3)
#else
            if(!gIsInSubMenu && gUnlockAllTxConfCnt>0 && gUnlockAllTxConfCnt<10)
#endif
                strcpy(String, "READ\nMANUAL");
            else
                strcpy(String, gSubMenu_F_LOCK[gSubMenuSelection]);
            break;

        #ifdef ENABLE_F_CAL_MENU
            case MENU_F_CALI:
                {
                    const uint32_t value   = 22656 + gSubMenuSelection;
                    const uint32_t xtal_Hz = (0x4f0000u + value) * 5;

                    writeXtalFreqCal(gSubMenuSelection, false);

                    sprintf(String, "%d\n%u.%06u\nMHz",
                        gSubMenuSelection,
                        xtal_Hz / 1000000, xtal_Hz % 1000000);
                }
                break;
        #endif

        case MENU_BATCAL:
        {
            const uint16_t vol = (uint32_t)gBatteryVoltageAverage * gBatteryCalibration[3] / gSubMenuSelection;
            sprintf(String, "%u.%02uV\n%u", vol / 100, vol % 100, gSubMenuSelection);
            break;
        }

        case MENU_BATTYP:
            strcpy(String, gSubMenu_BATTYP[gSubMenuSelection]);
            break;

        case MENU_SET_NAV:
            strcpy(String, gSubMenu_SET_NAV[gSubMenuSelection]);
            break;

        case MENU_F1SHRT:
        case MENU_F1LONG:
        case MENU_F2SHRT:
        case MENU_F2LONG:
        case MENU_MLONG:
            strcpy(String, gSubMenu_SIDEFUNCTIONS[gSubMenuSelection].name);
            break;

#ifdef ENABLE_FEAT_F4HWN_SLEEP
        case MENU_SET_OFF:
            if(gSubMenuSelection == 0)
            {
                strcpy(String, gSubMenu_OFF_ON[0]);
            }
            else if(gSubMenuSelection < 121)
            {
                sprintf(String, "%dh:%02dm", (gSubMenuSelection / 60), (gSubMenuSelection % 60));
                //#if !defined(ENABLE_SPECTRUM) || !defined(ENABLE_FMRADIO)
                //ST7565_Gauge(4, 1, 120, gSubMenuSelection);
                gaugeLine = 4;
                gaugeMin = 1;
                gaugeMax = 120;
                //#endif
            }
            break;
#endif

#ifdef ENABLE_FEAT_F4HWN
        case MENU_SET_PWR:
            sprintf(String, "%s\n%sW", gSubMenu_TXP[gSubMenuSelection + 1], gSubMenu_SET_PWR[gSubMenuSelection]);
            break;
    
        case MENU_SET_PTT:
            strcpy(String, gSubMenu_SET_PTT[gSubMenuSelection]);
            break;

        case MENU_SET_TOT:
        case MENU_SET_EOT:
            strcpy(String, gSubMenu_SET_TOT[gSubMenuSelection]); // Same as SET_TOT
            break;

        case MENU_SET_CTR:
            #ifdef ENABLE_FEAT_F4HWN_CTR
                sprintf(String, "%d", gSubMenuSelection);
                gSetting_set_ctr = gSubMenuSelection;
                ST7565_ContrastAndInv();
            #else
                strcpy(String, gSubMenu_NA);
            #endif
            break;

        case MENU_SET_INV:
            #ifdef ENABLE_FEAT_F4HWN_INV
                strcpy(String, gSubMenu_OFF_ON[gSubMenuSelection]);
                ST7565_ContrastAndInv();
            #else
                strcpy(String, gSubMenu_NA);
            #endif
            break;

        case MENU_SET_LCK:
            strcpy(String, gSubMenu_SET_LCK[gSubMenuSelection]);
            break;

        case MENU_SET_MET:
        case MENU_SET_GUI:
            strcpy(String, gSubMenu_SET_MET[gSubMenuSelection]); // Same as SET_MET
            break;

        #ifdef ENABLE_FEAT_F4HWN_SCAN_FASTER
            case MENU_SET_SCN:
                strcpy(String, gSubMenu_SET_SCN[gSubMenuSelection]);
                break;
        #endif

        #ifdef ENABLE_FEAT_F4HWN_AUDIO
            case MENU_SET_AUD:
                if(gTxVfo->Modulation == MODULATION_AM) {
                    strcpy(String, gSubMenu_SET_AUD_AM[gSubMenuSelection]);
                    strcpy(top_right_badge, "AM");
                }
                else if (gTxVfo->Modulation == MODULATION_USB) {
                    strcpy(String, "USB");
                    strcpy(top_right_badge, "USB");
                }
                else {
                    strcpy(String, gSubMenu_SET_AUD_FM[gSubMenuSelection]);
                    strcpy(top_right_badge, "FM");
                }
                break;
        #endif

        #ifdef ENABLE_FEAT_F4HWN_NARROWER
            case MENU_SET_NFM:
                strcpy(String, gSubMenu_SET_NFM[gSubMenuSelection]);
                break;
        #endif

        #ifdef ENABLE_FEAT_F4HWN_VOL
            case MENU_SET_VOL:
                if(gSubMenuSelection == 0)
                {
                    strcpy(String, gSubMenu_OFF_ON[0]);
                }
                else if(gSubMenuSelection < 64)
                {
                    sprintf(String, "%02u", gSubMenuSelection);
                    //#if !defined(ENABLE_SPECTRUM) || !defined(ENABLE_FMRADIO)
                    //ST7565_Gauge(4, 1, 63, gSubMenuSelection);
                    gaugeLine = 4;
                    gaugeMin = 1;
                    gaugeMax = 63;
                    //#endif
                }
                // gEeprom.VOLUME_GAIN = gSubMenuSelection;
                BK4819_SetRxAudioGain();
                break;
        #endif

        #ifdef ENABLE_FEAT_F4HWN_RESCUE_OPS
            case MENU_SET_KEY:
                strcpy(String, gSubMenu_SET_KEY[gSubMenuSelection]);
                break;                
        #endif
#endif

    }

    //#if !defined(ENABLE_SPECTRUM) || !defined(ENABLE_FMRADIO)
    if(gaugeLine != 0)
    {
        ST7565_Gauge(gaugeLine, gaugeMin, gaugeMax, gSubMenuSelection);
    }
    //#endif

    if (!already_printed)
    {   // we now do multi-line text in a single string

        unsigned int y;
        unsigned int lines = 1;
        unsigned int len   = strlen(String);
        bool         small = false;

        if (String[0] != '\0')
        {
            // count number of lines
            for (i = 0; i < len; i++)
            {
                if (String[i] == '\n' && i < (len - 1))
                {   // found new line char
                    lines++;
                    String[i] = 0;  // null terminate the line
                }
            }

            if (lines > 3)
            {   // use small text
                small = true;
                if (lines > 7)
                    lines = 7;
            }

            // center vertically'ish
            /*
            if (small)
                y = 3 - ((lines + 0) / 2);  // untested
            else
                y = 2 - ((lines + 0) / 2);
            */

            y = (small ? 3 : 2) - (lines / 2); 

            // draw the text lines
            for (i = 0; i < len && lines > 0; lines--)
            {
                if (small)
                    UI_PrintStringSmallNormal(String + i, menu_item_x1, menu_item_x2, y);
                else
                    UI_MENU_PrintString(String + i, menu_item_x1, menu_item_x2, y, 8);

                // look for start of next line
                while (i < len && String[i] >= 32)
                    i++;

                // hop over the null term char(s)
                while (i < len && String[i] < 32)
                    i++;

                y += small ? 1 : 2;
            }
        }
    }

    if (m == MENU_S_PRI_CH_1 || m == MENU_S_PRI_CH_2)
    {

    }

    if ((m == MENU_R_CTCS || m == MENU_R_DCS) && gCssBackgroundScan)
        UI_MENU_PrintString("SCAN", menu_item_x1, menu_item_x2, 4, 8);

#ifdef ENABLE_DTMF_CALLING
    if (m == MENU_D_LIST && gIsDtmfContactValid) {
        Contact[11] = 0;
        memcpy(&gDTMF_ID, Contact + 8, 4);
        sprintf(String, "ID:%4s", gDTMF_ID);
        UI_MENU_PrintString(String, menu_item_x1, menu_item_x2, 4, 8);
    }
#endif

    const bool is_ctcs = (m == MENU_R_CTCS || m == MENU_T_CTCS);
    const bool is_dcs  = (m == MENU_R_DCS  || m == MENU_T_DCS);

    if (is_ctcs || is_dcs) {
        if (gSubMenuSelection == 0) {
            strcpy(top_right_badge, is_ctcs ? "00/00" : "000/00");
        } else if (is_ctcs && gSubMenuSelection > ARRAY_SIZE(CTCSS_Options)) {
            sprintf(top_right_badge, "R/%02u", (unsigned)(gSubMenuSelection - ARRAY_SIZE(CTCSS_Options)));
        } else {
            const uint8_t approved_index = is_ctcs ? 
                DCS_GetCtcssApprovedIndex(gSubMenuSelection - 1) : 
                DCS_GetDcsApprovedIndex(gSubMenuSelection - 1);
                
            const uint8_t width = is_ctcs ? 2 : 3;

            if (approved_index != 0xFF) {
                sprintf(top_right_badge, "%0*u/%02u", width, (unsigned)gSubMenuSelection, (unsigned)approved_index + 1);
            } else {
                sprintf(top_right_badge, "%0*u/--", width, (unsigned)gSubMenuSelection);
            }
        }
    }

#ifdef ENABLE_DTMF_CALLING
    if (m == MENU_D_LIST) {
        sprintf(top_right_badge, "%03d", gSubMenuSelection);
    }
#endif

    if (top_right_badge[0] != '\0') {
        UI_MENU_DrawTopRightRoundedBadge(top_right_badge, 1, true, menu_item_x1, menu_item_x2);
    }

    const char *rxHelp = UI_MENU_GetRxHelp(m);
    if (rxHelp != NULL)
        UI_MENU_DrawRxHelp(rxHelp);

    if ((m == MENU_RESET    ||
         m == MENU_MEM_CH   ||
         m == MENU_MEM_NAME ||
         m == MENU_DEL_CH) && gAskForConfirmation)
    {   // display confirmation
        const char *pPrintStr = (gAskForConfirmation == 1) ?
            WRX_UI_TEXT_OK_QUESTION : WRX_UI_TEXT_WAIT;
        UI_MENU_PrintString(pPrintStr, menu_item_x1, menu_item_x2, 5, 8);
    }

    ST7565_BlitFullScreen();
}
