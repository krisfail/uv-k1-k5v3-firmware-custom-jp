/* Access to the fixed external Japanese font and channel-name table. */
#ifndef APP_JAPANESE_FONT_H
#define APP_JAPANESE_FONT_H

#include <stdbool.h>
#include <stdint.h>

#include "japanese_font_external.h"

bool JPFONT_ReadExternal(uint32_t address, void *buffer, uint32_t size);
bool JPFONT_WriteExternal(uint32_t address, const void *buffer, uint32_t size);
bool JPFONT_IsExternalRange(uint32_t address, uint32_t size);

bool JPFONT_HasGlyph(uint16_t codepoint);
bool JPFONT_ReadGlyph(uint16_t codepoint, uint8_t *glyph);
bool JPFONT_HasGlyph14(uint16_t codepoint);
bool JPFONT_ReadGlyph14(uint16_t codepoint, uint8_t *glyph);
bool JPFONT_HasGlyph8(uint16_t codepoint);
bool JPFONT_ReadGlyph8(uint16_t codepoint, uint8_t *glyph);
uint8_t JPFONT_ReadChannelName(uint16_t channel, char *buffer, uint8_t capacity);

#ifdef ENABLE_LCD_DEBUG
void JPFONT_DebugClearChannelNames(void);
void JPFONT_DebugSetChannelName(uint16_t channel, const char *name);
#endif

#endif /* APP_JAPANESE_FONT_H */
