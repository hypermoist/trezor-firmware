from typing import TYPE_CHECKING

from trezor.enums import MessageType

if TYPE_CHECKING:
    from trezor.wire import Handler, Msg


def repeated_backup_enabled() -> bool:
    import storage.cache as storage_cache

    storage_cache.get_bool(storage_cache.APP_RECOVERY_REPEATED_BACKUP_UNLOCKED)


def enable_repeated_backup():
    import storage.cache as storage_cache

    storage_cache.set_bool(storage_cache.APP_RECOVERY_REPEATED_BACKUP_UNLOCKED, True)


def add_repeated_backup_filter():
    from trezor import wire

    wire.filters.append(_repeated_backup_filter)


def disable_repeated_backup():
    import storage.cache as storage_cache
    from trezor import wire

    storage_cache.delete(storage_cache.APP_RECOVERY_REPEATED_BACKUP_UNLOCKED)
    wire.remove_filter(_repeated_backup_filter)


_ALLOW_WHILE_REPEATED_BACKUP_UNLOCKED = (
    MessageType.Initialize,
    MessageType.GetFeatures,
    MessageType.EndSession,
    MessageType.BackupDevice,
    MessageType.WipeDevice,
    MessageType.Cancel,
)


def _repeated_backup_filter(msg_type: int, prev_handler: Handler[Msg]) -> Handler[Msg]:
    from trezor import wire

    if msg_type in _ALLOW_WHILE_REPEATED_BACKUP_UNLOCKED:
        return prev_handler
    else:
        raise wire.ProcessError("Operation not allowed when in repeated backup state")
