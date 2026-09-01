/* LCD browser for every glyph in the external-font test image. */

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include "app/font_glyph_test.h"
#include "driver/backlight.h"
#include "driver/keyboard.h"
#include "driver/st7565.h"
#include "driver/system.h"
#include "japanese_font.h"

#define FONT_TEST_COLUMNS             8u
#define FONT_TEST_ROWS                4u
#define FONT_TEST_GLYPHS_PER_PAGE     (FONT_TEST_COLUMNS * FONT_TEST_ROWS)
#define FONT_TEST_INDEX_ENTRY_BYTES   4u
#define FONT_TEST_INDEX_PAGE_BYTES    \
    (FONT_TEST_GLYPHS_PER_PAGE * FONT_TEST_INDEX_ENTRY_BYTES)
#define FONT_TEST_PAGE_COUNT          \
    ((JAPANESE_FONT_GLYPH_COUNT + FONT_TEST_GLYPHS_PER_PAGE - 1u) / \
     FONT_TEST_GLYPHS_PER_PAGE)

static uint8_t *FontTest_PageBuffer(const uint8_t page)
{
    /* LCD page 0 is the status buffer; pages 1..7 are the normal framebuffer.
     * Together they provide four complete 16-pixel rows. */
    return page == 0u ? gStatusLine : gFrameBuffer[page - 1u];
}

static void FontTest_ClearDisplay(void)
{
    memset(gStatusLine, 0, sizeof(gStatusLine));
    memset(gFrameBuffer, 0, sizeof(gFrameBuffer));
}

static void FontTest_DrawGlyph(const uint8_t column, const uint8_t row,
                               const uint8_t *glyph)
{
    const uint8_t x = (uint8_t)(column * 16u);
    const uint8_t top_page = (uint8_t)(row * 2u);

    for (uint8_t glyph_page = 0u; glyph_page < 2u; glyph_page++)
    {
        uint8_t *destination = FontTest_PageBuffer(
            (uint8_t)(top_page + glyph_page));

        for (uint8_t glyph_column = 0u; glyph_column < 16u; glyph_column++)
        {
            uint8_t value = 0u;
            for (uint8_t glyph_row = 0u; glyph_row < 8u; glyph_row++)
            {
                const uint8_t source_row =
                    (uint8_t)(glyph_page * 8u + glyph_row);
                const uint16_t bitmap_row =
                    (uint16_t)glyph[source_row * 2u] |
                    ((uint16_t)glyph[source_row * 2u + 1u] << 8);
                if (bitmap_row & (uint16_t)(0x8000u >> glyph_column))
                    value |= (uint8_t)(1u << glyph_row);
            }
            destination[x + glyph_column] = value;
        }
    }
}

static bool FontTest_ReadPage(const uint16_t page)
{
    uint8_t index_bytes[FONT_TEST_INDEX_PAGE_BYTES];
    const uint32_t first_entry =
        (uint32_t)page * FONT_TEST_GLYPHS_PER_PAGE;
    const uint32_t remaining = JAPANESE_FONT_GLYPH_COUNT - first_entry;
    const uint32_t entry_count = remaining < FONT_TEST_GLYPHS_PER_PAGE
        ? remaining : FONT_TEST_GLYPHS_PER_PAGE;
    const uint32_t index_size = entry_count * FONT_TEST_INDEX_ENTRY_BYTES;

    FontTest_ClearDisplay();
    if (!JPFONT_ReadExternal(
            JAPANESE_FONT_FLASH_BASE + JAPANESE_FONT_INDEX_OFFSET +
                first_entry * FONT_TEST_INDEX_ENTRY_BYTES,
            index_bytes, index_size))
        return false;

    for (uint32_t slot = 0u; slot < entry_count; slot++)
    {
        const uint32_t offset = slot * FONT_TEST_INDEX_ENTRY_BYTES;
        const uint16_t glyph_index =
            (uint16_t)index_bytes[offset + 2u] |
            ((uint16_t)index_bytes[offset + 3u] << 8);
        uint8_t glyph[JAPANESE_FONT_GLYPH_BYTES];

        if (glyph_index >= JAPANESE_FONT_GLYPH_COUNT ||
            !JPFONT_ReadExternal(
                JAPANESE_FONT_FLASH_BASE + JAPANESE_FONT_BITMAP_OFFSET +
                    ((uint32_t)glyph_index * JAPANESE_FONT_GLYPH_BYTES),
                glyph, sizeof(glyph)))
            return false;

        FontTest_DrawGlyph(
            (uint8_t)(slot % FONT_TEST_COLUMNS),
            (uint8_t)(slot / FONT_TEST_COLUMNS),
            glyph);
    }

    ST7565_BlitStatusLine();
    ST7565_BlitFullScreen();
    return true;
}

static bool FontTest_HandleKey(const KEY_Code_t key, uint16_t *page)
{
    switch (key)
    {
        case KEY_UP:
            *page = *page == 0u ? (uint16_t)(FONT_TEST_PAGE_COUNT - 1u)
                                : (uint16_t)(*page - 1u);
            return true;

        case KEY_DOWN:
            *page = (uint16_t)((*page + 1u) % FONT_TEST_PAGE_COUNT);
            return true;

        case KEY_0:
            *page = 0u;
            return true;

        case KEY_9:
            *page = (uint16_t)(FONT_TEST_PAGE_COUNT - 1u);
            return true;

        default:
            return false;
    }
}

void FONT_GLYPH_TEST_Run(void)
{
    uint16_t page = 0u;
    KEY_Code_t previous = KEYBOARD_Poll();

    /* This image skips settings initialization.  Set the backlight explicitly
     * so the zero-initialized BACKLIGHT_TIME cannot turn it off. */
    BACKLIGHT_SetBrightness(10u);
    BACKLIGHT_UpdateTickless();
    (void)FontTest_ReadPage(page);

    while (true)
    {
        const KEY_Code_t current = KEYBOARD_Poll();
        if (current != previous && current != KEY_INVALID)
        {
            if (FontTest_HandleKey(current, &page))
                (void)FontTest_ReadPage(page);
        }
        previous = current;
        SYSTEM_DelayMs(10u);
    }
}
