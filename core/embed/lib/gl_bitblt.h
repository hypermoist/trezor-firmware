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

#ifndef GL_BITBLT_H
#define GL_BITBLT_H

#include <stdbool.h>
#include <stdint.h>

#include "gl_color.h"

typedef struct {
  // Destination bitma[
  // Following fields are used for all operations
  uint16_t height;
  uint16_t width;
  void* dst_row;
  uint16_t dst_x;
  uint16_t dst_y;
  uint16_t dst_stride;

  // Source bitmap
  // Used for copying and blending, but src_fg & src_alpha
  // fields are also used for fill operation
  void* src_row;
  uint16_t src_x;
  uint16_t src_y;
  uint16_t src_stride;
  gl_color_t src_fg;
  gl_color_t src_bg;
  uint8_t src_alpha;

} gl_bitblt_t;

void gl_rgb565_fill(const gl_bitblt_t* bb);
void gl_rgb565_copy_mono4(const gl_bitblt_t* bb);
void gl_rgb565_copy_rgb565(const gl_bitblt_t* bb);
void gl_rgb565_blend_mono4(const gl_bitblt_t* bb);

void gl_rgba8888_fill(const gl_bitblt_t* bb);
void gl_rgba8888_copy_mono4(const gl_bitblt_t* bb);
void gl_rgba8888_copy_rgb565(const gl_bitblt_t* bb);
void gl_rgba8888_copy_rgba8888(const gl_bitblt_t* bb);
void gl_rgba8888_blend_mono4(const gl_bitblt_t* bb);

void gl_mono8_fill(const gl_bitblt_t* bb);
void gl_mono8_copy_mono1p(const gl_bitblt_t* bb);
void gl_mono8_copy_mono4(const gl_bitblt_t* bb);
void gl_mono8_blend_mono1p(const gl_bitblt_t* bb);
void gl_mono8_blend_mono4(const gl_bitblt_t* bb);

#endif  // GL_BITBLT_H