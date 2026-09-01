/*
 * WRX-JP menu text catalog
 *
 * Edit the display labels and the receive-only help strings in this file.
 * Menu order, IDs, and behavior remain in menu.c.  Each label must fit the
 * six-character menu field (the surrounding array reserves seven bytes for
 * the terminating NUL).  Japanese labels remain in the firmware's internal
 * one-byte code set; the menu renderer may map known labels to the uploaded
 * Unicode font and falls back to these codes when that is not possible.
 */

#ifndef APP_UI_MENU_TEXT_H
#define APP_UI_MENU_TEXT_H

#include "jp_vocab.h"

#ifdef ENABLE_JAPANESE
#define WRX_MENU_LABEL_STEP             {0xBD, 0xC3, 0xAF, 0xCC, 0xDF}
#define WRX_MENU_LABEL_RX_DCS           {0x80, 0x81, 'D', 'C', 'S'}
#define WRX_MENU_LABEL_RX_CTCS          {0x80, 0x81, 'C', 'T', 'C', 'S'}
#define WRX_MENU_LABEL_W_N             {0xEE, 0xFF}
#define WRX_MENU_LABEL_RX_EXT           {0x80, 0x81, 0xE1, 0xE2}
#define WRX_MENU_LABEL_RX_BANK          {0x80, 0x81, 'B'}
#define WRX_MENU_LABEL_RX_BANK_SET      {0xF5, 0xF6}
#define WRX_MENU_LABEL_MODULATION       {0x82, 0x83}
#define WRX_MENU_LABEL_CHANNEL_LIST     {'C', 'H', 0xD8, 0xBD, 0xC4}
#define WRX_MENU_LABEL_SAVE_CHANNEL     {'C', 'H', 0x86, 0x87}
#define WRX_MENU_LABEL_DELETE_CHANNEL   {'C', 'H', 0x88, 0x89}
#define WRX_MENU_LABEL_CHANNEL_NAME     {'C', 'H', 0x8A}
#define WRX_MENU_LABEL_SCAN_LIST         WRX_JP_SCAN_LIST
#define WRX_MENU_LABEL_PRIORITY         {0xE3, 0xE4}
#define WRX_MENU_LABEL_PRIORITY1        {0xE3, 0xE4, '1'}
#define WRX_MENU_LABEL_PRIORITY2        {0xE3, 0xE4, '2'}
#define WRX_MENU_LABEL_F1_SHORT         {'F', '1', 0x8C, 0x8D}
#define WRX_MENU_LABEL_F1_LONG          {'F', '1', 0x8B, 0x8D}
#define WRX_MENU_LABEL_F2_SHORT         {'F', '2', 0x8C, 0x8D}
#define WRX_MENU_LABEL_F2_LONG          {'F', '2', 0x8B, 0x8D}
#define WRX_MENU_LABEL_M_LONG           {'M', 0x8B, 0x8D}
#define WRX_MENU_LABEL_KEY_LOCK         {0xB7, 0xE0, 0xDB, 0xAF, 0xB8}
#define WRX_MENU_LABEL_BATTERY_SAVE     {0x8F, 0xF7}
#define WRX_MENU_LABEL_BATTERY_TEXT     {0x8F, 0x92, '%', 0x93, 0x94}
#define WRX_MENU_LABEL_CHANNEL_DISPLAY  {'C', 'H', 0x93, 0x94}
#define WRX_MENU_LABEL_POWER_ON         {'O', 'N', 0x95, 0x96}
#define WRX_MENU_LABEL_BACKLIGHT        {0x95, 0x96, 0x93, 0x94}
#define WRX_MENU_LABEL_BACKLIGHT_MIN    {0x95, 0x96, 'M', 'i', 'n'}
#define WRX_MENU_LABEL_BACKLIGHT_MAX    {0x95, 0x96, 'M', 'a', 'x'}
#define WRX_MENU_LABEL_BEEP             {0xB7, 0xE0, 0x8E}
#define WRX_MENU_LABEL_INFO             {0xE5, 0xE6}
#define WRX_MENU_LABEL_BATTERY_VOLTAGE  "BatVol"
#define WRX_MENU_LABEL_RX_MODE          {0x80, 0x81, 0xD3, 0xE0, 0xC4, 0xDE}
#define WRX_MENU_LABEL_SQUELCH          {0xBD, 0xB9, 0xD9, 0xC1}
#define WRX_MENU_LABEL_SET_INV          {0xE7, 0xE8}
#define WRX_MENU_LABEL_SET_MENU_LOCK    {0xB7, 0xE0, 0xDB, 0xAF, 0xB8}
#define WRX_MENU_LABEL_SET_METER        {0x93, 0x94}
#define WRX_MENU_LABEL_SET_GUI          {0x95, 0x96}
#define WRX_MENU_LABEL_SET_AUDIO        {0xE9, 0xEA}
#define WRX_MENU_LABEL_SET_SLEEP        {0xEB, 0xEC}
#define WRX_MENU_LABEL_SET_NFM          {0xED, 0xEE}
#define WRX_MENU_LABEL_SET_VOLUME       {0xE9, 0xEF}
#define WRX_MENU_LABEL_SET_SCAN         WRX_JP_HIGH_SPEED
#define WRX_MENU_LABEL_SET_SAVE         {0x86, 0x87}
#define WRX_MENU_LABEL_BATTERY_CAL      {0x8F, 0xF7, 0xFB, 0xFC}
#define WRX_MENU_LABEL_BATTERY_TYPE     {0x8F, 0xF7}
#define WRX_MENU_LABEL_RESET            {0xF8, 0xF9, 0xFA}
#define WRX_MENU_LABEL_COMPANDER        {'C', 'M', 'P'}
#define WRX_MENU_LABEL_SCAN_REVERSE     {'S', 0xE7, 0xE8}
#define WRX_MENU_LABEL_DTMF_LIVE        {'D', 'T', 'M', 'F'}
#define WRX_MENU_LABEL_SET_CONTRAST     {0x93, 0x94}
#else
#define WRX_MENU_LABEL_STEP             "Step"
#define WRX_MENU_LABEL_RX_DCS           "RxDCS"
#define WRX_MENU_LABEL_RX_CTCS          "RxCTCS"
#define WRX_MENU_LABEL_W_N             "W/N"
#define WRX_MENU_LABEL_RX_EXT           "RXExt"
#define WRX_MENU_LABEL_RX_BANK_SET      "BnkSet"
#define WRX_MENU_LABEL_MODULATION       "Mode"
#define WRX_MENU_LABEL_CHANNEL_LIST     "ChList"
#define WRX_MENU_LABEL_SAVE_CHANNEL     "ChSave"
#define WRX_MENU_LABEL_DELETE_CHANNEL   "ChDele"
#define WRX_MENU_LABEL_CHANNEL_NAME     "ChName"
#define WRX_MENU_LABEL_SCAN_LIST         "ScList"
#define WRX_MENU_LABEL_PRIORITY         "ScPri"
#define WRX_MENU_LABEL_PRIORITY1        "PriCh1"
#define WRX_MENU_LABEL_PRIORITY2        "PriCh2"
#define WRX_MENU_LABEL_F1_SHORT         "F1Shrt"
#define WRX_MENU_LABEL_F1_LONG          "F1Long"
#define WRX_MENU_LABEL_F2_SHORT         "F2Shrt"
#define WRX_MENU_LABEL_F2_LONG          "F2Long"
#define WRX_MENU_LABEL_M_LONG           "M Long"
#define WRX_MENU_LABEL_KEY_LOCK         "KeyLck"
#define WRX_MENU_LABEL_BATTERY_SAVE     "BatSav"
#define WRX_MENU_LABEL_BATTERY_TEXT     "BatTxt"
#define WRX_MENU_LABEL_CHANNEL_DISPLAY  "ChDisp"
#define WRX_MENU_LABEL_POWER_ON         "POnMsg"
#define WRX_MENU_LABEL_BACKLIGHT        "BLTime"
#define WRX_MENU_LABEL_BACKLIGHT_MIN    "BLMin"
#define WRX_MENU_LABEL_BACKLIGHT_MAX    "BLMax"
#define WRX_MENU_LABEL_BEEP             "Beep"
#define WRX_MENU_LABEL_INFO             "SysInf"
#define WRX_MENU_LABEL_BATTERY_VOLTAGE  "BatVol"
#define WRX_MENU_LABEL_RX_MODE          "RxMode"
#define WRX_MENU_LABEL_SQUELCH          "Sql"
#define WRX_MENU_LABEL_SET_INV          "SetInv"
#define WRX_MENU_LABEL_SET_MENU_LOCK    "SetLck"
#define WRX_MENU_LABEL_SET_METER        "SetMet"
#define WRX_MENU_LABEL_SET_GUI          "SetGUI"
#define WRX_MENU_LABEL_SET_AUDIO        "SetRxA"
#define WRX_MENU_LABEL_SET_SLEEP        "SetOff"
#define WRX_MENU_LABEL_SET_NFM          "SetNFM"
#define WRX_MENU_LABEL_SET_VOLUME       "SetVol"
#define WRX_MENU_LABEL_SET_SCAN         "SetScn"
#define WRX_MENU_LABEL_SET_SAVE         "SetSav"
#define WRX_MENU_LABEL_BATTERY_CAL      "BatCal"
#define WRX_MENU_LABEL_RESET            "Reset"
#endif

