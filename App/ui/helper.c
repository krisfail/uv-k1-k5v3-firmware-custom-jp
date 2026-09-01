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

#include "driver/st7565.h"
#include "external/printf/printf.h"
#include "font.h"
#ifdef ENABLE_JAPANESE
#include "japanese_font.h"
#endif
#include "ui/helper.h"
#include "ui/inputbox.h"
#include "ui/jp_text.h"
#include "misc.h"
#include "settings.h"

static uint8_t UI_CenteredStart(const uint8_t start, const uint8_t end,
                                const size_t length, const unsigned int advance)
{
    if (end <= start || length == 0u)
        return start;

    const uint16_t available = (uint16_t)(end - start);
    const uint32_t used = (uint32_t)length * advance;
    if (used >= available)
        return start;

    return (uint8_t)(start + (uint8_t)((available - used + 1u) / 2u));
}

static void UI_CopyLargeGlyphClipped(const uint8_t line, const unsigned int x,
                                     const uint8_t *glyph, const size_t width,
                                     const uint8_t end)
{
    const size_t line_count = sizeof(gFrameBuffer) / sizeof(gFrameBuffer[0]);
    if ((size_t)line + 1u >= line_count || x >= LCD_WIDTH || x > end)
        return;

    size_t copy_width = LCD_WIDTH - x;
    if (copy_width > width)
        copy_width = width;
    if (copy_width > (size_t)end + 1u - x)
        copy_width = (size_t)end + 1u - x;

    if (copy_width == 0u)
        return;

    memcpy(gFrameBuffer[line] + x, glyph, copy_width);
    memcpy(gFrameBuffer[line + 1u] + x, glyph + width, copy_width);
}

static void UI_CopyLargeGlyph(const uint8_t line, const unsigned int x,
                              const uint8_t *glyph, const size_t width)
{
    UI_CopyLargeGlyphClipped(line, x, glyph, width, LCD_WIDTH - 1u);
}

void UI_GenerateChannelString(char *pString, const uint16_t Channel)
{
    unsigned int i;

    if (gInputBoxIndex == 0)
    {
        sprintf(pString, "CH-%02u", Channel + 1);
        return;
    }

    pString[0] = 'C';
    pString[1] = 'H';
    pString[2] = '-';
    for (i = 0; i < 2; i++)
        pString[i + 3] = (gInputBox[i] == 10) ? '-' : gInputBox[i] + '0';

    pString[5] = 0;
}

void UI_GenerateChannelStringEx(char *pString, const bool bShowPrefix, const uint16_t ChannelNumber)
{
    if (gInputBoxIndex > 0) {
        for (unsigned int i = 0; i < 4; i++) {
            pString[i] = (gInputBox[i] == 10) ? '-' : gInputBox[i] + '0';
        }

        pString[4] = 0;
        return;
    }

    if (bShowPrefix) {
        // BUG here? Prefixed NULLs are allowed
        sprintf(pString, "CH-%04u", ChannelNumber + 1);
    } else if (ChannelNumber == MR_CHANNEL_LAST + 1) {
        strcpy(pString, WRX_UI_TEXT_NONE);
    } else if (ChannelNumber == 0xFFFF) {
        strcpy(pString, "NULL");
    } else {
        sprintf(pString, "%04u", ChannelNumber + 1);
    }
}

static void UI_PrintStringBufferClipped(const char *pString, uint8_t *buffer,
                                        const uint32_t char_width,
                                        const uint8_t *font,
                                        const size_t capacity)
{
    const size_t Length = strlen(pString);
    const unsigned int char_spacing = char_width + 1;
    for (size_t i = 0; i < Length; i++) {
        const uint8_t code = (uint8_t)pString[i];
#ifdef ENABLE_JAPANESE
        const bool is_small_font =
            font == (const uint8_t *)gFontSmall
#ifdef ENABLE_SMALL_BOLD
            || font == (const uint8_t *)gFontSmallBold
#endif
            ;
        const bool is_extended_small = is_small_font && code >= 0x7F && code <= FONT_CODE_MAX;
#else
        const bool is_extended_small = false;
#endif
        if (code > ' ' && (code < 127 || is_extended_small)) {
            const size_t offset = i * char_spacing + 1u;
            if (offset >= capacity)
                continue;

            size_t copy_width = char_width;
            if (copy_width > capacity - offset)
                copy_width = capacity - offset;
#ifdef ENABLE_JAPANESE
            if (is_extended_small)
                memcpy(buffer + offset, gFontSmallJapanese[code - 0x7F], copy_width);
            else
#endif
                memcpy(buffer + offset, font + (code - ' ' - 1) * char_width, copy_width);
        }
    }
}

