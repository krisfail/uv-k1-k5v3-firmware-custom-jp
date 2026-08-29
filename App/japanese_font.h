/* Fixed external Japanese bitmap font and channel-name storage. */
#ifndef APP_JAPANESE_FONT_H
#define APP_JAPANESE_FONT_H

#include <stdbool.h>
#include <stdint.h>

#include "japanese_font_external.h"

bool JPFONT_ReadExternal(uint32_t address, void *buffer, uint32_t size);
bool JPFONT_WriteExternal(uint32_t address, const void *buffer, uint32_t size);
bool JPFONT_IsExternalRange(uint32_t address, uint32_t size);

bool JPFONT_ReadGlyph(uint16_t codepoint, uint8_t *glyph);
uint8_t JPFONT_ReadChannelName(uint16_t channel, char *buffer, uint8_t capacity);

#endif /* APP_JAPANESE_FONT_H */
