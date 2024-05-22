use crate::{
    error::Error,
    micropython::{ffi, obj::Obj, qstr::Qstr, simple_type::SimpleTypeObj, typ::Type, util},
};

/* CODER BEWARE
 * The following is an ugly hack to pull out the backlight theme from the
 * appropriate model. Going forward, we should not be adding more code like
 * this.
 *
 * Good news is, this whole module should be removed, in favor of fully
 * moving backlight control into Rust. Relatively easy to do, but not
 * necessary right now. Filed as https://github.com/trezor/trezor-firmware/issues/3849
 *
 * Consider this module temporary. (yeah yeah everyone knows "temporary"
 * things stay forever. Written in May 2024.)
 */
#[cfg(feature = "model_mercury")]
use super::model_mercury::theme::backlight;
#[cfg(all(not(feature = "model_mercury"), feature = "model_tt"))]
use super::model_tt::theme::backlight;
#[cfg(all(not(feature = "model_mercury"), not(feature = "model_tt")))]
mod backlight {
    pub fn get_backlight_none() -> u16 {
        0
    }
    pub fn get_backlight_normal() -> u16 {
        0
    }
    pub fn get_backlight_low() -> u16 {
        0
    }
    pub fn get_backlight_dim() -> u16 {
        0
    }
    pub fn get_backlight_max() -> u16 {
        0
    }
}

static BACKLIGHT_LEVELS_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_BacklightLevels,
    attr_fn: backlight_levels_attr,
};

unsafe extern "C" fn backlight_levels_attr(_self_in: Obj, attr: ffi::qstr, dest: *mut Obj) {
    let block = || {
        let arg = unsafe { dest.read() };
        if !arg.is_null() {
            // Null destination would mean a `setattr`.
            return Err(Error::TypeError);
        }
        let attr = Qstr::from_u16(attr as _);
        let value = match attr {
            Qstr::MP_QSTR_NONE => backlight::get_backlight_none(),
            Qstr::MP_QSTR_NORMAL => backlight::get_backlight_normal(),
            Qstr::MP_QSTR_LOW => backlight::get_backlight_low(),
            Qstr::MP_QSTR_DIM => backlight::get_backlight_dim(),
            Qstr::MP_QSTR_MAX => backlight::get_backlight_max(),
            _ => return Err(Error::AttributeError(attr)),
        };
        unsafe { dest.write(value.into()) };
        Ok(())
    };
    unsafe { util::try_or_raise(block) }
}

pub static BACKLIGHT_LEVELS_OBJ: SimpleTypeObj = SimpleTypeObj::new(&BACKLIGHT_LEVELS_TYPE);