void UI_PrintStringBuffer(const char *pString, uint8_t *buffer, uint32_t char_width, const uint8_t *font)
{
    /* The legacy API has no capacity parameter; keep its behavior for callers
     * that provide a complete scratch buffer. LCD drawing uses the clipped
     * variant below, where the capacity is known. */
    UI_PrintStringBufferClipped(pString, buffer, char_width, font, (size_t)-1);
}

void UI_PrintString(const char *pString, uint8_t Start, uint8_t End, uint8_t Line, uint8_t Width)
{
    size_t i;
    size_t Length = strlen(pString);

    Start = UI_CenteredStart(Start, End, Length, Width);

    for (i = 0; i < Length; i++)
    {
        const unsigned int ofs   = (unsigned int)Start + (i * Width);
        const uint8_t code = (uint8_t)pString[i];
        if (code > ' ' && code < 127)
        {
            const unsigned int index = code - ' ' - 1;
            UI_CopyLargeGlyph(Line, ofs, gFontBig[index], 7u);
#ifdef ENABLE_JAPANESE
        }
        else if (code >= 0x7F && code <= FONT_CODE_MAX)
        {
            const uint8_t *glyph = gFontBigJapanese[code - 0x7F];
            /* Japanese uses the same fixed two-page storage format.  The
             * glyph data itself decides which rows are lit. */
            UI_CopyLargeGlyph(Line, ofs, glyph, 7u);
#endif
        }
    }
}

void UI_PrintStringClipped(const char *pString, uint8_t Start, uint8_t End, uint8_t Line, uint8_t Width)
{
    const size_t Length = strlen(pString);

    if (Start >= LCD_WIDTH || End < Start)
        return;

    for (size_t i = 0; i < Length; i++)
    {
        const unsigned int ofs = (unsigned int)Start + (i * Width);
        const uint8_t code = (uint8_t)pString[i];
        if (code > ' ' && code < 127)
        {
            const unsigned int index = code - ' ' - 1;
            UI_CopyLargeGlyphClipped(Line, ofs, gFontBig[index], 7u, End);
#ifdef ENABLE_JAPANESE
        }
        else if (code >= 0x7F && code <= FONT_CODE_MAX)
        {
            UI_CopyLargeGlyphClipped(Line, ofs, gFontBigJapanese[code - 0x7F], 7u, End);
#endif
        }
    }
}

#ifdef ENABLE_JAPANESE
static void UI_CopyExternalGlyph(uint8_t line, uint8_t x, uint8_t end,
                                 const uint8_t *glyph);

static const uint16_t gJapaneseHalfwidthToFullwidth[0x3F] = {
    0x3002, 0x300C, 0x300D, 0x3001, 0x30FB, 0x30F2, 0x30A1, 0x30A3,
    0x30A5, 0x30A7, 0x30A9, 0x30E3, 0x30E5, 0x30E7, 0x30C3, 0x30FC,
    0x30A2, 0x30A4, 0x30A6, 0x30A8, 0x30AA, 0x30AB, 0x30AD, 0x30AF,
    0x30B1, 0x30B3, 0x30B5, 0x30B7, 0x30B9, 0x30BB, 0x30BD, 0x30BF,
    0x30C1, 0x30C4, 0x30C6, 0x30C8, 0x30CA, 0x30CB, 0x30CC, 0x30CD,
    0x30CE, 0x30CF, 0x30D2, 0x30D5, 0x30D8, 0x30DB, 0x30DE, 0x30DF,
    0x30E0, 0x30E1, 0x30E2, 0x30E4, 0x30E6, 0x30E8, 0x30E9, 0x30EA,
    0x30EB, 0x30EC, 0x30ED, 0x30EF, 0x30F3, 0x3099, 0x309A,
};

