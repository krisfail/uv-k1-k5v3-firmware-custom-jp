/* Fixed external-flash layout for the EEPROM bridge and Japanese resources. */
#ifndef DRIVER_FLASH_LAYOUT_H
#define DRIVER_FLASH_LAYOUT_H

#include "japanese_font_external.h"

/* The logical EEPROM window is kept for compatibility with the stock tools. */
#define K1_CALIBRATION_LOGICAL_BASE       0xB000u
#define K1_CALIBRATION_LOGICAL_END        0xB200u

/* Reserve the complete 4 KiB sector containing calibration data. */
#define K1_EXTERNAL_FLASH_SIZE            0x200000u
#define K1_CALIBRATION_FLASH_BASE         0x010000u
#define K1_CALIBRATION_FLASH_SECTOR_END   0x011000u

#define K1_JAPANESE_FONT_FLASH_END       \
    (JAPANESE_FONT_FLASH_BASE + JAPANESE_FONT_TOTAL_BYTES)
#define K1_JAPANESE_NAME_TABLE_END      \
    (JAPANESE_NAME_TABLE_BASE + JAPANESE_NAME_TABLE_SIZE)

/* A layout mistake must stop the build instead of becoming a field bug. */
#if JAPANESE_FONT_FLASH_BASE < K1_CALIBRATION_FLASH_SECTOR_END && \
    K1_CALIBRATION_FLASH_BASE < K1_JAPANESE_FONT_FLASH_END
#error "Japanese font range overlaps the calibration sector"
#endif

#if JAPANESE_NAME_TABLE_BASE < K1_CALIBRATION_FLASH_SECTOR_END && \
    K1_CALIBRATION_FLASH_BASE < K1_JAPANESE_NAME_TABLE_END
#error "Japanese name range overlaps the calibration sector"
#endif

#if K1_JAPANESE_FONT_FLASH_END > JAPANESE_NAME_TABLE_BASE && \
    JAPANESE_FONT_FLASH_BASE < K1_JAPANESE_NAME_TABLE_END
#error "Japanese font range overlaps the Japanese name table"
#endif

#if K1_JAPANESE_NAME_TABLE_END > K1_EXTERNAL_FLASH_SIZE
#error "Japanese name range exceeds the external flash"
#endif

#endif /* DRIVER_FLASH_LAYOUT_H */
