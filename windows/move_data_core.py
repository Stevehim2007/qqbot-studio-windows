"""Shared, Windows-specific data-directory migration helpers.

This module is intentionally free of launcher UI code so both the command-line
launcher and the token-protected console extension validate and persist paths in
exactly the same way. It remains a Windows-owned module and is not copied from
the Linux upstream.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from qqbot_studio.store import default_data_dir

DATA_LOCATION_POINTER_FILENAME = "data-location.json"
MOVE_RECORD_FILENAME = "windows-data-move.json"
MOVE_REQUEST_FILENAME = "windows-console-move-request.json"
MOVE_STATUS_FILENAME = "windows-console-move-status.json"


def _write_text_atomic(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(payload, encoding="utf-8")
    try:
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    _write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def data_location_pointer_path() -> Path:
    """Stable pointer outside the data directory, used after a data move."""

    base = (
        os.environ.get("LOCALAPPDATA", "").strip()
        or os.environ.get("APPDATA", "").strip()
        or str(Path.home())
    )
    return Path(base) / "QQBotStudio" / DATA_LOCATION_POINTER_FILENAME


def _read_data_location_pointer(pointer_path: Path | None = None) -> Path | None:
    path = pointer_path or data_location_pointer_path()
    if not path.is_file():
        return None
    payload = _read_json(path)
    if not isinstance(payload, dict) or not str(payload.get("data_dir") or "").strip():
        raise ValueError(
            f"Data location pointer is invalid: {path}. Repair it or pass --data-dir explicitly."
        )
    target = Path(str(payload["data_dir"])).expanduser().resolve()
    if not target.is_dir():
        raise ValueError(
            f"Data location pointer points to a missing directory: {target}. "
            "Restore the directory or pass --data-dir explicitly."
        )
    return target


def _write_data_location_pointer(target: Path, pointer_path: Path | None = None) -> Path:
    path = pointer_path or data_location_pointer_path()
    _write_json_atomic(
        path,
        {
            "schema_version": 1,
            "data_dir": str(target.resolve()),
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return path


def resolve_data_dir(value: str | None, *, pointer_path: Path | None = None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    env_value = os.environ.get("QQBOT_STUDIO_DATA_DIR", "").strip()
    if env_value:
        return Path(env_value).expanduser().resolve()
    pointed = _read_data_location_pointer(pointer_path)
    if pointed is not None:
        return pointed
    return default_data_dir().resolve()


def _is_path_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _lower_path_parts(value: str) -> list[str]:
    return [part for part in re.split(r"[\\/]+", value.lower()) if part]


def _windows_drive_type(path: Path) -> int:
    """Return the Win32 drive type for a path, or 1 when unavailable."""

    if os.name != "nt":
        return 3
    try:
        import ctypes

        drive = str(path.drive)
        if not drive:
            return 1
        root = drive + "\\"
        return int(ctypes.windll.kernel32.GetDriveTypeW(root))
    except Exception:
        return 1


def validate_move_target(
    source: Path,
    target: Path,
    *,
    drive_type_func: Callable[[Path], int] | None = None,
) -> Path:
    """Validate a destination for the safe data-directory migration."""

    raw_source = str(source)
    raw_target = str(target)
    lower_target = raw_target.lower().replace("/", "\\")
    parts = _lower_path_parts(lower_target)

    # Reject forbidden path kinds before resolve(): resolving a nonexistent UNC
    # path on Windows raises FileNotFoundError before we can emit a clear error.
    if (
        lower_target.startswith("\\\\wsl$")
        or lower_target.startswith("\\\\wsl.localhost")
        or "\\wsl$\\" in lower_target
        or "\\wsl.localhost\\" in lower_target
        or any(part in {"wsl$", "wsl.localhost"} for part in parts)
    ):
        raise ValueError("Data directory cannot be placed in the Docker Desktop/WSL filesystem.")

    if lower_target.startswith("\\\\") or lower_target.startswith("//"):
        raise ValueError("Data directory cannot be a UNC/network share.")

    if any(
        part == "onedrive"
        or part.startswith("onedrive ")
        or part.startswith("onedrive-")
        for part in parts
    ):
        raise ValueError("Data directory cannot be inside OneDrive; use a local fixed NTFS directory.")

    source = Path(raw_source).expanduser().resolve()
    target = Path(raw_target).expanduser().resolve()

    for env_name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        root_value = os.environ.get(env_name, "").strip()
        if root_value:
            try:
                root = Path(root_value).expanduser().resolve()
            except OSError:
                continue
            if _is_path_within(target, root):
                raise ValueError(
                    "Data directory cannot be inside OneDrive; choose a local non-synced directory."
                )

    if os.name == "nt":
        if not target.drive:
            raise ValueError("Data directory must be an absolute path on a local fixed drive.")
        drive_type = (drive_type_func or _windows_drive_type)(target)
        # 3 = DRIVE_FIXED. Reject remote/removable/unknown drives for migration.
        if drive_type != 3:
            raise ValueError(
                "Data directory must be on a local fixed NTFS drive "
                "(network, removable, CD-ROM, RAM and unknown drives are rejected)."
            )

    if target.parent == target:
        raise ValueError("A filesystem/drive root cannot be used as the data directory.")
    if target == source:
        raise ValueError("New data directory must differ from the current data directory.")
    if _is_path_within(target, source) or _is_path_within(source, target):
        raise ValueError("New data directory cannot contain the old data directory or be nested inside it.")

    if target.exists():
        if not target.is_dir():
            raise ValueError(f"New data path exists but is not a directory: {target}")
        try:
            if any(target.iterdir()):
                raise ValueError(
                    f"New data directory must be empty or absent; refusing to merge into: {target}"
                )
        except OSError as exc:
            raise ValueError(f"Cannot inspect new data directory {target}: {exc}") from exc

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        probe = target.parent / f".qqbot-move-write-test-{os.getpid()}"
        probe.write_text("QQ Bot Studio data-directory write probe\n", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        raise ValueError(f"New data directory is not writable: {target}: {exc}") from exc

    return target
