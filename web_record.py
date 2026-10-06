"""Kamera mikrofonundan qeyd → voices/"""
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify

bp = Blueprint("record", __name__)
_cfg = {}
_lock = threading.Lock()
_proc = None
_path = None
_recording = False


def init(cfg: dict):
    global _cfg
    _cfg = cfg


def _voices_dir() -> Path:
    return Path(_cfg["voices_dir"])


@bp.get("/api/record/status")
def api_record_status():
    return jsonify(recording=_recording, file=_path.name if _path else None)


@bp.post("/api/record/toggle")
def api_record_toggle():
    global _proc, _path, _recording
    with _lock:
        if _recording:
            return _stop_locked()
        return _start_locked()


@bp.post("/api/record/start")
def api_record_start():
    with _lock:
        if _recording:
            return jsonify(ok=True, already=True, file=_path.name if _path else None)
        return _start_locked()


@bp.post("/api/record/stop")
def api_record_stop():
    with _lock:
        if not _recording:
            return jsonify(ok=True, already=True)
        return _stop_locked()


def _start_locked():
    global _proc, _path, _recording
    d = _voices_dir()
    d.mkdir(parents=True, exist_ok=True)
    name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".wav"
    _path = d / name
    rtsp = (
        f"rtsp://{_cfg['camera_user']}:{_cfg['camera_pass']}"
        f"@{_cfg['camera_ip']}:554/stream1"
    )
    # kamera audio → wav (pcm_s16le 8k mono, brauzer/ffmpeg uyğun)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-rtsp_transport",
        "tcp",
        "-i",
        rtsp,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "8000",
        "-c:a",
        "pcm_s16le",
        "-f",
        "wav",
        str(_path),
    ]
    _proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _recording = True
    return jsonify(ok=True, recording=True, file=name)


def _stop_locked():
    global _proc, _path, _recording
    name = _path.name if _path else None
    if _proc is not None:
        try:
            _proc.terminate()
            try:
                _proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _proc.kill()
                _proc.wait(timeout=2)
        except Exception:
            pass
        _proc = None
    _recording = False
    # boş/çox kiçik faylı sil
    if _path and _path.is_file() and _path.stat().st_size < 1000:
        try:
            _path.unlink()
            name = None
        except OSError:
            pass
    _path = None
    return jsonify(ok=True, recording=False, file=name)