static uint16_t UI_InternalJapaneseCodepoint(const uint8_t code)
{
    switch (code)
    {
        case 0x80: return 0x53D7; // 受
        case 0x81: return 0x4FE1; // 信
        case 0x82: return 0x5909; // 変
        case 0x83: return 0x8ABF; // 調
        case 0x86: return 0x4FDD; // 保
        case 0x87: return 0x5B58; // 存
        case 0x88: return 0x524A; // 削
        case 0x89: return 0x9664; // 除
        case 0x8A: return 0x540D; // 名
        case 0x8B: return 0x9577; // 長
        case 0x8C: return 0x77ED; // 短
        case 0x8D: return 0x62BC; // 押
        case 0x8E: return 0x97F3; // 音
        case 0x8F: return 0x96FB; // 電
        case 0x90: return 0x6E90; // 源
        case 0x92: return 0x5727; // 圧
        case 0x93: return 0x8868; // 表
        case 0x94: return 0x793A; // 示
        case 0x95: return 0x753B; // 画
        case 0x96: return 0x9762; // 面
        case 0x97: return 0x7121; // 無
        case 0x98: return 0x5C02; // 専
        case 0x99: return 0x7528; // 用
        case 0xE0: return 0x30FC; // ー
        case 0xE1: return 0x62E1; // 拡
        case 0xE2: return 0x5F35; // 張
        case 0xE3: return 0x512A; // 優
        case 0xE4: return 0x5148; // 先
        case 0xE5: return 0x60C5; // 情
        case 0xE6: return 0x5831; // 報
        case 0xE7: return 0x53CD; // 反
        case 0xE8: return 0x8EE2; // 転
        case 0xE9: return 0x97F3; // 音
        case 0xEA: return 0x58F0; // 声
        case 0xEB: return 0x81EA; // 自
        case 0xEC: return 0x52D5; // 動
        case 0xED: return 0x72ED; // 狭
        case 0xEE: return 0x5E2F; // 帯
        case 0xEF: return 0x91CF; // 量
        case 0xF0: return 0x9AD8; // 高
        case 0xF1: return 0x901F; // 速
        case 0xF2: return 0x5468; // 周
        case 0xF3: return 0x6CE2; // 波
        case 0xF4: return 0x6570; // 数
        case 0xF5: return 0x8A2D; // 設
        case 0xF6: return 0x5B9A; // 定
        case 0xF7: return 0x6C60; // 池
        case 0xF8: return 0x521D; // 初
        case 0xF9: return 0x671F; // 期
        case 0xFA: return 0x5316; // 化
        case 0xFB: return 0x6821; // 校
        case 0xFC: return 0x6B63; // 正
        case 0xFF: return 0x57DF; // 域
        default:
            if (code >= 0xA1u && code <= 0xDFu)
                return gJapaneseHalfwidthToFullwidth[code - 0xA1u];
            return 0;
    }
}

static uint16_t UI_ComposeJapaneseKana(const uint16_t base, const bool handakuten)
{
    static const uint16_t voiced[][2] = {
        {0x30AB, 0x30AC}, {0x30AD, 0x30AE}, {0x30AF, 0x30B0},
        {0x30B1, 0x30B2}, {0x30B3, 0x30B4}, {0x30B5, 0x30B6},
        {0x30B7, 0x30B8}, {0x30B9, 0x30BA}, {0x30BB, 0x30BC},
        {0x30BD, 0x30BE}, {0x30BF, 0x30C0}, {0x30C1, 0x30C2},
        {0x30C4, 0x30C5}, {0x30C6, 0x30C7}, {0x30C8, 0x30C9},
        {0x30CF, 0x30D0}, {0x30D2, 0x30D3}, {0x30D5, 0x30D6},
        {0x30D8, 0x30D9}, {0x30DB, 0x30DC},
    };
    static const uint16_t semi[][2] = {
        {0x30CF, 0x30D1}, {0x30D2, 0x30D4}, {0x30D5, 0x30D7},
        {0x30D8, 0x30DA}, {0x30DB, 0x30DD},
    };
    const uint16_t (*table)[2] = handakuten ? semi : voiced;
    const size_t count = handakuten ? ARRAY_SIZE(semi) : ARRAY_SIZE(voiced);
    for (size_t i = 0; i < count; i++)
        if (table[i][0] == base)
            return table[i][1];
    return 0;
}

