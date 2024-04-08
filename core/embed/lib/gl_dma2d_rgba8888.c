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

#include "gl_dma2d.h"

#if USE_DMA2D
#include "dma2d.h"
#endif

bool rgba8888_fill(const dma2d_params_t* dp) {
#if defined(USE_DMA2D) && !defined(TREZOR_EMULATOR)
  if (dma2d_accessible(dp->dst_row)) {
    return dma2d_rgba8888_fill(dp);
  } else
#endif
  {
    uint32_t* dst_ptr = (uint32_t*)dp->dst_row + dp->dst_x;
    uint16_t height = dp->height;

    if (dp->src_alpha == 255) {
      while (height-- > 0) {
        for (int x = 0; x < dp->width; x++) {
          dst_ptr[x] = gl_color_to_color32(dp->src_fg);
        }
        dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
      }
    } else {
      uint8_t alpha = dp->src_alpha;
      while (height-- > 0) {
        for (int x = 0; x < dp->width; x++) {
          dst_ptr[x] = gl_color32_blend_a8(
              dp->src_fg, gl_color32_to_color(dst_ptr[x]), alpha);
        }
        dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
      }
    }
    return true;
  }
}

bool rgba8888_copy_mono4(const dma2d_params_t* dp) {
#if defined(USE_DMA2D) && !defined(TREZOR_EMULATOR)
  if (dma2d_accessible(dp->dst_row) && dma2d_accessible(dp->src_row)) {
    return dma2d_rgba8888_copy_mono4(dp);
  } else
#endif
  {
    const gl_color32_t* gradient =
        gl_color32_gradient_a4(dp->src_fg, dp->src_bg);

    uint32_t* dst_ptr = (uint32_t*)dp->dst_row + dp->dst_x;
    uint8_t* src_row = (uint8_t*)dp->src_row;
    uint16_t height = dp->height;

    while (height-- > 0) {
      for (int x = 0; x < dp->width; x++) {
        uint8_t fg_data = src_row[(x + dp->src_x) / 2];
        uint8_t fg_lum = (x + dp->src_x) & 1 ? fg_data >> 4 : fg_data & 0xF;
        dst_ptr[x] = gradient[fg_lum];
      }
      dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
      src_row += dp->src_stride / sizeof(*src_row);
    }

    return true;
  }
}

bool rgba8888_copy_rgb565(const dma2d_params_t* dp) {
#if defined(USE_DMA2D) && !defined(TREZOR_EMULATOR)
  if (dma2d_accessible(dp->dst_row) && dma2d_accessible(dp->src_row)) {
    return dma2d_rgba8888_copy_rgb565(dp);
  } else
#endif
  {
    uint32_t* dst_ptr = (uint32_t*)dp->dst_row + dp->dst_x;
    uint16_t* src_ptr = (uint16_t*)dp->src_row + dp->src_x;
    uint16_t height = dp->height;

    while (height-- > 0) {
      for (int x = 0; x < dp->width; x++) {
        dst_ptr[x] = gl_color16_to_color32(src_ptr[x]);
      }
      dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
      src_ptr += dp->src_stride / sizeof(*src_ptr);
    }

    return true;
  }
}

bool rgba8888_copy_rgba8888(const dma2d_params_t* dp) {
#if defined(USE_DMA2D) && !defined(TREZOR_EMULATOR)
  if (dma2d_accessible(dp->dst_row) && dma2d_accessible(dp->src_row)) {
    return dma2d_rgba8888_copy_rgba8888(dp);
  } else
#endif
  {
    uint32_t* dst_ptr = (uint32_t*)dp->dst_row + dp->dst_x;
    uint32_t* src_ptr = (uint32_t*)dp->src_row + dp->src_x;
    uint16_t height = dp->height;

    while (height-- > 0) {
      for (int x = 0; x < dp->width; x++) {
        dst_ptr[x] = src_ptr[x];
      }
      dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
      src_ptr += dp->src_stride / sizeof(*src_ptr);
    }

    return true;
  }
}

bool rgba8888_blend_mono4(const dma2d_params_t* dp) {
#if defined(USE_DMA2D) && !defined(TREZOR_EMULATOR)
  if (dma2d_accessible(dp->dst_row) && dma2d_accessible(dp->src_row)) {
    return dma2d_rgba8888_blend_mono4(dp);
  } else
#endif
  {
    uint32_t* dst_ptr = (uint32_t*)dp->dst_row + dp->dst_x;
    uint8_t* src_row = (uint8_t*)dp->src_row;
    uint16_t height = dp->height;

    while (height-- > 0) {
      for (int x = 0; x < dp->width; x++) {
        uint8_t fg_data = src_row[(x + dp->src_x) / 2];
        uint8_t fg_alpha = (x + dp->src_x) & 1 ? fg_data >> 4 : fg_data & 0x0F;
        dst_ptr[x] = gl_color32_blend_a4(
            dp->src_fg, gl_color32_to_color(dst_ptr[x]), fg_alpha);
      }
      dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
      src_row += dp->src_stride / sizeof(*src_row);
    }

    return true;
  }
}
