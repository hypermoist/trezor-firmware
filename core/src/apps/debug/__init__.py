if not __debug__:
    from trezor.utils import halt

    halt("debug mode inactive")

if __debug__:
    from storage import debug as storage
    from storage.debug import debug_events

    import trezorui2

    from trezor import log, loop, utils, wire
    from trezor.ui import display
    from trezor.enums import MessageType, DebugPhysicalButton
    from trezor.messages import (
        DebugLinkLayout,
        Success,
    )

    from apps import workflow_handlers

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from trezor.ui import Layout
        from trezor.messages import (
            DebugLinkDecision,
            DebugLinkEraseSdCard,
            DebugLinkGetState,
            DebugLinkRecordScreen,
            DebugLinkReseedRandom,
            DebugLinkState,
            DebugLinkWatchLayout,
        )

    reset_current_words = loop.chan()
    reset_word_index = loop.chan()

    confirm_chan = loop.chan()
    swipe_chan = loop.chan()
    input_chan = loop.chan()
    model_r_btn_chan = loop.chan()
    confirm_signal = confirm_chan.take
    swipe_signal = swipe_chan.take
    input_signal = input_chan.take
    model_r_btn_signal = model_r_btn_chan.take

    synthetic_event = loop.chan()
    synthetic_event_signal = synthetic_event.take

    debuglink_decision_chan = loop.chan()

    layout_change_chan = loop.chan()

    DEBUG_CONTEXT: wire.Context | None = None

    LAYOUT_WATCHER_NONE = 0
    LAYOUT_WATCHER_STATE = 1
    LAYOUT_WATCHER_LAYOUT = 2

    def screenshot() -> bool:
        if storage.save_screen:
            display.save(storage.save_screen_directory + "/refresh-")
            return True
        return False

    def notify_layout_change(layout: Layout, event_id: int | None = None) -> None:
        storage.current_content[:] = layout.read_content()
        if storage.watch_layout_changes or layout_change_chan.takers:
            payload = (event_id, storage.current_content)
            layout_change_chan.publish(payload)

    async def _dispatch_debuglink_decision(msg: DebugLinkDecision) -> None:
        from trezor.enums import DebugButton
        from trezor.ui import Result

        if msg.button is not None:
            if msg.button == DebugButton.NO:
                await confirm_chan.put(Result(trezorui2.CANCELLED))
            elif msg.button == DebugButton.YES:
                await confirm_chan.put(Result(trezorui2.CONFIRMED))
            elif msg.button == DebugButton.INFO:
                await confirm_chan.put(Result(trezorui2.INFO))
        if msg.physical_button is not None:
            await model_r_btn_chan.put(msg.physical_button)
        if msg.swipe is not None:
            await swipe_chan.put(msg.swipe)
        if msg.input is not None:
            await input_chan.put(Result(msg.input))

    async def debuglink_decision_dispatcher() -> None:
        while True:
            msg = await debuglink_decision_chan.take()
            await _dispatch_debuglink_decision(msg)

    async def return_layout_change() -> None:
        awaited_event_id = debug_events.awaited_event
        last_result_id = debug_events.last_result

        should_wait_first_paint = False
        if awaited_event_id is not None and awaited_event_id == last_result_id:
            content = storage.current_content[:]
        else:
            while True:
                event_id, content = await layout_change_chan.take()
                if storage.new_layout:
                    should_wait_first_paint = True
                    storage.new_layout = False
                if event_id is None or awaited_event_id is None:
                    break
                if event_id > awaited_event_id:
                    raise RuntimeError(
                        f"Waiting for event that already happened - {event_id} > {awaited_event_id}"
                    )
                elif event_id == awaited_event_id:
                    if should_wait_first_paint:
                        should_wait_first_paint = False
                        continue
                    storage.awaited_event_id_result = None
                    break

        if awaited_event_id is not None:
            debug_events.last_result = awaited_event_id

        assert DEBUG_CONTEXT is not None
        if storage.layout_watcher is LAYOUT_WATCHER_LAYOUT:
            await DEBUG_CONTEXT.write(DebugLinkLayout(lines=content))
        else:
            from trezor.messages import DebugLinkState

            await DEBUG_CONTEXT.write(DebugLinkState(layout_lines=content))
        storage.layout_watcher = LAYOUT_WATCHER_NONE

    async def touch_hold(x: int, y: int, duration_ms: int) -> None:
        from trezor import io

        await loop.sleep(duration_ms)
        synthetic_event.publish((io.TOUCH_END, x, y))

    async def button_hold(btn: int, duration_ms: int) -> None:
        from trezor import io

        await loop.sleep(duration_ms)
        synthetic_event.publish((io.BUTTON, (io.BUTTON_RELEASED, btn)))

    async def dispatch_DebugLinkWatchLayout(
        ctx: wire.Context, msg: DebugLinkWatchLayout
    ) -> Success:
        from trezor import ui

        # Modifying `watch_layout_changes` means we will probably
        # be sending debug events from the host and will want to
        # analyze the resulted layout.
        # Resetting the debug events makes sure that the previous
        # events/layouts are not mixed with the new ones.
        storage.reset_debug_events()

        layout_change_chan.putters.clear()
        if msg.watch:
            await ui.wait_until_layout_is_running()
        storage.watch_layout_changes = bool(msg.watch)
        log.debug(__name__, "Watch layout changes: %s", storage.watch_layout_changes)
        return Success()

    async def dispatch_DebugLinkDecision(
        ctx: wire.Context, msg: DebugLinkDecision
    ) -> None:
        from trezor import io, workflow

        workflow.idle_timer.touch()

        if debuglink_decision_chan.putters:
            log.warning(__name__, "DebugLinkDecision queue is not empty")

        x = msg.x  # local_cache_attribute
        y = msg.y  # local_cache_attribute

        # TT click on specific coordinates, with possible hold
        if x is not None and y is not None and utils.MODEL in ("T",):
            evt_down = (debug_events.last_event + 1, io.TOUCH_START), x, y
            evt_up = (debug_events.last_event + 2, io.TOUCH_END), x, y
            debug_events.last_event += 2
            synthetic_event.publish(evt_down)
            if msg.hold_ms is not None:
                loop.schedule(touch_hold(x, y, msg.hold_ms))
            else:
                synthetic_event.publish(evt_up)
        # TR hold of a specific button
        elif (
            msg.physical_button is not None
            and msg.hold_ms is not None
            and utils.MODEL in ("R",)
        ):
            if msg.physical_button == DebugPhysicalButton.LEFT_BTN:
                btn = io.BUTTON_LEFT
            elif msg.physical_button == DebugPhysicalButton.RIGHT_BTN:
                btn = io.BUTTON_RIGHT
            else:
                raise wire.ProcessError("Unknown physical button")
            synthetic_event.publish((io.BUTTON, (io.BUTTON_PRESSED, btn)))
            loop.schedule(button_hold(btn, msg.hold_ms))
        # Something more general
        else:
            debuglink_decision_chan.publish(msg)

        if msg.wait:
            # We wait for all the previously sent events
            debug_events.awaited_event = debug_events.last_event
            storage.layout_watcher = LAYOUT_WATCHER_LAYOUT
            loop.schedule(return_layout_change())

    async def dispatch_DebugLinkGetState(
        ctx: wire.Context, msg: DebugLinkGetState
    ) -> DebugLinkState | None:
        from trezor.messages import DebugLinkState
        from apps.common import mnemonic, passphrase

        m = DebugLinkState()
        m.mnemonic_secret = mnemonic.get_secret()
        m.mnemonic_type = mnemonic.get_type()
        m.passphrase_protection = passphrase.is_enabled()
        m.reset_entropy = storage.reset_internal_entropy

        if msg.wait_layout:
            if not storage.watch_layout_changes:
                raise wire.ProcessError("Layout is not watched")
            storage.layout_watcher = LAYOUT_WATCHER_STATE
            # We wait for the last previously sent event to finish
            debug_events.awaited_event = debug_events.last_event
            loop.schedule(return_layout_change())
            return None
        else:
            m.layout_lines = storage.current_content

        if msg.wait_word_pos:
            m.reset_word_pos = await reset_word_index.take()
        if msg.wait_word_list:
            m.reset_word = " ".join(await reset_current_words.take())
        return m

    async def dispatch_DebugLinkRecordScreen(
        ctx: wire.Context, msg: DebugLinkRecordScreen
    ) -> Success:
        if msg.target_directory:
            storage.save_screen_directory = msg.target_directory
            storage.save_screen = True
        else:
            storage.save_screen = False
            display.clear_save()  # clear C buffers

        return Success()

    async def dispatch_DebugLinkReseedRandom(
        ctx: wire.Context, msg: DebugLinkReseedRandom
    ) -> Success:
        if msg.value is not None:
            from trezor.crypto import random

            random.reseed(msg.value)
        return Success()

    async def dispatch_DebugLinkEraseSdCard(
        ctx: wire.Context, msg: DebugLinkEraseSdCard
    ) -> Success:
        from trezor import io

        sdcard = io.sdcard  # local_cache_attribute

        try:
            sdcard.power_on()
            if msg.format:
                io.fatfs.mkfs()
            else:
                # trash first 1 MB of data to destroy the FAT filesystem
                assert sdcard.capacity() >= 1024 * 1024
                empty_block = bytes([0xFF] * sdcard.BLOCK_SIZE)
                for i in range(1024 * 1024 // sdcard.BLOCK_SIZE):
                    sdcard.write(i, empty_block)

        except OSError:
            raise wire.ProcessError("SD card operation failed")
        finally:
            sdcard.power_off()
        return Success()

    def boot() -> None:
        register = workflow_handlers.register  # local_cache_attribute

        register(MessageType.DebugLinkDecision, dispatch_DebugLinkDecision)  # type: ignore [Argument of type "(ctx: Context, msg: DebugLinkDecision) -> Coroutine[Any, Any, None]" cannot be assigned to parameter "handler" of type "Handler[Msg@register]" in function "register"]
        register(MessageType.DebugLinkGetState, dispatch_DebugLinkGetState)  # type: ignore [Argument of type "(ctx: Context, msg: DebugLinkGetState) -> Coroutine[Any, Any, DebugLinkState | None]" cannot be assigned to parameter "handler" of type "Handler[Msg@register]" in function "register"]
        register(MessageType.DebugLinkReseedRandom, dispatch_DebugLinkReseedRandom)
        register(MessageType.DebugLinkRecordScreen, dispatch_DebugLinkRecordScreen)
        register(MessageType.DebugLinkEraseSdCard, dispatch_DebugLinkEraseSdCard)
        register(MessageType.DebugLinkWatchLayout, dispatch_DebugLinkWatchLayout)

        loop.schedule(debuglink_decision_dispatcher())
        if storage.layout_watcher is not LAYOUT_WATCHER_NONE:
            loop.schedule(return_layout_change())