static bool UI_DrawExternalJapaneseCodepoints(const uint16_t *codepoints,
                                              const size_t count,
                                              const uint16_t pixel_width,
                                              const uint8_t start,
                                              const uint8_t end,
                                              const uint8_t line,
                                              const bool center_full_width);

bool UI_PrintStringJapaneseExternal(const char *pString, uint8_t Start, uint8_t End, uint8_t Line)
{
    uint16_t codepoints[16];
    size_t count = 0;
    uint16_t pixel_width = 0;

    if (pString == NULL)
        return false;

    for (size_t index = 0; pString[index] != 0; index++)
    {
        const uint8_t code = (uint8_t)pString[index];
        if (code == '\n' || count >= ARRAY_SIZE(codepoints))
            return false;
        if (code == 0xDEu || code == 0xDFu)
        {
            if (count == 0u)
                return false;
            const uint16_t composed = UI_ComposeJapaneseKana(
                codepoints[count - 1u], code == 0xDFu);
            if (composed == 0u)
                return false;
            codepoints[count - 1u] = composed;
            continue;
        }

        const uint16_t codepoint = code >= 0x20u && code <= 0x7Eu
            ? code : UI_InternalJapaneseCodepoint(code);
        if (codepoint == 0u)
            return false;
        codepoints[count++] = codepoint;
        pixel_width = (uint16_t)(pixel_width +
                     (codepoint < 0x80u ? 8u : 16u));
    }

    return UI_DrawExternalJapaneseCodepoints(codepoints, count, pixel_width,
                                              Start, End, Line, false);
}

void UI_PrintStringJapaneseExtraLarge(const char *pString, uint8_t Start, uint8_t End, uint8_t Line, uint8_t Width)
{
    const size_t Length = strlen(pString);

    Start = UI_CenteredStart(Start, End, Length, Width);

    for (size_t i = 0; i < Length; i++)
    {
        const uint8_t code = (uint8_t)pString[i];
        const unsigned int ofs = (unsigned int)Start + (i * Width);
        for (size_t glyph = 0; glyph < FONT_JP_EXTRA_LARGE_GLYPHS; glyph++)
        {
            if (gFontJapaneseExtraLargeCodes[glyph] == code)
            {
                UI_CopyLargeGlyph(Line, ofs, gFontJapaneseExtraLarge[glyph],
                                  FONT_JP_EXTRA_LARGE_WIDTH);
                break;
            }
        }
    }
}

static bool UI_DecodeExternalUtf8(const uint8_t *input, size_t remaining,
                                  size_t *used, uint16_t *codepoint)
{
    const uint8_t first = input[0];

    if (first < 0x80u)
    {
        if (first < 0x20u || first > 0x7Eu)
            return false;
        *used = 1u;
        *codepoint = first;
        return true;
    }

    if (first >= 0xC2u && first <= 0xDFu)
    {
        if (remaining < 2u || (input[1] & 0xC0u) != 0x80u)
            return false;
        *used = 2u;
        *codepoint = (uint16_t)(((first & 0x1Fu) << 6) |
                                (input[1] & 0x3Fu));
        return true;
    }

    if (first >= 0xE0u && first <= 0xEFu)
    {
        if (remaining < 3u || (input[1] & 0xC0u) != 0x80u ||
            (input[2] & 0xC0u) != 0x80u)
            return false;

        const uint16_t value = (uint16_t)(((first & 0x0Fu) << 12) |
                                          ((input[1] & 0x3Fu) << 6) |
                                          (input[2] & 0x3Fu));
        if (value < 0x0800u || (value >= 0xD800u && value <= 0xDFFFu))
            return false;
        *used = 3u;
        *codepoint = value;
        return true;
    }

    // Channel names support BMP UTF-8 only; reject four-byte sequences.
    return false;
}

static void UI_CopyExternalGlyph(uint8_t line, uint8_t x, uint8_t end,
                                 const uint8_t *glyph)
{
    if (line + 1u >= (sizeof(gFrameBuffer) / sizeof(gFrameBuffer[0])) ||
        x >= LCD_WIDTH || x > end)
        return;

    uint8_t width = LCD_WIDTH - x;
    if (width > 16u)
        width = 16u;
    if (width > (uint8_t)(end + 1u - x))
        width = (uint8_t)(end + 1u - x);

    for (uint8_t page = 0; page < 2u; page++)
    {
        for (uint8_t column = 0; column < width; column++)
        {
            uint8_t value = 0;
            for (uint8_t row = 0; row < 8u; row++)
            {
                const uint8_t absolute_row = (uint8_t)(page * 8u + row);
                const uint16_t bitmap_row = (uint16_t)glyph[absolute_row * 2u] |
                                             ((uint16_t)glyph[absolute_row * 2u + 1u] << 8);
                if (bitmap_row & (uint16_t)(0x8000u >> column))
                    value |= (uint8_t)(1u << row);
            }
            gFrameBuffer[line + page][x + column] = value;
        }
    }
}

