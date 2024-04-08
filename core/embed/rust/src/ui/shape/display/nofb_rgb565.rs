use crate::trezorhal::{display, dma2d_new::Dma2d};

use crate::ui::{
    display::Color,
    geometry::{Offset, Rect},
};

use super::super::{
    BasicCanvas, BitmapFormat, BitmapView, DrawingCache, ProgressiveRenderer, Viewport,
};

use static_alloc::Bump;

const SHAPE_MEM_SIZE: usize = 5 * 1024;
const BUMP_A_SIZE: usize = DrawingCache::get_bump_a_size() + SHAPE_MEM_SIZE;
const BUMP_B_SIZE: usize = DrawingCache::get_bump_b_size();

pub fn render_on_display<'a, F>(clip: Option<Rect>, bg_color: Option<Color>, func: F)
where
    F: FnOnce(&mut ProgressiveRenderer<'_, 'a, Bump<[u8; BUMP_A_SIZE]>, DisplayCanvas>),
{
    #[cfg_attr(not(target_os = "macos"), link_section = ".no_dma_buffers")]
    static mut BUMP_A: Bump<[u8; BUMP_A_SIZE]> = Bump::uninit();

    #[cfg_attr(not(target_os = "macos"), link_section = ".buf")]
    static mut BUMP_B: Bump<[u8; BUMP_B_SIZE]> = Bump::uninit();

    let bump_a = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_A) };
    let bump_b = unsafe { &mut *core::ptr::addr_of_mut!(BUMP_B) };
    {
        bump_a.reset();
        bump_b.reset();

        let cache = DrawingCache::new(bump_a, bump_b);
        let mut canvas = DisplayCanvas::acquire().unwrap();

        if let Some(clip) = clip {
            canvas.set_viewport(Viewport::new(clip));
        }

        let mut target = ProgressiveRenderer::new(&mut canvas, bg_color, &cache, bump_a, 45);

        func(&mut target);

        target.render(16);

        display::refresh();
    }
}

pub struct DisplayCanvas {
    size: Offset,
    viewport: Viewport,
}

impl DisplayCanvas {
    pub fn acquire() -> Option<Self> {
        let size = Offset::new(240, 240); // TODO
        let viewport = Viewport::from_size(size);
        Some(Self { size, viewport })
    }
}

impl BasicCanvas for DisplayCanvas {
    fn viewport(&self) -> Viewport {
        self.viewport
    }

    fn set_viewport(&mut self, viewport: Viewport) {
        self.viewport = viewport.absolute_clip(self.bounds());
    }

    fn size(&self) -> Offset {
        self.size
    }

    fn fill_rect(&mut self, r: Rect, color: Color, _alpha: u8) {
        let r = r.translate(self.viewport.origin);
        if let Some(dma2d) = Dma2d::new_fill(r, self.viewport.clip, color, 255) {
            unsafe { dma2d.display_fill() };
        }
    }

    fn draw_bitmap(&mut self, r: Rect, bitmap: BitmapView) {
        let r = r.translate(self.viewport.origin);
        if let Some(dma2d) = Dma2d::new_copy(r, self.viewport.clip, &bitmap) {
            match bitmap.format() {
                BitmapFormat::RGB565 => unsafe { dma2d.display_copy_rgb565() },
                _ => panic!("Unsupported DMA operation"),
            }
            bitmap.bitmap.mark_dma_pending();
        }
    }
}
