#!/usr/bin/env python3
"""Native Windows single-instance POC launcher for AstrBot + SnowLuma + NTQQ.

This is NOT the bootstrap placeholder anymore: it owns real local process
start/stop/PID/log/port/health/config lifecycle. It does not install or
authenticate third-party components; when NTQQ/AstrBot/SnowLuma are missing,
commands report explicit blockers rather than pretending an E2E run succeeded.
No Docker, WSL or noVNC is used.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import webbrowser
from pathlib import Path

NATIVE_LAUNCHER_VERSION = "0.7.1"
SNOWLUMA_WINDOWS_DOCS = "https://snowluma.github.io/zh/docs/guide/deploy/windows"
SNOWLUMA_RELEASES = "https://github.com/SnowLuma/SnowLuma/releases"
ASTRBOT_WINDOWS_DOCS = "https://docs.astrbot.app/deploy/astrbot/package.html"
NOVNC_REPO = "https://github.com/novnc/noVNC"
WEBSOCKIFY_REPO = "https://github.com/novnc/websockify"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windows import native_runtime  # noqa: E402


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def _read_bundle_text(name: str) -> str:
    try:
        return (_bundle_root() / name).read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def _bundled_core_version() -> str:
    upstream = _read_bundle_text("UPSTREAM.md")
    for line in upstream.splitlines():
        if line.startswith("- Bundled core version:"):
            part = line.rsplit("==", 1)[-1].strip().strip("`")
            if part:
                return part
    return "unknown"


def _print_guide() -> None:
    print("QQ Bot Studio Windows - Native Edition POC")
    print("==========================================")
    print("Native single-instance POC: AstrBot + SnowLuma + local NTQQ.")
    print("No Docker, WSL, Linux VM or noVNC is used. QQ login/device checks")
    print("must be completed manually in the official local NTQQ window.")
    print("")
    print("Required native components (not bundled):")
    print("  1. Official Windows desktop QQ/NTQQ, signed in on this Windows user.")
    print("  2. AstrBot Windows deployment with Python 3.12+ / astrbot CLI.")
    print("  3. Official SnowLuma Windows x64 package, extracted locally.")
    print("")
    print("Typical commands (after configuring paths):")
    print("  QQBotStudioWindowsNative.exe --configure --non-interactive ^")
    print("    --ntqq-path \"C:\\Program Files\\Tencent\\QQ.exe\" ^")
    print("    --astrbot-command \"astrbot run\" --snowluma-dir \"D:\\SnowLuma\"")
    print("  QQBotStudioWindowsNative.exe --check --strict-check")
    print("  QQBotStudioWindowsNative.exe --write-onebot-config")
    print("  QQBotStudioWindowsNative.exe --start")
    print("  QQBotStudioWindowsNative.exe --status")
    print("  QQBotStudioWindowsNative.exe --health")
    print("  QQBotStudioWindowsNative.exe --logs --log-service all --lines 100")
    print("  QQBotStudioWindowsNative.exe --open-qq")
    print("  QQBotStudioWindowsNative.exe --stop")
    print("")
    print("OneBot is fixed to loopback by default: ws://127.0.0.1:<onebot-port>/ws")
    print("SnowLuma's global config/onebot.json is written with statusCommand #sl disabled.")
    print("")
    print("Official links:")
    print(f"  SnowLuma Windows guide : {SNOWLUMA_WINDOWS_DOCS}")
    print(f"  SnowLuma releases      : {SNOWLUMA_RELEASES}")
    print(f"  AstrBot Windows docs   : {ASTRBOT_WINDOWS_DOCS}")
    print("")
    print("noVNC is NOT part of this native POC. Optional noVNC would require")
    print("an external Windows VNC Server + websockify and whole-desktop sharing;")
    print(f"it is not per-instance and is not installed automatically: {NOVNC_REPO}")
    print("The Docker Desktop + WSL2 edition remains the simpler stable edition.")


def _print_checks(checks: list[dict[str, object]]) -> None:
    for item in checks:
        marker = "OK" if item.get("ok") else ("BLOCKED" if item.get("blocking") else "WARN")
        print(f"[{marker}] {item.get('name')}: {item.get('detail', '')}")


def _configure(root: Path, args: argparse.Namespace) -> dict:
    cfg = native_runtime.load_config(root)
    if args.ntqq_path is not None:
        cfg["ntqq_path"] = str(Path(args.ntqq_path).expanduser().resolve()) if args.ntqq_path else ""
    if args.astrbot_command is not None:
        cfg["astrbot_command"] = native_runtime.parse_command(args.astrbot_command)
    elif not cfg.get("astrbot_command"):
        cfg["astrbot_command"] = native_runtime.find_astrbot_command()
    if args.astrbot_root:
        cfg["astrbot_root"] = str(Path(args.astrbot_root).expanduser().resolve())
    if args.snowluma_dir:
        cfg["snowluma_dir"] = str(Path(args.snowluma_dir).expanduser().resolve())
    if args.snowluma_command is not None:
        cfg["snowluma_command"] = native_runtime.parse_command(args.snowluma_command)
    if args.bind_host:
        if str(args.bind_host).strip() not in {"127.0.0.1", "localhost", "::1"}:
            raise native_runtime.NativePOCError(
                "Native POC defaults to loopback and refuses non-loopback bind_host; "
                "use a VPN/reverse proxy for remote access."
            )
        cfg["bind_host"] = "127.0.0.1"
    for field, value in (
        ("astrbot_webui_port", args.astrbot_webui_port),
        ("astrbot_onebot_port", args.astrbot_onebot_port),
        ("snowluma_webui_port", args.snowluma_webui_port),
    ):
        if value is not None:
            if not (1 <= int(value) <= 65535):
                raise native_runtime.NativePOCError(f"{field} must be between 1 and 65535")
            cfg[field] = int(value)
    ports = {
        int(cfg.get("astrbot_webui_port") or 6185),
        int(cfg.get("astrbot_onebot_port") or 6199),
        int(cfg.get("snowluma_webui_port") or 5099),
    }
    if len(ports) != 3:
        raise native_runtime.NativePOCError("AstrBot WebUI/OneBot and SnowLuma WebUI ports must be distinct")
    cfg["onebot_url"] = (
        f"ws://127.0.0.1:{int(cfg.get('astrbot_onebot_port') or 6199)}/ws"
    )
    cfg["ntqq_path"] = str(cfg.get("ntqq_path") or native_runtime.find_ntqq_path())
    cfg["snowluma_dir"] = str(Path(str(cfg.get("snowluma_dir") or (root / "snowluma"))).expanduser().resolve())
    if not cfg.get("snowluma_command"):
        detected = native_runtime.find_snowluma_launcher(cfg["snowluma_dir"])
        if detected:
            cfg["snowluma_command"] = detected
    if not cfg.get("onebot_token"):
        import secrets

        cfg["onebot_token"] = secrets.token_urlsafe(24)
    path = native_runtime.save_config(root, cfg)
    print(f"Configuration saved: {path}")
    print(f"Native data root   : {root}")
    print(f"OneBot             : {cfg['onebot_url']}")
    print(f"NTQQ               : {cfg.get('ntqq_path') or 'BLOCKED: not found'}")
    print(f"AstrBot command    : {' '.join(cfg.get('astrbot_command') or []) or 'BLOCKED: not found'}")
    print(f"SnowLuma directory : {cfg.get('snowluma_dir')}")
    print(f"SnowLuma command   : {' '.join(cfg.get('snowluma_command') or []) or 'BLOCKED: not found'}")
    return cfg


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="QQBotStudioWindowsNative",
        description=(
            "Native single-instance Windows POC process manager for AstrBot + "
            "SnowLuma + local NTQQ. Does not install/authenticate third-party "
            "components; missing dependencies are explicit blockers."
        ),
    )
    parser.add_argument("--version", action="version", version=f"QQ Bot Studio Windows Native POC {NATIVE_LAUNCHER_VERSION} (bundled core {_bundled_core_version()})")
    parser.add_argument("--data-dir", default=None, help="Native data root (default: %%LOCALAPPDATA%%\\QQBotStudio\\data\\native).")
    parser.add_argument("--configure", action="store_true", help="Configure paths/ports and save native.json.")
    parser.add_argument("--non-interactive", action="store_true", help="Do not prompt during configuration.")
    parser.add_argument("--astrbot-command", default=None, help="Quoted AstrBot CLI command, e.g. \"astrbot run\".")
    parser.add_argument("--astrbot-root", default=None, help="AstrBot ASTRBOT_ROOT directory.")
    parser.add_argument("--snowluma-dir", default=None, help="Extracted official SnowLuma Windows directory.")
    parser.add_argument("--snowluma-command", default=None, help="Optional SnowLuma launcher command override.")
    parser.add_argument("--ntqq-path", default=None, help="Official QQ.exe path override.")
    parser.add_argument("--bind-host", default=None, help="Only loopback is accepted by Native POC.")
    parser.add_argument("--astrbot-webui-port", type=int, default=None)
    parser.add_argument("--astrbot-onebot-port", type=int, default=None)
    parser.add_argument("--snowluma-webui-port", type=int, default=None)
    parser.add_argument("--write-onebot-config", action="store_true", help="Write SnowLuma config/onebot.json for loopback AstrBot.")
    parser.add_argument("--force-onebot-config", action="store_true", help="Overwrite SnowLuma onebot.json instead of merging.")
    parser.add_argument("--start", action="store_true", help="Start AstrBot and SnowLuma native processes.")
    parser.add_argument("--stop", action="store_true", help="Stop managed native processes.")
    parser.add_argument("--restart", action="store_true", help="Stop then start managed native processes.")
    parser.add_argument("--status", action="store_true", help="Show native config/process/PID/log/port/health status.")
    parser.add_argument("--health", action="store_true", help="Probe AstrBot/SnowLuma local web UIs and OneBot port.")
    parser.add_argument("--logs", action="store_true", help="Print managed service log tails.")
    parser.add_argument("--log-service", choices=("all", "both", "astrbot", "snowluma"), default="all")
    parser.add_argument("--lines", type=int, default=80)
    parser.add_argument("--check", action="store_true", help="Print environment/prerequisite diagnostics.")
    parser.add_argument("--strict-check", action="store_true", help="Exit nonzero when blocking prerequisites are missing.")
    parser.add_argument("--open-qq", action="store_true", help="Open the official local NTQQ window (no login automation).")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON for status/health/check.")
    parser.add_argument("--guide", action="store_true", help="Print the native POC setup guide.")
    parser.add_argument("--open-snowluma", action="store_true")
    parser.add_argument("--open-snowluma-release", action="store_true")
    parser.add_argument("--open-astrbot", action="store_true")
    return parser


def _open(url: str) -> None:
    print(f"Opening: {url}")
    try:
        webbrowser.open_new_tab(url)
    except Exception as exc:
        print(f"ERROR: Could not open browser: {exc}", file=sys.stderr)


def run(argv: list[str] | None = None) -> int:
    # Windows legacy consoles may use a code page that cannot encode emoji
    # present in AstrBot/SnowLuma logs. Never crash while tailing logs.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, OSError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    root = native_runtime.native_root(args.data_dir)
    open_requested = False
    if args.open_snowluma:
        _open(SNOWLUMA_WINDOWS_DOCS)
        open_requested = True
    if args.open_snowluma_release:
        _open(SNOWLUMA_RELEASES)
        open_requested = True
    if args.open_astrbot:
        _open(ASTRBOT_WINDOWS_DOCS)
        open_requested = True
    if open_requested and not any(
        (args.configure, args.start, args.stop, args.restart, args.status,
         args.health, args.logs, args.check, args.write_onebot_config, args.open_qq)
    ):
        return 0
    try:
        if args.configure:
            _configure(root, args)
            return 0
        cfg = native_runtime.load_config(root)
        if args.write_onebot_config:
            result = native_runtime.write_snowluma_onebot_config(
                root, cfg, force=bool(args.force_onebot_config)
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.start:
            print(f"Native data root: {root}")
            result = native_runtime.start_native(root, cfg)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print("")
            print("Next: open the official local NTQQ window and complete QQ scan/verification there.")
            print("NoVNC was NOT started. Use --open-qq, then --status/--health.")
            return 0
        if args.stop:
            result = native_runtime.stop_native(root)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.restart:
            native_runtime.stop_native(root)
            result = native_runtime.start_native(root, cfg)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.status:
            payload = native_runtime.status_payload(root, cfg)
            print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else _format_status(payload))
            return 0
        if args.health:
            payload = native_runtime.health_payload(root, cfg)
            print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else _format_health(payload))
            return 0 if payload.get("ok") else 1
        if args.logs:
            logs = native_runtime.native_logs(root, args.log_service, args.lines)
            for service, text in logs.items():
                print(f"=== {service} log ===")
                print(text if text else "(empty or missing)")
            return 0
        if args.check or args.strict_check:
            checks = native_runtime.check_prerequisites(root, cfg)
            if args.json:
                print(json.dumps({"root": str(root), "checks": checks, "blockers": native_runtime.blockers(checks)}, ensure_ascii=False, indent=2))
            else:
                print(f"Native data root: {root}")
                _print_checks(checks)
                print("")
                missing = native_runtime.blockers(checks)
                print("NATIVE_PREREQ_CHECK=COMPLETE")
                print("NATIVE_E2E=NOT_VERIFIED")
                if missing:
                    print("NATIVE_START=BLOCKED")
                    for item in missing:
                        print(f"  - {item}")
                else:
                    print("NATIVE_START=READY_FOR_MANUAL_POC")
                    print("NATIVE_QQ_LOGIN=USE_OFFICIAL_LOCAL_NTQQ_WINDOW_ONLY")
            return 1 if args.strict_check and native_runtime.blockers(checks) else 0
        if args.open_qq:
            path = native_runtime.open_qq_window(cfg)
            print(f"Opened official NTQQ: {path}")
            print("Complete QR/device/SMS/slider verification manually in that window.")
            return 0
        _print_guide()
        return 0
    except native_runtime.NativeBlocked as exc:
        print("NATIVE_START=BLOCKED")
        for blocker in exc.blockers:
            print(f"  - {blocker}")
        print("Install/configure the missing official components, then retry. No E2E claim is made.")
        return 2
    except (native_runtime.NativePOCError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _format_status(payload: dict) -> str:
    lines = [
        f"Native mode : {payload.get('mode')}",
        f"Data root   : {payload.get('data_root')}",
        f"Bind host   : {payload.get('bind_host')}",
        f"OneBot URL  : {(payload.get('onebot') or {}).get('url')}",
        f"NTQQ        : {(payload.get('qq') or {}).get('path') or 'NOT FOUND'}",
        f"QQ login    : {(payload.get('qq') or {}).get('login')}",
        "Services:",
    ]
    for service, info in (payload.get("services") or {}).items():
        lines.append(
            f"  {service}: running={info.get('running')} pid={info.get('pid')} "
            f"log={info.get('log_path')}"
        )
    health = payload.get("health") or {}
    lines.append(f"Health ok   : {health.get('ok')}")
    for service in ("astrbot", "snowluma"):
        item = health.get(service) or {}
        lines.append(
            f"  {service}: alive={item.get('alive')} http={(item.get('http') or {}).get('detail')}"
        )
    onebot = health.get("onebot") or {}
    lines.append(f"OneBot port : {onebot.get('port')} listening={onebot.get('listening')}")
    lines.append("noVNC used  : False")
    return "\n".join(lines)


def _format_health(payload: dict) -> str:
    lines = [f"NATIVE_HEALTH_OK={payload.get('ok')}"]
    for service in ("astrbot", "snowluma"):
        item = payload.get(service) or {}
        lines.append(
            f"NATIVE_{service.upper()}_ALIVE={item.get('alive')} "
            f"HTTP={(item.get('http') or {}).get('status')} "
            f"DETAIL={(item.get('http') or {}).get('detail')}"
        )
    onebot = payload.get("onebot") or {}
    lines.append(f"NATIVE_ONEBOT_PORT={onebot.get('port')} LISTENING={onebot.get('listening')} URL={onebot.get('url')}")
    lines.append(f"NATIVE_NO_VNC_USED={payload.get('no_vnc_used')}")
    return "\n".join(lines)


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