static bool UI_DrawExternalJapaneseCodepoints(const uint16_t *codepoints,
                                              const size_t count,
                                              const uint16_t pixel_width,
                                              const uint8_t start,
                                              const uint8_t end,
                                              const uint8_t line,
                                              const bool center_full_width)
{
    const uint8_t right = end == 0u ? LCD_WIDTH - 1u : end;
    if (codepoints == NULL || line + 1u >= (sizeof(gFrameBuffer) / sizeof(gFrameBuffer[0])) ||
        start >= LCD_WIDTH || start > right ||
        pixel_width > (uint16_t)(right + 1u - start))
        return false;

    /* Validate all external glyphs before changing the framebuffer. */
    for (size_t index = 0; index < count; index++)
    {
        if (codepoints[index] >= 0x80u &&
            !JPFONT_HasGlyph(codepoints[index]))
            return false;
    }

    uint8_t x = start;
    if (center_full_width || end != 0u)
        x = (uint8_t)(start + ((right + 1u - start - pixel_width) / 2u));

    for (size_t index = 0; index < count; index++)
    {
        const uint16_t codepoint = codepoints[index];
        if (codepoint < 0x80u)
        {
            if (codepoint > ' ')
                UI_CopyLargeGlyphClipped(line, x,
                                         gFontBig[codepoint - ' ' - 1u],
                                         7u, right);
            x = (uint8_t)(x + 8u);
        }
        else
        {
            uint8_t glyph[JAPANESE_FONT_GLYPH_BYTES];
            if (!JPFONT_ReadGlyph(codepoint, glyph))
                return false;
            UI_CopyExternalGlyph(line, x, right, glyph);
            x = (uint8_t)(x + 16u);
        }
    }

    return true;
}

bool UI_PrintJapaneseChannelName(uint16_t channel, uint8_t Start, uint8_t End, uint8_t Line)
{
    char name[JAPANESE_NAME_RECORD_SIZE];
    const uint8_t length = JPFONT_ReadChannelName(channel, name, sizeof(name));
    uint16_t codepoints[JAPANESE_NAME_PAYLOAD_MAX];
    size_t codepoint_count = 0;
    size_t offset = 0;
    uint16_t pixel_width = 0;

    if (length == 0u || Line + 1u >= (sizeof(gFrameBuffer) / sizeof(gFrameBuffer[0])))
        return false;

    while (offset < length)
    {
        size_t used;
        uint16_t codepoint;
        if (codepoint_count >= ARRAY_SIZE(codepoints) ||
            !UI_DecodeExternalUtf8((const uint8_t *)name + offset,
                                   length - offset, &used, &codepoint))
            return false;
        codepoints[codepoint_count++] = codepoint;
        offset += used;
        pixel_width = (uint16_t)(pixel_width +
                     (codepoint < 0x80u ? 8u : 16u));
    }

    return UI_DrawExternalJapaneseCodepoints(codepoints, codepoint_count,
                                              pixel_width, Start, End, Line,
                                              true);
}
#endif

void UI_PrintStringSmall(const char *pString, uint8_t Start, uint8_t End, uint8_t Line, uint8_t char_width, const uint8_t *font)
{
    const size_t Length = strlen(pString);
    const unsigned int char_spacing = char_width + 1;

    Start = UI_CenteredStart(Start, End, Length, char_spacing);

    if (Start >= LCD_WIDTH || Line >= (sizeof(gFrameBuffer) / sizeof(gFrameBuffer[0])))
        return;

    UI_PrintStringBufferClipped(pString, gFrameBuffer[Line] + Start,
                                char_width, font, LCD_WIDTH - Start);
}


