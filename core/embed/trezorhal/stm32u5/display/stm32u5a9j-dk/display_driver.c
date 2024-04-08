/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <stdint.h>
#include <string.h>

#include TREZOR_BOARD
#include STM32_HAL_H

#include "display_internal.h"
#include "xdisplay.h"

#if (DISPLAY_RESX != 480) || (DISPLAY_RESY != 480)
#error "Incompatible display resolution"
#endif

// Display driver context.
typedef struct {
  // Current display orientation (0, 90, 180, 270)
  int orientation_angle;
  // Current backlight level ranging from 0 to 255
  int backlight_level;
} display_driver_t;

// Display driver instance
static display_driver_t g_display_driver;

void display_init(void) {
  RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

  // Initializes the common periph clock
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_LTDC | RCC_PERIPHCLK_DSI;
  PeriphClkInit.DsiClockSelection = RCC_DSICLKSOURCE_PLL3;
  PeriphClkInit.LtdcClockSelection = RCC_LTDCCLKSOURCE_PLL3;
  PeriphClkInit.PLL3.PLL3Source = RCC_PLLSOURCE_HSE;
  PeriphClkInit.PLL3.PLL3M = 4;
  PeriphClkInit.PLL3.PLL3N = 125;
  PeriphClkInit.PLL3.PLL3P = 8;
  PeriphClkInit.PLL3.PLL3Q = 2;
  PeriphClkInit.PLL3.PLL3R = 24;
  PeriphClkInit.PLL3.PLL3RGE = RCC_PLLVCIRANGE_0;
  PeriphClkInit.PLL3.PLL3FRACN = 0;
  PeriphClkInit.PLL3.PLL3ClockOut = RCC_PLL3_DIVP | RCC_PLL3_DIVR;
  HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit);

  // Clear framebuffers
  memset(physical_frame_buffer_0, 0x00, PHYSICAL_FRAME_BUFFER_SIZE);
  memset(physical_frame_buffer_1, 0x00, PHYSICAL_FRAME_BUFFER_SIZE);

  BSP_LCD_Init(0, LCD_ORIENTATION_PORTRAIT);
  BSP_LCD_SetBrightness(0, 100);
  BSP_LCD_DisplayOn(0);
}

void display_reinit(void) {
  BSP_LCD_Reinit(0);
  if (current_frame_buffer == 0) {
    BSP_LCD_SetFrameBuffer(0, GFXMMU_VIRTUAL_BUFFER0_BASE_S);
  } else {
    BSP_LCD_SetFrameBuffer(0, GFXMMU_VIRTUAL_BUFFER1_BASE_S);
  }
}

void display_finish_actions(void) {
  // Not used and intentionally left empty
}

int display_set_backlight(int level) {
  display_driver_t* drv = &g_display_driver;

  // Just emulation, not doing anything
  drv->backlight_level = level;
  return level;
}

int display_get_backlight(void) {
  display_driver_t* drv = &g_display_driver;

  return drv->orientation_angle;
}

int display_set_orientation(int angle) {
  display_driver_t* drv = &g_display_driver;

  if (angle == 0 || angle == 90 || angle == 180 || angle == 270) {
    // Just emulation, not doing anything
    drv->orientation_angle = angle;
  }

  return drv->orientation_angle;
}

int display_get_orientation(void) {
  display_driver_t* drv = &g_display_driver;

  return drv->orientation_angle;
}

const char* display_save(const char* prefix) { return NULL; }

void display_clear_save(void) {}

void display_set_compatible_settings() {}

// Functions for drawing on display
/*

// Fills a rectangle with a specified color
void display_fill(gdc_dma2d_t *dp);

// Copies an RGB565 bitmap to specified rectangle
void display_copy_rgb565(gdc_dma2d_t *dp);

// Copies a MONO4 bitmap to specified rectangle
void display_copy_mono4(gdc_dma2d_t *dp);

// Copies a MONO1P bitmap to specified rectangle
void display_copy_mono1p(gdc_dma2d_t *dp);
*/
