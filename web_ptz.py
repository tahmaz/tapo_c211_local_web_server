"""
PTZ — ONVIF ContinuousMove (hold = move, release = stop)
"""
import threading

from flask import Blueprint, jsonify, request
from onvif import ONVIFCamera

bp = Blueprint("ptz", __name__)
_cfg = {}
_lock = threading.Lock()
_cam = None
_ptz = None
_token = None
_move_req = None
_stop_req = None
_current = None
_speed = 0.6


def init(cfg: dict):
    global _cfg, _speed
    _cfg = cfg
    _speed = float(cfg.get("ptz_speed", 0.6))


def _ensure():
    global _cam, _ptz, _token, _move_req, _stop_req
    if _ptz is not None:
        return
    host = _cfg["camera_ip"]
    port = int(_cfg.get("onvif_port", 2020))
    user = _cfg["camera_user"]
    password = _cfg.get("onvif_pass") or _cfg["camera_pass"]


    cam = ONVIFCamera(host, port, user, password)
    media = cam.create_media_service()
    profiles = media.GetProfiles()
    if not profiles:
        raise RuntimeError("ONVIF profile yoxdur")
    profile = profiles[0]
    token = profile.token
    ptz = cam.create_ptz_service()

    try:
        PTZSpeed = ptz.zeep_client.get_type(
            "{http://www.onvif.org/ver20/ptz/wsdl}PTZSpeed"
        )
    except Exception:
        PTZSpeed = ptz.zeep_client.get_type(
            "{http://www.onvif.org/ver10/schema}PTZSpeed"
        )
    Vector2D = ptz.zeep_client.get_type(
        "{http://www.onvif.org/ver10/schema}Vector2D"
    )

    move_req = ptz.create_type("ContinuousMove")
    move_req.ProfileToken = token
    move_req.Velocity = PTZSpeed(PanTilt=Vector2D(x=0.0, y=0.0))

    stop_req = ptz.create_type("Stop")
    stop_req.ProfileToken = token
    stop_req.PanTilt = True
    stop_req.Zoom = False

    try:
        ptz.Stop(stop_req)
    except Exception:
        pass

    _cam, _ptz, _token = cam, ptz, token
    _move_req, _stop_req = move_req, stop_req
    print(f"[ptz] ONVIF ready token={token} {host}:{port}")


def _do_move(x: float, y: float):
    _move_req.Velocity.PanTilt.x = x
    _move_req.Velocity.PanTilt.y = y
    _ptz.ContinuousMove(_move_req)


def _do_stop():
    global _current
    try:
        if _ptz is not None and _stop_req is not None:
            _ptz.Stop(_stop_req)
    except Exception as e:
        print("[ptz] stop error:", e)
    _current = None


def _dir_xy(direction: str, speed: float):
    d = direction.lower()
    if d in ("up", "w"):
        return "up", 0.0, speed
    if d in ("down", "s"):
        return "down", 0.0, -speed
    if d in ("left", "a"):
        return "left", -speed, 0.0
    if d in ("right", "d"):
        return "right", speed, 0.0
    return None


@bp.post("/api/ptz")
def api_ptz():
    """
    {"action":"start","dir":"left|right|up|down","speed":0.6}
    {"action":"stop"}
    """
    global _current, _speed
    data = request.get_json(force=True, silent=True) or {}
    action = (data.get("action") or "start").lower()
    direction = (data.get("dir") or "").lower()
    if data.get("speed") is not None:
        try:
            _speed = max(0.05, min(1.0, float(data["speed"])))
        except (TypeError, ValueError):
            pass

    with _lock:
        try:
            _ensure()
        except Exception as e:
            return jsonify(ok=False, error=str(e)), 500

        if action == "stop":
            _do_stop()
            return jsonify(ok=True, action="stop")

        parsed = _dir_xy(direction, _speed)
        if parsed is None:
            return jsonify(ok=False, error="dir: up/down/left/right"), 400
        name, x, y = parsed

        if _current != name:
            try:
                _do_move(x, y)
                _current = name
            except Exception as e:
                msg = str(e)
                if "MOTOR" in msg or "64304" in msg:
                    return jsonify(ok=True, limit=True, error=msg)
                return jsonify(ok=False, error=msg), 500

        return jsonify(ok=True, action="start", dir=name, speed=_speed, x=x, y=y)


@bp.get("/api/ptz/status")
def api_ptz_status():
    return jsonify(dir=_current, speed=_speed, connected=_ptz is not None)