void UI_PrintStringSmallNormal(const char *pString, uint8_t Start, uint8_t End, uint8_t Line)
{
    UI_PrintStringSmall(pString, Start, End, Line, ARRAY_SIZE(gFontSmall[0]), (const uint8_t *)gFontSmall);
}

void UI_PrintStringSmallNormalClipped(const char *pString, uint8_t Start, uint8_t End, uint8_t Line)
{
    const unsigned int line_count = sizeof(gFrameBuffer) / sizeof(gFrameBuffer[0]);
    const unsigned int end = (unsigned int)End + 1u;

    if (Start >= LCD_WIDTH || Line >= line_count || end <= Start)
        return;

    UI_PrintStringBufferClipped(pString, gFrameBuffer[Line] + Start,
                                ARRAY_SIZE(gFontSmall[0]),
                                (const uint8_t *)gFontSmall, end - Start);
}

void UI_PrintStringSmallNormalInverse(const char *pString, uint8_t Start, uint8_t End, uint8_t Line)
{
    // First draw the string normally
    UI_PrintStringSmallNormal(pString, Start, End, Line);

    /* Recompute the centered origin used by UI_PrintStringSmall.  The old
     * implementation inverted from the caller's Start value, so centered
     * labels were drawn in one place and inverted in another. */
    const size_t length = strlen(pString);
    const unsigned int char_width = ARRAY_SIZE(gFontSmall[0]);
    const unsigned int char_spacing = char_width + 1u;
    const size_t line_count = sizeof(gFrameBuffer) / sizeof(gFrameBuffer[0]);
    const uint8_t x_start = UI_CenteredStart(Start, End, length, char_spacing);

    /* Inversion uses the preceding framebuffer page for the top edge.  A
     * status-line call (Line == 0) must remain a normal, non-inverted draw. */
    if (length == 0u || Line == 0u || Line >= line_count || x_start >= LCD_WIDTH)
        return;

    size_t x_end = (size_t)x_start + length * char_spacing;
    const size_t right_edge = (End != 0u && End < LCD_WIDTH) ? End : LCD_WIDTH;
    if (x_end > right_edge)
        x_end = right_edge;

    if (x_start > 0u)
        gFrameBuffer[Line][x_start - 1u] ^= 0x7F;
    for (size_t x = x_start; x < x_end; x++)
    {
        gFrameBuffer[Line][x] ^= 0xFF;
        gFrameBuffer[Line - 1u][x] ^= 0x80;
    }
    if (x_end < LCD_WIDTH)
        gFrameBuffer[Line][x_end] ^= 0x7F;
}


void UI_PrintStringSmallBold(const char *pString, uint8_t Start, uint8_t End, uint8_t Line)
{
#ifdef ENABLE_SMALL_BOLD
    const uint8_t *font = (uint8_t *)gFontSmallBold;
    const uint8_t char_width = ARRAY_SIZE(gFontSmallBold[0]);
#else
    const uint8_t *font = (uint8_t *)gFontSmall;
    const uint8_t char_width = ARRAY_SIZE(gFontSmall[0]);
#endif

    UI_PrintStringSmall(pString, Start, End, Line, char_width, font);
}

void UI_PrintStringSmallBufferNormal(const char *pString, uint8_t * buffer)
{
    UI_PrintStringBuffer(pString, buffer, ARRAY_SIZE(gFontSmall[0]), (uint8_t *)gFontSmall);
}

void UI_PrintStringSmallBufferBold(const char *pString, uint8_t * buffer)
{
#ifdef ENABLE_SMALL_BOLD
    const uint8_t *font = (uint8_t *)gFontSmallBold;
    const uint8_t char_width = ARRAY_SIZE(gFontSmallBold[0]);
#else
    const uint8_t *font = (uint8_t *)gFontSmall;
    const uint8_t char_width = ARRAY_SIZE(gFontSmall[0]);
#endif
    UI_PrintStringBuffer(pString, buffer, char_width, font);
}

