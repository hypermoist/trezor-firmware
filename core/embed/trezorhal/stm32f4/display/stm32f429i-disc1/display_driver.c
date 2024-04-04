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
#include "ili9341_spi.h"
#include "xdisplay.h"

#if (DISPLAY_RESX != 240) || (DISPLAY_RESY != 320)
#error "Incompatible display resolution"
#endif

// Display driver context.
typedef struct {
  // Pointer to the frame buffer
  uint16_t *framebuf;
  // Current display orientation (0, 90, 180, 270)
  int orientation_angle;
  // Current backlight level ranging from 0 to 255
  int backlight_level;
} display_driver_t;

// Display driver instance
static display_driver_t g_display_driver;

void display_init(void) {
  display_driver_t *drv = &g_display_driver;
  memset(drv, 0, sizeof(display_driver_t));
  drv->framebuf = (uint16_t *)FRAME_BUFFER_ADDR;

  // Initialize LTDC controller
  BSP_LCD_Init();
  // Initialize external display controller
  ili9341_init();
}

void display_reinit(void) {
  display_driver_t *drv = &g_display_driver;
  memset(drv, 0, sizeof(display_driver_t));
  drv->framebuf = (uint16_t *)FRAME_BUFFER_ADDR;
}

void display_finish_actions(void) {
  // Not used and intentionally left empty
}

int display_set_backlight(int level) {
  display_driver_t *drv = &g_display_driver;

  // Just emulation, not doing anything
  drv->backlight_level = level;
  return level;
}

int display_get_backlight(void) {
  display_driver_t *drv = &g_display_driver;

  return drv->backlight_level;
}

int display_set_orientation(int angle) {
  display_driver_t *drv = &g_display_driver;

  if (angle == 0 || angle == 90 || angle == 180 || angle == 270) {
    // Just emulation, not doing anything
    drv->orientation_angle = angle;
  }

  return drv->orientation_angle;
}

int display_get_orientation(void) {
  display_driver_t *drv = &g_display_driver;

  return drv->orientation_angle;
}

void *display_get_frame_addr(void) {
  display_driver_t *drv = &g_display_driver;

  return (void *)drv->framebuf;
}

void display_refresh(void) {
  // Do nothing as using just a single frame buffer
}

void display_set_compatible_settings() {}

void display_fill(const dma2d_params_t *dp) {
  display_driver_t *drv = &g_display_driver;

  dma2d_params_t dp_new = *dp;
  dp_new.dst_row = drv->framebuf + (DISPLAY_RESX * dp_new.dst_y);
  dp_new.dst_stride = DISPLAY_RESX * 2;

  rgb565_fill(&dp_new);
}

void display_copy_rgb565(const dma2d_params_t *dp) {
  display_driver_t *drv = &g_display_driver;

  dma2d_params_t dp_new = *dp;
  dp_new.dst_row = drv->framebuf + (DISPLAY_RESX * dp_new.dst_y);
  dp_new.dst_stride = DISPLAY_RESX * 2;

  rgb565_copy_rgb565(&dp_new);
}

void display_copy_mono4(const dma2d_params_t *dp) {
  display_driver_t *drv = &g_display_driver;

  dma2d_params_t dp_new = *dp;
  dp_new.dst_row = drv->framebuf + (DISPLAY_RESX * dp_new.dst_y);
  dp_new.dst_stride = DISPLAY_RESX * 2;

  rgb565_copy_mono4(&dp_new);
}
