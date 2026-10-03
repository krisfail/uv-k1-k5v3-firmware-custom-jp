/* Access to the fixed external Japanese font and channel-name table. */

#include <string.h>

#include "driver/flash_layout.h"
#include "driver/py25q16.h"
#include "japanese_font.h"
#include "misc.h"

static bool JPFONT_RangeContains(uint32_t base, uint32_t size,
                                 uint32_t address, uint32_t length)
{
    return address >= base && address - base <= size && length <= size - (address - base);
}

bool JPFONT_IsExternalRange(uint32_t address, uint32_t size)
{
    /* Keep this as an allowlist.  The compile-time checks in flash_layout.h
     * keep both resources away from the complete calibration sector. */
    return JPFONT_RangeContains(JAPANESE_FONT_FLASH_BASE,
                                JAPANESE_FONT_TOTAL_BYTES, address, size) ||
           JPFONT_RangeContains(JAPANESE_NAME_TABLE_BASE,
                                JAPANESE_NAME_TABLE_SIZE, address, size);
}

bool JPFONT_ReadExternal(uint32_t address, void *buffer, uint32_t size)
{
    if (buffer == NULL || !JPFONT_IsExternalRange(address, size))
        return false;

    PY25Q16_ReadBuffer(address, buffer, size);
    return true;
}

bool JPFONT_WriteExternal(uint32_t address, const void *buffer, uint32_t size)
{
    if (buffer == NULL || !JPFONT_IsExternalRange(address, size))
        return false;

    PY25Q16_WriteBuffer(address, buffer, size, false);
    return true;
}

static bool JPFONT_FindGlyph(uint16_t codepoint, uint16_t *glyph_index)
{
    uint16_t low = 0;
    uint16_t high = JAPANESE_FONT_GLYPH_COUNT;

    while (low < high)
    {
        const uint16_t middle = low + (uint16_t)((high - low) / 2u);
        uint8_t entry[4];
        const uint32_t address = JAPANESE_FONT_FLASH_BASE +
                                 JAPANESE_FONT_INDEX_OFFSET +
                                 ((uint32_t)middle * 4u);

        if (!JPFONT_ReadExternal(address, entry, sizeof(entry)))
            return false;

        const uint16_t entry_codepoint = (uint16_t)entry[0] |
                                         ((uint16_t)entry[1] << 8);
        if (entry_codepoint < codepoint)
        {
            low = middle + 1u;
        }
        else if (entry_codepoint > codepoint)
        {
            high = middle;
        }
        else
        {
            *glyph_index = (uint16_t)entry[2] |
                           ((uint16_t)entry[3] << 8);
            return *glyph_index < JAPANESE_FONT_GLYPH_COUNT;
        }
    }

    return false;
}

bool JPFONT_HasGlyph(uint16_t codepoint)
{
    uint16_t glyph_index;
    return JPFONT_FindGlyph(codepoint, &glyph_index);
}

bool JPFONT_ReadGlyph(uint16_t codepoint, uint8_t *glyph)
{
    uint16_t glyph_index;

    if (glyph == NULL || !JPFONT_FindGlyph(codepoint, &glyph_index))
        return false;

    return JPFONT_ReadExternal(
        JAPANESE_FONT_FLASH_BASE + JAPANESE_FONT_BITMAP_OFFSET +
            ((uint32_t)glyph_index * JAPANESE_FONT_GLYPH_BYTES),
        glyph, JAPANESE_FONT_GLYPH_BYTES);
}

bool JPFONT_HasGlyph14(uint16_t codepoint)
{
    uint16_t glyph_index;
    return JPFONT_FindGlyph(codepoint, &glyph_index);
}