void UI_DisplayFrequency(const char *string, uint8_t X, uint8_t Y, bool center)
{
    const unsigned int char_width  = 13;
    uint8_t           *pFb0        = gFrameBuffer[Y] + X;
    uint8_t           *pFb1        = pFb0 + 128;
    bool               bCanDisplay = false;

    uint8_t len = strlen(string);
    for(int i = 0; i < len; i++) {
        char c = string[i];
        if(c=='-') c = '9' + 1;
        if (bCanDisplay || c != ' ')
        {
            bCanDisplay = true;
            if(c>='0' && c<='9' + 1) {
                memcpy(pFb0 + 2, gFontBigDigits[c-'0'],                  char_width - 3);
                memcpy(pFb1 + 2, gFontBigDigits[c-'0'] + char_width - 3, char_width - 3);
            }
            else if(c=='.') {
                *pFb1 = 0x60; pFb0++; pFb1++;
                *pFb1 = 0x60; pFb0++; pFb1++;
                *pFb1 = 0x60; pFb0++; pFb1++;
                continue;
            }

        }
        else if (center) {
            pFb0 -= 6;
            pFb1 -= 6;
        }
        pFb0 += char_width;
        pFb1 += char_width;
    }
}

/*
void UI_DisplayFrequency(const char *string, uint8_t X, uint8_t Y, bool center)
{
    const unsigned int char_width  = 13;
    uint8_t           *pFb0        = gFrameBuffer[Y] + X;
    uint8_t           *pFb1        = pFb0 + 128;
    bool               bCanDisplay = false;

    if (center) {
        uint8_t len = 0;
        for (const char *ptr = string; *ptr; ptr++)
            if (*ptr != ' ') len++; // Ignores spaces for centering

        X -= (len * char_width) / 2; // Centering adjustment
        pFb0 = gFrameBuffer[Y] + X;
        pFb1 = pFb0 + 128;
    }

    for (; *string; string++) {
        char c = *string;
        if (c == '-') c = '9' + 1; // Remap of '-' symbol

        if (bCanDisplay || c != ' ') {
            bCanDisplay = true;
            if (c >= '0' && c <= '9' + 1) {
                memcpy(pFb0 + 2, gFontBigDigits[c - '0'], char_width - 3);
                memcpy(pFb1 + 2, gFontBigDigits[c - '0'] + char_width - 3, char_width - 3);
            } else if (c == '.') {
                memset(pFb1, 0x60, 3); // Replaces the three assignments
                pFb0 += 3;
                pFb1 += 3;
                continue;
            }
        }
        pFb0 += char_width;
        pFb1 += char_width;
    }
}
*/

void UI_DrawPixelBuffer(uint8_t (*buffer)[128], uint8_t x, uint8_t y, bool black)
{
    const uint8_t pattern = 1 << (y % 8);
    if(black)
        buffer[y/8][x] |= pattern;
    else
        buffer[y/8][x] &= ~pattern;
}

static void sort(int16_t *a, int16_t *b)
{
    if(*a > *b) {
        int16_t t = *a;
        *a = *b;
        *b = t;
    }
}

