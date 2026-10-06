"""Kamera mikrofonu → browser (RTSP audio → PCM s16le 8k → HTTP stream)"""
import subprocess
from flask import Blueprint, Response

bp = Blueprint("receive_voice", __name__)
_cfg = {}


def init(cfg: dict):
    global _cfg
    _cfg = cfg


@bp.get("/api/camera_audio")
def api_camera_audio():
    """
    Raw PCM s16le mono 8000 Hz — browser Web Audio ilə oxuyur.
    Content-Type: application/octet-stream
    """
    rtsp = (
        f"rtsp://{_cfg['camera_user']}:{_cfg['camera_pass']}"
        f"@{_cfg['camera_ip']}:554/stream1"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-rtsp_transport", "tcp", "-i", rtsp,
        "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1",
    ]

    def gen():
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            while True:
                chunk = proc.stdout.read(3200)  # 200ms @ 8k s16le
                if not chunk:
                    break
                yield chunk
        finally:
            proc.kill()

    return Response(
        gen(),
        mimetype="application/octet-stream",
        headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
    )
