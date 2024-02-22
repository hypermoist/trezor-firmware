use crate::ui::{
    canvas::{Bitmap, BitmapFormat, BitmapView, Canvas},
    geometry::{Offset, Point, Rect},
};

use super::{DrawingCache, Renderer, Shape, ShapeClone};

use without_alloc::alloc::LocalAllocLeakExt;

/// A shape for rendering compressed JPEG images.
pub struct JpegImage {
    /// Left-top corner
    pos: Point,
    /// JPEG data
    jpeg: &'static [u8],
    /// Scale factor (default 0)
    scale: u8,
    /// Blurring radius or 0 if no blurring required (default 0)
    blur_radius: usize,
    /// Set if blurring is pending
    /// (used only during image drawing).
    blur_tag: Option<u32>,
}

impl JpegImage {
    pub fn new(pos: Point, jpeg: &'static [u8]) -> Self {
        JpegImage {
            pos,
            scale: 0,
            blur_radius: 0,
            jpeg,
            blur_tag: None,
        }
    }

    pub fn with_scale(self, scale: u8) -> Self {
        assert!(scale <= 3);
        Self { scale, ..self }
    }

    pub fn with_blur(self, blur_radius: usize) -> Self {
        Self {
            blur_radius,
            ..self
        }
    }

    pub fn render(self, renderer: &mut impl Renderer) {
        renderer.render_shape(self);
    }
}

impl Shape for JpegImage {
    fn bounds(&self, cache: &DrawingCache) -> Rect {
        let size = unwrap!(cache.jpeg().get_size(self.jpeg, self.scale), "Invalid JPEG");
        Rect::from_top_left_and_size(self.pos, size)
    }

    fn cleanup(&mut self, _cache: &DrawingCache) {
        self.blur_tag = None;
    }

    /*
    // Faster implementation suitable for DirectRenderer without blurring support
    // (but is terribly slow on ProgressiveRenderer if slices are not aligned
    //  to JPEG MCUs )
    fn draw(&mut self, canvas: &mut dyn RgbCanvasEx, cache: &DrawingCache) {
        let clip = canvas.viewport().relative_clip(self.bounds(cache)).clip;

        // translate clip to JPEG relative coordinates
        let clip = clip.translate(-canvas.viewport().origin);
        let clip = clip.translate((-self.pos).into());

        unwrap!(
            cache.jpeg().decompress_mcu(
                self.jpeg,
                self.scale,
                clip.top_left(),
                &mut |mcu_r, mcu_bitmap| {
                    // Draw single MCU
                    canvas.draw_bitmap(mcu_r.translate(self.pos.into()), mcu_bitmap);
                    // Return true if we are not done yet
                    mcu_r.x1 < clip.x1 || mcu_r.y1 < clip.y1
                }
            ),
            "Invalid JPEG"
        );
    }*/

    // This is a little bit slower implementation suitable for ProgressiveRenderer
    fn draw(&mut self, canvas: &mut dyn Canvas, cache: &DrawingCache) {
        let clip = canvas.viewport().relative_clip(self.bounds(cache)).clip;

        // Translate clip to JPEG relative coordinates
        let clip = clip.translate(-canvas.viewport().origin);
        let clip = clip.translate((-self.pos).into());

        if self.blur_radius == 0 {
            // Draw JPEG without blurring

            // Routine for drawing single JPEG MCU
            let draw_mcu = &mut |row_r: Rect, row_bitmap: BitmapView| {
                // Draw a row of decoded MCUs
                canvas.draw_bitmap(row_r.translate(self.pos.into()), row_bitmap);
                // Return true if we are not done yet
                row_r.y1 < clip.y1
            };

            unwrap!(
                cache
                    .jpeg()
                    .decompress_row(self.jpeg, self.scale, clip.y0, draw_mcu),
                "Invalid JPEG"
            );
        } else {
            // Draw JPEG with blurring effect
            let jpeg_size = self.bounds(cache).size();

            // Get a single line working bitmap
            let buff = &mut unwrap!(cache.image_buff(), "No image buffer");
            let mut slice = unwrap!(
                Bitmap::new(
                    BitmapFormat::RGB565,
                    None,
                    Offset::new(jpeg_size.x, 1),
                    None,
                    &mut buff[..]
                ),
                "Too small buffer"
            );

            // Get the blurring algorithm instance
            let mut blur_cache = cache.blur();
            let (blur, blur_tag) =
                unwrap!(blur_cache.get(jpeg_size, self.blur_radius, self.blur_tag));
            self.blur_tag = Some(blur_tag);

            if let Some(y) = blur.push_ready() {
                // A function for drawing a row of JPEG MCUs
                let draw_row = &mut |row_r: Rect, jpeg_slice: BitmapView| {
                    loop {
                        if let Some(y) = blur.push_ready() {
                            if y < row_r.y1 {
                                // should never fail
                                blur.push(unwrap!(jpeg_slice.row(y - row_r.y0)));
                            } else {
                                return true; // need more data
                            }
                        }

                        if let Some(y) = blur.pop_ready() {
                            blur.pop(unwrap!(slice.row_mut(0))); // should never fail
                            let dst_r = Rect::from_top_left_and_size(self.pos, jpeg_size)
                                .translate(Offset::new(0, y));
                            canvas.draw_bitmap(dst_r, slice.view());

                            if y + 1 >= clip.y1 {
                                return false; // we are done
                            }
                        }
                    }
                };

                unwrap!(
                    cache
                        .jpeg()
                        .decompress_row(self.jpeg, self.scale, y, draw_row),
                    "Invalid JPEG"
                );
            }
        }
    }
}

impl ShapeClone for JpegImage {
    fn clone_at_bump<'alloc, T>(self, bump: &'alloc T) -> Option<&'alloc mut dyn Shape>
    where
        T: LocalAllocLeakExt<'alloc>,
    {
        let clone = bump.alloc_t::<JpegImage>()?;
        Some(clone.uninit.init(JpegImage { ..self }))
    }
}