#define WRX_MENU_LABEL_POWER            "Power"
#define WRX_MENU_LABEL_TX_DCS           "TxDCS"
#define WRX_MENU_LABEL_TX_CTCS         "TxCTCS"
#define WRX_MENU_LABEL_TX_OFFSET_DIR   "TxODir"
#define WRX_MENU_LABEL_TX_OFFSET       "TxOffs"
#ifndef WRX_MENU_LABEL_RX_BANK
#define WRX_MENU_LABEL_RX_BANK         "Bank"
#endif
#define WRX_MENU_LABEL_SCRAMBLER       "Scramb"
#define WRX_MENU_LABEL_BUSY_CANCEL     "BusyCL"
#ifndef WRX_MENU_LABEL_COMPANDER
#define WRX_MENU_LABEL_COMPANDER       "Compnd"
#endif
#ifndef WRX_MENU_LABEL_SCAN_REVERSE
#define WRX_MENU_LABEL_SCAN_REVERSE    "ScnRev"
#endif
#define WRX_MENU_LABEL_NOAA_SCAN       "NOAA-S"
#define WRX_MENU_LABEL_TX_TIMEOUT      "TxTOut"
#define WRX_MENU_LABEL_MIC             "Mic"
#define WRX_MENU_LABEL_MIC_BAR         "MicBar"
#define WRX_MENU_LABEL_BACKLIGHT_TXRX  "BLTxRx"
#define WRX_MENU_LABEL_VOICE           "Voice"
#define WRX_MENU_LABEL_ROGER           "Roger"
#define WRX_MENU_LABEL_STE             "STE"
#define WRX_MENU_LABEL_RP_STE          "RP STE"
#define WRX_MENU_LABEL_CALL1           "1 Call"
#define WRX_MENU_LABEL_ALARM           "AlarmT"
#define WRX_MENU_LABEL_ANI             "ANI ID"
#define WRX_MENU_LABEL_UP_CODE         "UPCode"
#define WRX_MENU_LABEL_DOWN_CODE       "DWCode"
#define WRX_MENU_LABEL_PTT_ID          "PTT ID"
#define WRX_MENU_LABEL_DTMF_ST         "D ST"
#define WRX_MENU_LABEL_DTMF_RESPONSE   "D Resp"
#define WRX_MENU_LABEL_DTMF_HOLD       "D Hold"
#define WRX_MENU_LABEL_DTMF_PRE        "D Prel"
#define WRX_MENU_LABEL_DTMF_DECODE     "D Decd"
#define WRX_MENU_LABEL_DTMF_LIST       "D List"
#ifndef WRX_MENU_LABEL_DTMF_LIVE
#define WRX_MENU_LABEL_DTMF_LIVE       "D Live"
#endif
#define WRX_MENU_LABEL_AM_FIX          "AM Fix"
#define WRX_MENU_LABEL_VOX             "VOX"
#ifndef WRX_MENU_LABEL_SET_CONTRAST
#define WRX_MENU_LABEL_SET_CONTRAST    "SetCtr"
#endif
#define WRX_MENU_LABEL_SET_POWER       "SetPwr"
#define WRX_MENU_LABEL_SET_PTT         "SetPTT"
#define WRX_MENU_LABEL_SET_TOT         "SetTOT"
#define WRX_MENU_LABEL_SET_EOT         "SetEOT"
#define WRX_MENU_LABEL_SET_TIMER       "SetTmr"
#define WRX_MENU_LABEL_SET_KEY         "SetKey"
#define WRX_MENU_LABEL_SET_NWR         "SetNWR"
#define WRX_MENU_LABEL_F_LOCK          "F Lock"
#define WRX_MENU_LABEL_TX_200          "Tx 200"
#define WRX_MENU_LABEL_TX_350          "Tx 350"
#define WRX_MENU_LABEL_TX_500          "Tx 500"
#define WRX_MENU_LABEL_350_ENABLE      "350 En"
#define WRX_MENU_LABEL_SCRAMBLER_EN    "ScraEn"
#define WRX_MENU_LABEL_FREQ_CAL        "FrCali"
#ifndef WRX_MENU_LABEL_BATTERY_TYPE
#define WRX_MENU_LABEL_BATTERY_TYPE    "BatTyp"
#endif
#define WRX_MENU_LABEL_SET_NAV         "SetNav"

