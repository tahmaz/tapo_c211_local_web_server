"""
Live video — /api/snapshot (poll) + /api/mjpeg
Keyfiyyət query ilə dəyişir; snapshot worker lazım gələndə restart olur.
"""
import subprocess
import threading
time_mod = __import__("time")

from flask import Blueprint, Response, request

bp = Blueprint("live_video", __name__)
_cfg = {}

_snap_lock = threading.Lock()
_snap_jpeg = None
_snap_ts = 0.0
_snap_proc = None
_snap_thread = None
_snap_stop = threading.Event()
_snap_key = None  # (stream, w, q, fps, transport)


def init(cfg: dict):
    global _cfg
    _cfg = cfg


def _rtsp_url(stream: str) -> str:
    return (
        f"rtsp://{_cfg['camera_user']}:{_cfg['camera_pass']}"
        f"@{_cfg['camera_ip']}:554/stream{stream}"
    )


def _stop_snap():
    global _snap_proc, _snap_thread, _snap_key
    _snap_stop.set()
    if _snap_proc is not None:
        try:
            _snap_proc.kill()
        except Exception:
            pass
        _snap_proc = None
    _snap_key = None
    time_mod.sleep(0.15)
    _snap_stop.clear()


def _start_snap_worker(stream: str, w: int, q: int, fps: int, transport: str):
    global _snap_proc, _snap_thread, _snap_key

    key = (stream, w, q, fps, transport)
    if _snap_thread is not None and _snap_thread.is_alive() and _snap_key == key:
        return
    if _snap_thread is not None and _snap_thread.is_alive():
        _stop_snap()

    _snap_key = key

    def worker():
        global _snap_proc, _snap_jpeg, _snap_ts
        vf = f"fps={fps}"
        if w > 0:
            vf = f"scale={w}:-2,{vf}"
        transports = [transport, "tcp"] if transport != "tcp" else ["tcp"]
        for tr in transports:
            if _snap_stop.is_set():
                return
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-fflags", "nobuffer+discardcorrupt",
                "-flags", "low_delay",
                "-probesize", "32", "-analyzeduration", "0",
                "-rtsp_transport", tr,
                "-i", _rtsp_url(stream),
                "-an", "-vf", vf, "-q:v", str(q),
                "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1",
            ]
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0
                )
            except Exception:
                continue
            _snap_proc = proc
            buf = b""
            try:
                while not _snap_stop.is_set():
                    chunk = proc.stdout.read(4096)
                    if not chunk:
                        break
                    buf += chunk
                    while True:
                        a = buf.find(b"\xff\xd8")
                        b = buf.find(b"\xff\xd9")
                        if a >= 0 and b > a:
                            frame = buf[a : b + 2]
                            buf = buf[b + 2 :]
                            with _snap_lock:
                                _snap_jpeg = frame
                                _snap_ts = time_mod.time()
                        else:
                            if a > 0:
                                buf = buf[a:]
                            elif len(buf) > 512_000:
                                buf = b""
                            break
            finally:
                try:
                    proc.kill()
                except Exception:
                    pass
            _snap_proc = None

    _snap_thread = threading.Thread(target=worker, daemon=True)
    _snap_thread.start()


def _params_from_request():
    stream = request.args.get("stream", _cfg.get("video_stream", "2"))
    if stream not in ("1", "2"):
        stream = "2"
    w = int(request.args.get("w", _cfg.get("video_width", 480)))
    q = int(request.args.get("q", _cfg.get("video_q", 12)))
    fps = int(request.args.get("fps", _cfg.get("video_fps", 10)))
    transport = request.args.get("t", _cfg.get("rtsp_transport", "udp"))
    w = max(0, min(1920, w))
    q = max(2, min(31, q))
    fps = max(5, min(25, fps))
    return stream, w, q, fps, transport


@bp.get("/api/snapshot")
def api_snapshot():
    stream, w, q, fps, transport = _params_from_request()
    _start_snap_worker(stream, w, q, fps, transport)
    deadline = time_mod.time() + 4.0
    while time_mod.time() < deadline:
        with _snap_lock:
            data = _snap_jpeg
            ts = _snap_ts
        if data and (time_mod.time() - ts) < 5.0:
            return Response(
                data,
                mimetype="image/jpeg",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "X-Snapshot-Age-Ms": str(int((time_mod.time() - ts) * 1000)),
                },
            )
        time_mod.sleep(0.04)
    return Response(b"", status=503, mimetype="text/plain")


@bp.get("/api/mjpeg")
def api_mjpeg():
    stream, w, q, fps, transport = _params_from_request()
    vf = f"fps={fps}"
    if w > 0:
        vf = f"scale={w}:-2,{vf}"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-fflags", "nobuffer+discardcorrupt",
        "-flags", "low_delay",
        "-probesize", "32", "-analyzeduration", "0",
        "-rtsp_transport", transport,
        "-i", _rtsp_url(stream),
        "-an", "-vf", vf, "-q:v", str(q),
        "-f", "mjpeg", "pipe:1",
    ]

    def gen():
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0
        )
        try:
            buf = b""
            last_send = 0.0
            min_interval = 1.0 / max(fps, 1)
            while True:
                chunk = proc.stdout.read(8192)
                if not chunk:
                    break
                buf += chunk
                frame = None
                while True:
                    a, b = buf.find(b"\xff\xd8"), buf.find(b"\xff\xd9")
                    if a >= 0 and b > a:
                        frame = buf[a : b + 2]
                        buf = buf[b + 2 :]
                    else:
                        if a > 0:
                            buf = buf[a:]
                        break
                if frame is None:
                    continue
                now = time_mod.time()
                if now - last_send < min_interval * 0.45:
                    continue
                last_send = now
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        finally:
            proc.kill()

    return Response(
        gen(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store", "X-Accel-Buffering": "no"},
    )
