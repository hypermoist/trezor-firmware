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

#ifndef TREZORHAL_XDISPLAY_H
#define TREZORHAL_XDISPLAY_H

#include <stdint.h>
#include "gl_dma2d.h"

#include TREZOR_BOARD

// This is a universal API for controlling different types of display
// controllers.
//
// Currently, following displays displays are supported
//
// VG-2864KSWEG01  - OLED Mono / 128x64 pixels  / SPI
//                 - Model T1B1 / Model T2B1
//
// UG-2828SWIG01   - OLED Mono / 128x128 pixels / Parallel
//                 - Early revisions of T2B1
//
// ST7789V         - TFT RGB   / 240x240 pixels / Parallel
//                 - Model T2T1 / Model T3T1
//
// ILI9341         - TFT RGB   / 320x240 pixels / Parallel / LTDC + SPI
//                 - STM32F429I-DISC1 Discovery Board
//
// MIPI            -
//                 - STM32U5A9J-DK Discovery Board

// Fully initializes the display controller.
void display_init(void);

// Called in application to reinitialize an already initialized display
// controller without any distrubing visible effect (blinking, etc.).
void display_reinit(void);

// Waits for any backround operations (such as DMA copying)
// and returns.
//
// The function provides a barrier when jumping between
// boardloader/bootloader and firmware.
void display_finish_actions(void);

// Sets display backlight level ranging from 0 (off)..255 (maximum).
//
// The default backligt level is 0. Without settings it
// to some higher value the displayed pixels are not visible.
// Beware that his also applies to the emulator.
//
// Returns the set level (usually the same value or the
// closest value to the `level` argument)
int display_set_backlight(int level);

// Gets current display level ranging from 0 (off)..255 (maximum).
int display_get_backlight(void);

// Sets the display orientation.
//
// May accept one of following values: 0, 90, 180, 270
// but accepted values are model-dependent.
// Default display orientation is always 0.
//
// Returns the set orientation
int display_set_orientation(int angle);

// Gets the display's current orientation
//
// Returned value is one of 0, 90, 180, 270.
int display_get_orientation(void);

#ifdef XFRAMEBUFFER
// Provides pointer to the inactive (writeable) framebuffer.
//
// If framebuffer is not available yet due to display refreshing etc.,
// the function may block until the buffer is ready to write.
void *display_get_frame_addr(void);

#else  // XFRAMEBUFFER

// Waits for the vertical synchronization pulse.
//
// Used for synchronization with the display refresh cycle
// to achieve tearless UX if possible when not using a frame buffer.
void display_wait_for_sync(void);
#endif

// Swaps the frame buffers
//
// The function waits for vertical synchronization and
// swaps the active (currently displayed) and the inactive frame buffers.
void display_refresh(void);

//
void display_set_compatible_settings(void);

// Functions for drawing on the display
// Fills a rectangle with a specified color
void display_fill(const dma2d_params_t *dp);

// Copies an RGB565 bitmap to a specified rectangle
void display_copy_rgb565(const dma2d_params_t *dp);

// Copies a MONO4 bitmap to a specified rectangle
void display_copy_mono4(const dma2d_params_t *dp);

// Copies a MONO1P bitmap to a specified rectangle
void display_copy_mono1p(const dma2d_params_t *dp);

// Save the screen content to a file.
//
// The function is available only on the emulator
const char *display_save(const char *prefix);
void display_clear_save(void);

#include "xdisplay_legacy.h"

#endif  // TREZORHAL_XDISPLAY_H