#ifdef ENABLE_JAPANESE
#define WRX_MENU_HELP_SQL              "\xEB\xEC"
#define WRX_MENU_HELP_W_N              "W+25 W20 N12 N-6"
#define WRX_MENU_HELP_CHANNEL_LIST     "CH \xD8\xBD\xC4"
#define WRX_MENU_HELP_CTCS             "CT NORMAL/REV"
#define WRX_MENU_HELP_RX_EXT           "\x80\x81\xE1\xE2"
#define WRX_MENU_HELP_RX_BANK          "\x80\x81" "B"
#define WRX_MENU_HELP_RX_BANK_SET      "B\xF5\xF6"
#else
#define WRX_MENU_HELP_SQL              "AUTO=measure noise"
#define WRX_MENU_HELP_W_N              "W+25 W20 N12 N-6"
#define WRX_MENU_HELP_CHANNEL_LIST     "scan list membership"
#define WRX_MENU_HELP_CTCS             "normal/reverse tone"
#define WRX_MENU_HELP_RX_EXT           "RX features master"
#define WRX_MENU_HELP_RX_BANK          "scan bank filter"
#define WRX_MENU_HELP_RX_BANK_SET      "set channel bank"
#endif

#ifdef ENABLE_JAPANESE
#define WRX_ACTION_NONE                 "\x97"
#define WRX_ACTION_FLASHLIGHT           "\xD7\xB2\xC4"
#define WRX_ACTION_MONITOR              "\xD3\xC6\xC0\xE0"
#define WRX_ACTION_SCAN                 WRX_JP_SCAN
#define WRX_ACTION_FM                   "FM"
#define WRX_ACTION_LOCK_KEYPAD          "\xB7\xE0\xDB\xAF\xB8"
#define WRX_ACTION_VFO_A_B              "VFO A\nVFO B"
#define WRX_ACTION_VFO_MEM              "VFO\nMEM"
#define WRX_ACTION_MODE                 "\xD3\xE0\xC4\xDE"
#define WRX_ACTION_RX_MODE              "\x80\x81"
#define WRX_ACTION_MAIN_ONLY            "\x80\x81\x98\x99"
#define WRX_ACTION_WIDE_NARROW          "W/N"
#define WRX_ACTION_MUTE                 "MUTE"
#else
#define WRX_ACTION_NONE                 "NONE"
#define WRX_ACTION_FLASHLIGHT           "FLASH\nLIGHT"
#define WRX_ACTION_MONITOR              "MONITOR"
#define WRX_ACTION_SCAN                 "SCAN"
#define WRX_ACTION_FM                   "FM RADIO"
#define WRX_ACTION_LOCK_KEYPAD          "LOCK\nKEYPAD"
#define WRX_ACTION_VFO_A_B              "VFO A\nVFO B"
#define WRX_ACTION_VFO_MEM              "VFO\nMEM"
#define WRX_ACTION_MODE                 "MODE"
#define WRX_ACTION_RX_MODE              "RX MODE"
#define WRX_ACTION_MAIN_ONLY            "MAIN ONLY"
#define WRX_ACTION_WIDE_NARROW          "WIDE\nNARROW"
#define WRX_ACTION_MUTE                 "MUTE"
#endif

