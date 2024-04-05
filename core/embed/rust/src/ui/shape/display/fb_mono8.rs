use crate::ui::{
    display::Color,
    geometry::{Offset, Rect},
    shape::{BasicCanvas, DirectRenderer, DrawingCache, Mono8Canvas, Viewport},
};

use crate::trezorhal::display;

use static_alloc::Bump;

pub fn render_on_display<'a, F>(clip: Option<Rect>, bg_color: Option<Color>, func: F)
where
    F: FnOnce(&mut DirectRenderer<'_, 'a, Mono8Canvas<'a>>),
{
    const BUMP_SIZE: usize = DrawingCache::get_bump_a_size() + DrawingCache::get_bump_b_size();

    static mut BUMP: Bump<[u8; BUMP_SIZE]> = Bump::uninit();

    let bump = unsafe { &mut *core::ptr::addr_of_mut!(BUMP) };
    {
        let width = display::DISPLAY_RESX as i16;
        let height = display::DISPLAY_RESY as i16;

        bump.reset();

        let cache = DrawingCache::new(bump, bump);

        let (fb, fb_stride) = display::get_frame_buffer();

        let mut canvas = unwrap!(Mono8Canvas::new(
            Offset::new(width, height),
            Some(fb_stride),
            None,
            fb
        ));

        if let Some(clip) = clip {
            canvas.set_viewport(Viewport::new(clip));
        }

        let mut target = DirectRenderer::new(&mut canvas, bg_color, &cache);

        func(&mut target);

        display::refresh();
    }
}