bool JPFONT_ReadGlyph14(uint16_t codepoint, uint8_t *glyph)
{
    uint16_t glyph_index;

    if (glyph == NULL || !JPFONT_FindGlyph(codepoint, &glyph_index))
        return false;

    return JPFONT_ReadExternal(
        JAPANESE_FONT_FLASH_BASE + JAPANESE_FONT_BITMAP14_OFFSET +
            ((uint32_t)glyph_index * JAPANESE_FONT_GLYPH14_BYTES),
        glyph, JAPANESE_FONT_GLYPH14_BYTES);
}

bool JPFONT_HasGlyph8(uint16_t codepoint)
{
    uint16_t glyph_index;
    return JPFONT_FindGlyph(codepoint, &glyph_index);
}

bool JPFONT_ReadGlyph8(uint16_t codepoint, uint8_t *glyph)
{
    uint16_t glyph_index;

    if (glyph == NULL || !JPFONT_FindGlyph(codepoint, &glyph_index))
        return false;

    return JPFONT_ReadExternal(
        JAPANESE_FONT_FLASH_BASE + JAPANESE_FONT_BITMAP8_OFFSET +
            ((uint32_t)glyph_index * JAPANESE_FONT_GLYPH8_BYTES),
        glyph, JAPANESE_FONT_GLYPH8_BYTES);
}

#ifdef ENABLE_LCD_DEBUG
typedef struct
{
    uint16_t channel;
    char     name[JAPANESE_NAME_RECORD_SIZE];
} JPFONT_DebugChannelName_t;

static JPFONT_DebugChannelName_t gJpfontDebugNames[2];
static uint8_t gJpfontDebugNameCount;

void JPFONT_DebugClearChannelNames(void)
{
    memset(gJpfontDebugNames, 0, sizeof(gJpfontDebugNames));
    gJpfontDebugNameCount = 0u;
}

void JPFONT_DebugSetChannelName(const uint16_t channel, const char *name)
{
    if (name == NULL)
        return;

    uint8_t slot = 0u;
    while (slot < gJpfontDebugNameCount &&
           gJpfontDebugNames[slot].channel != channel)
        slot++;

    if (slot >= ARRAY_SIZE(gJpfontDebugNames))
        return;
    if (slot == gJpfontDebugNameCount)
        gJpfontDebugNameCount++;

    const size_t length = strlen(name) < JAPANESE_NAME_PAYLOAD_MAX
        ? strlen(name) : JAPANESE_NAME_PAYLOAD_MAX;
    gJpfontDebugNames[slot].channel = channel;
    memcpy(gJpfontDebugNames[slot].name, name, length);
    gJpfontDebugNames[slot].name[length] = '\0';
}
#endif

uint8_t JPFONT_ReadChannelName(uint16_t channel, char *buffer, uint8_t capacity)
{
    uint8_t record[JAPANESE_NAME_RECORD_SIZE];
    uint8_t length = 0;

    if (buffer == NULL || capacity == 0 || channel >= MR_CHANNELS_MAX)
        return 0;

    memset(buffer, 0, capacity);
#ifdef ENABLE_LCD_DEBUG
    for (uint8_t slot = 0u; slot < gJpfontDebugNameCount; slot++)
    {
        if (gJpfontDebugNames[slot].channel != channel)
            continue;

        length = (uint8_t)strlen(gJpfontDebugNames[slot].name);
        if (length >= capacity)
            length = (uint8_t)(capacity - 1u);
        memcpy(buffer, gJpfontDebugNames[slot].name, length);
        buffer[length] = '\0';
        return length;
    }
#endif
    if (!JPFONT_ReadExternal(
            JAPANESE_NAME_TABLE_BASE +
                ((uint32_t)channel * JAPANESE_NAME_RECORD_SIZE),
            record, sizeof(record)))
        return 0;

    while (length < JAPANESE_NAME_PAYLOAD_MAX &&
           record[length] != 0x00u && record[length] != 0xFFu)
        length++;

    if (length >= capacity)
        length = (uint8_t)(capacity - 1u);
    memcpy(buffer, record, length);
    buffer[length] = '\0';
    return length;
}