/* The category header uses the large font. Keep these labels short so the
 * category picker remains legible on the 128-pixel LCD. */
#ifdef ENABLE_JAPANESE
#define WRX_MENU_CATEGORY_CHANNELS     "\xC1\xAC\xDD\xC8\xD9"
#define WRX_MENU_CATEGORY_SCAN         WRX_JP_SCAN
#define WRX_MENU_CATEGORY_KEYS         "\xB7\xE0"
#define WRX_MENU_CATEGORY_POWER        "\x8F\x90"
#define WRX_MENU_CATEGORY_DISPLAY      "\x93\x94"
#define WRX_MENU_CATEGORY_TIMERS       "\xC3\xB2\xCF\xE0"
#define WRX_MENU_CATEGORY_AUDIO        "\x8E\xEA"
#define WRX_MENU_CATEGORY_RADIO        "\x80\x81"
#define WRX_MENU_CATEGORY_DTMF         "DTMF"
#define WRX_MENU_CATEGORY_SERVICE      "\xF5\xF6"
#define WRX_MENU_CATEGORY_ALL          "ALL"
#else
#define WRX_MENU_CATEGORY_CHANNELS     "Channels"
#define WRX_MENU_CATEGORY_SCAN         "Scan"
#define WRX_MENU_CATEGORY_KEYS         "Keys"
#define WRX_MENU_CATEGORY_POWER        "Power"
#define WRX_MENU_CATEGORY_DISPLAY      "Display"
#define WRX_MENU_CATEGORY_TIMERS       "Timers"
#define WRX_MENU_CATEGORY_AUDIO        "Audio"
#define WRX_MENU_CATEGORY_RADIO        "Radio"
#define WRX_MENU_CATEGORY_DTMF         "DTMF"
#define WRX_MENU_CATEGORY_SERVICE      "Service"
#define WRX_MENU_CATEGORY_ALL          "All"
#endif

#endif