#ifdef ENABLE_FEAT_F4HWN
    /*
    void UI_DrawLineDottedBuffer(uint8_t (*buffer)[128], int16_t x1, int16_t y1, int16_t x2, int16_t y2, bool black)
    {
        if(x2==x1) {
            sort(&y1, &y2);
            for(int16_t i = y1; i <= y2; i+=2) {
                UI_DrawPixelBuffer(buffer, x1, i, black);
            }
        } else {
            const int multipl = 1000;
            int a = (y2-y1)*multipl / (x2-x1);
            int b = y1 - a * x1 / multipl;

            sort(&x1, &x2);
            for(int i = x1; i<= x2; i+=2)
            {
                UI_DrawPixelBuffer(buffer, i, i*a/multipl +b, black);
            }
        }
    }
    */

    void PutPixel(uint8_t x, uint8_t y, bool fill) {
      UI_DrawPixelBuffer(gFrameBuffer, x, y, fill);
    }

    void PutPixelStatus(uint8_t x, uint8_t y, bool fill) {
      UI_DrawPixelBuffer(&gStatusLine, x, y, fill);
    }

    void GUI_DisplaySmallest(const char *pString, uint8_t x, uint8_t y,
                                    bool statusbar, bool fill) {
      uint8_t c;
      uint8_t pixels;
      const uint8_t *p = (const uint8_t *)pString;

      while ((c = *p++) && c != '\0') {
        c -= 0x20;
        for (int i = 0; i < 3; ++i) {
          pixels = gFont3x5[c][i];
          for (int j = 0; j < 6; ++j) {
            if (pixels & 1) {
              if (statusbar)
                PutPixelStatus(x + i, y + j, fill);
              else
                PutPixel(x + i, y + j, fill);
            }
            pixels >>= 1;
          }
        }
        x += 4;
      }
    }

    void GUI_DisplaySmallestInverse(const char *pString, uint8_t x, uint8_t Line,
                                bool statusbar, bool fill, uint8_t end)
    {
        // First draw the string normally
        GUI_DisplaySmallest(pString, x, (Line * 8) + 1, statusbar, fill);

        // Now invert the framebuffer/statusline bits for the rendered area
        uint8_t start = (x - 2);
        uint8_t *buffer = statusbar ? gStatusLine : gFrameBuffer[Line];

        buffer[start] ^= 0x3E;
        for (uint8_t i = start + 1; i < end; i++) {
            buffer[i] ^= 0x7F;
        }
        buffer[end] ^= 0x3E;
    }

    void UI_DisplayUnlockKeyboard(uint8_t shift) {
        if (gEeprom.KEY_LOCK && gKeypadLocked > 0)
        {   // tell user how to unlock the keyboard
            
            //memcpy(gFrameBuffer[shift] + 2, gFontKeyLock, sizeof(gFontKeyLock));
            UI_PrintStringSmallBold(WRX_UI_TEXT_UNLOCK_KEYBOARD, 12, 0, shift);
            //memcpy(gFrameBuffer[shift] + 120, gFontKeyLock, sizeof(gFontKeyLock));

            /*
            for (uint8_t i = 12; i < 116; i++)
            {
                gFrameBuffer[shift][i] ^= 0xFF;
            }
            */
        }
    }

    bool IsEmptyName(const char *name, uint8_t len) {
        if (name[0] == '\0' || name[0] == '\xff')
            return true;
        for (uint8_t i = 0; i < len; i++) {
            if (name[i] != ' ' && name[i] != '\xff' && name[i] != '\0')
                return false;
        }
        return true;
    }
#endif
    
void UI_DrawLineBuffer(uint8_t (*buffer)[128], int16_t x1, int16_t y1, int16_t x2, int16_t y2, bool black)
{
    if(x2==x1) {
        sort(&y1, &y2);
        for(int16_t i = y1; i <= y2; i++) {
            UI_DrawPixelBuffer(buffer, x1, i, black);
        }
    } else {
        const int multipl = 1000;
        int a = (y2-y1)*multipl / (x2-x1);
        int b = y1 - a * x1 / multipl;

        sort(&x1, &x2);
        for(int i = x1; i<= x2; i++)
        {
            UI_DrawPixelBuffer(buffer, i, i*a/multipl +b, black);
        }
    }
}

void UI_DrawRectangleBuffer(uint8_t (*buffer)[128], int16_t x1, int16_t y1, int16_t x2, int16_t y2, bool black)
{
    UI_DrawLineBuffer(buffer, x1,y1, x1,y2, black);
    UI_DrawLineBuffer(buffer, x1,y1, x2,y1, black);
    UI_DrawLineBuffer(buffer, x2,y1, x2,y2, black);
    UI_DrawLineBuffer(buffer, x1,y2, x2,y2, black);
}


void UI_DisplayPopup(const char *string)
{
    UI_DisplayClear();

    // for(uint8_t i = 1; i < 5; i++) {
    //  memset(gFrameBuffer[i]+8, 0x00, 111);
    // }

    // for(uint8_t x = 10; x < 118; x++) {
    //  UI_DrawPixelBuffer(x, 10, true);
    //  UI_DrawPixelBuffer(x, 46-9, true);
    // }

    // for(uint8_t y = 11; y < 37; y++) {
    //  UI_DrawPixelBuffer(10, y, true);
    //  UI_DrawPixelBuffer(117, y, true);
    // }
    // DrawRectangle(9,9, 118,38, true);
    UI_PrintString(string, 9, 118, 2, 8);
    UI_PrintStringSmallNormal(WRX_UI_TEXT_PRESS_EXIT, 9, 118, 6);
}

void UI_DisplayUnavailable(const char *string)
{
    UI_DisplayPopup(string);
    ST7565_BlitFullScreen();
}

void UI_DisplayClear()
{
    memset(gFrameBuffer, 0, sizeof(gFrameBuffer));
}

void UI_StatusClear()
{
    memset(gStatusLine, 0, sizeof(gStatusLine));
}
