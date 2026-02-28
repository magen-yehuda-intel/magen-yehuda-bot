#!/usr/bin/env python3
"""
dispatch.py — Multi-output alert dispatcher for MagenYehudaBot

Routes alerts to multiple Telegram channels based on configurable rules.
Each output channel can filter by: language, content types, severity, and image policy.

Usage (from bash):
    echo '{"type":"siren","severity":"CRITICAL","text_he":"...","text_en":"..."}' | python3 dispatch.py config.json

Usage (as Python module):
    from dispatch import Dispatcher
    d = Dispatcher("config.json")
    d.emit("siren", "CRITICAL", text_he="...", text_en="...")

Config shape (config.json):
    {
      "telegram_bot_token": "...",
      "telegram_chat_id": "@main_channel",     # backward compat (auto-generates default output)
      "outputs": [                               # optional — overrides telegram_chat_id if present
        {
          "id": "main",
          "chat_id": "@main_channel",
          "language": "both",                    # "he" | "en" | "both"
          "content": ["all"],                    # or specific: ["siren","osint","fires",...]
          "min_severity": "LOW",                 # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
          "images": "all"                        # "all" | "high_only" | "critical_only" | "none"
        }
      ]
    }

Event types:
    siren, siren_standdown, siren_clear, threat_change,
    osint, fires, seismic, strike_correlation,
    blackout, military_flights, polymarket,
    map, summary_he, summary_en, timelapse, pinned_status

Severity levels (ascending):
    LOW, MEDIUM, HIGH, CRITICAL

Image importance (set by caller):
    low, medium, high, critical
"""

import json
import sys
import os
import io
import uuid
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

# ─── Severity ranking ───

SEVERITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
IMAGE_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}

ALL_EVENT_TYPES = {
    "siren", "siren_standdown", "siren_clear", "threat_change",
    "osint", "fires", "seismic", "strike_correlation",
    "blackout", "military_flights", "polymarket",
    "map", "summary_he", "summary_en", "timelapse", "pinned_status",
}


def severity_rank(level: str) -> int:
    return SEVERITY_RANK.get(level.upper(), 0)


def image_rank(importance: str) -> int:
    return IMAGE_RANK.get(importance.lower(), 0)


# ─── Telegram delivery ───

def send_telegram_text(bot_token: str, chat_id: str, text: str) -> bool:
    """Send an HTML text message to Telegram."""
    if not text or not text.strip():
        return False
    try:
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=data,
        )
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        return result.get("ok", False)
    except Exception as e:
        print(f"  ⚠️  Telegram text send failed ({chat_id}): {e}", file=sys.stderr)
        return False


def send_telegram_photo(bot_token: str, chat_id: str, photo_path: str, caption: str = "") -> bool:
    """Send a photo to Telegram via multipart upload."""
    if not os.path.isfile(photo_path):
        return False
    try:
        with open(photo_path, "rb") as f:
            img_data = f.read()

        boundary = uuid.uuid4().hex
        body = io.BytesIO()
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode())
        if caption:
            body.write(f"--{boundary}\r\n".encode())
            body.write(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode())
        body.write(f"--{boundary}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="photo"; filename="image.png"\r\n')
        body.write(b"Content-Type: image/png\r\n\r\n")
        body.write(img_data)
        body.write(b"\r\n")
        body.write(f"--{boundary}--\r\n".encode())

        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendPhoto",
            data=body.getvalue(),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        return result.get("ok", False)
    except Exception as e:
        print(f"  ⚠️  Telegram photo send failed ({chat_id}): {e}", file=sys.stderr)
        return False


def send_telegram_animation(bot_token: str, chat_id: str, gif_path: str, caption: str = "") -> bool:
    """Send a GIF animation to Telegram."""
    if not os.path.isfile(gif_path):
        return False
    try:
        with open(gif_path, "rb") as f:
            gif_data = f.read()

        boundary = uuid.uuid4().hex
        body = io.BytesIO()
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode())
        if caption:
            body.write(f"--{boundary}\r\n".encode())
            body.write(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode())
        body.write(f"--{boundary}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="animation"; filename="animation.gif"\r\n')
        body.write(b"Content-Type: image/gif\r\n\r\n")
        body.write(gif_data)
        body.write(b"\r\n")
        body.write(f"--{boundary}--\r\n".encode())

        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendAnimation",
            data=body.getvalue(),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        return result.get("ok", False)
    except Exception as e:
        print(f"  ⚠️  Telegram animation send failed ({chat_id}): {e}", file=sys.stderr)
        return False


def edit_telegram_message(bot_token: str, chat_id: str, message_id: int, text: str) -> bool:
    """Edit an existing Telegram message."""
    try:
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/editMessageText",
            data=data,
        )
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        return result.get("ok", False)
    except Exception as e:
        print(f"  ⚠️  Telegram edit failed ({chat_id}): {e}", file=sys.stderr)
        return False


def pin_telegram_message(bot_token: str, chat_id: str, message_id: int) -> bool:
    """Pin a message in a Telegram channel."""
    try:
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "message_id": message_id,
            "disable_notification": "true",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/pinChatMessage",
            data=data,
        )
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        return result.get("ok", False)
    except Exception:
        return False


# ─── Output filtering ───

def should_send(output: dict, event_type: str, severity: str) -> bool:
    """Check if an event should be sent to this output based on filters."""
    # Content filter
    content_filter = output.get("content", ["all"])
    if "all" not in content_filter and event_type not in content_filter:
        return False

    # Severity filter
    min_sev = output.get("min_severity", "LOW")
    if severity_rank(severity) < severity_rank(min_sev):
        return False

    return True


def should_include_image(output: dict, image_importance: str, severity: str) -> bool:
    """Decide whether to include an image for this output."""
    policy = output.get("images", "all")

    if policy == "none":
        return False
    if policy == "all":
        return True
    if policy == "critical_only":
        return severity.upper() == "CRITICAL" or image_importance.lower() == "critical"
    if policy == "high_only":
        return (severity_rank(severity) >= severity_rank("HIGH")
                or image_rank(image_importance) >= image_rank("high"))

    return True  # default: include


def pick_text(output: dict, text_he: str, text_en: str) -> str:
    """Select the appropriate language text for an output."""
    lang = output.get("language", "both")

    if lang == "he":
        return text_he or text_en or ""
    if lang == "en":
        return text_en or text_he or ""

    # "both" — return both if available, separated
    if text_he and text_en and text_he != text_en:
        return text_he  # For "both", we send as separate messages (caller handles)
    return text_he or text_en or ""


# ─── Dispatcher class ───

class Dispatcher:
    """Routes alerts to configured Telegram output channels."""

    def __init__(self, config_path: str):
        self.config_path = os.path.abspath(config_path)
        with open(config_path) as f:
            self.config = json.load(f)

        self.bot_token = self.config["telegram_bot_token"]
        self.outputs = self._load_outputs()

    def _load_outputs(self) -> list:
        """Load outputs from config, with backward-compatible fallback."""
        if "outputs" in self.config and self.config["outputs"]:
            return self.config["outputs"]

        # Backward compat: single telegram_chat_id → default output
        chat_id = self.config.get("telegram_chat_id", "")
        if not chat_id:
            return []

        return [{
            "id": "default",
            "chat_id": chat_id,
            "language": "both",
            "content": ["all"],
            "min_severity": "LOW",
            "images": "all",
        }]

    def emit(self, event_type: str, severity: str = "LOW",
             text_he: str = "", text_en: str = "",
             image_path: str = None, image_importance: str = "low",
             image_caption: str = "", image_caption_he: str = "",
             gif_path: str = None, gif_caption: str = ""):
        """
        Dispatch an alert to all matching outputs.

        Args:
            event_type: Type of event (siren, osint, fires, etc.)
            severity: Alert severity (LOW, MEDIUM, HIGH, CRITICAL)
            text_he: Hebrew text (HTML formatted)
            text_en: English text (HTML formatted)
            image_path: Optional path to image file (map, etc.)
            image_importance: How important the image is (low/medium/high/critical)
            image_caption: Caption for the image (English)
            image_caption_he: Caption for the image (Hebrew)
            gif_path: Optional path to GIF animation
            gif_caption: Caption for the GIF
        """
        results = {}

        for output in self.outputs:
            out_id = output.get("id", output.get("chat_id", "?"))
            chat_id = output.get("chat_id", "")

            if not chat_id:
                continue

            if not should_send(output, event_type, severity):
                results[out_id] = "filtered"
                continue

            lang = output.get("language", "both")
            include_image = image_path and should_include_image(output, image_importance, severity)
            include_gif = gif_path and should_include_image(output, image_importance, severity)

            sent = False

            # Send image first if applicable
            if include_image:
                cap = image_caption
                if lang == "he" and image_caption_he:
                    cap = image_caption_he
                ok = send_telegram_photo(self.bot_token, chat_id, image_path, cap)
                if ok:
                    sent = True

            # Send text
            if lang == "both":
                # Send both languages as separate messages
                if text_he:
                    ok = send_telegram_text(self.bot_token, chat_id, text_he)
                    sent = sent or ok
                if text_en:
                    ok = send_telegram_text(self.bot_token, chat_id, text_en)
                    sent = sent or ok
            else:
                text = pick_text(output, text_he, text_en)
                if text:
                    ok = send_telegram_text(self.bot_token, chat_id, text)
                    sent = sent or ok

            # Send GIF if applicable
            if include_gif:
                ok = send_telegram_animation(self.bot_token, chat_id, gif_path, gif_caption)
                sent = sent or ok

            results[out_id] = "sent" if sent else "empty"

        # ── Log dispatch event ──
        self._log_dispatch(event_type, severity, results,
                           image_path=image_path, image_importance=image_importance,
                           gif_path=gif_path, has_text_he=bool(text_he),
                           has_text_en=bool(text_en))

        return results

    def _log_dispatch(self, event_type, severity, results,
                      image_path=None, image_importance="low",
                      gif_path=None, has_text_he=False, has_text_en=False):
        """Log every dispatch to state/dispatch-log.jsonl for tracking."""
        try:
            import time
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            state_dir = os.path.join(os.path.dirname(self.config_path), "state")
            os.makedirs(state_dir, exist_ok=True)
            log_path = os.path.join(state_dir, "dispatch-log.jsonl")

            entry = {
                "ts": time.time(),
                "utc": now.isoformat(),
                "type": event_type,
                "severity": severity,
                "media": {
                    "image": os.path.basename(image_path) if image_path else None,
                    "image_importance": image_importance if image_path else None,
                    "gif": os.path.basename(gif_path) if gif_path else None,
                    "has_text_he": has_text_he,
                    "has_text_en": has_text_en,
                },
                "results": results,
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            # Rotate at 2MB
            if os.path.getsize(log_path) > 2_000_000:
                self._rotate_dispatch_log(log_path)
        except Exception:
            pass  # Never let logging break dispatch

    @staticmethod
    def _rotate_dispatch_log(path, keep_hours=168):
        """Keep last 7 days of dispatch logs."""
        import time
        cutoff = time.time() - (keep_hours * 3600)
        kept = []
        with open(path) as f:
            for line in f:
                try:
                    e = json.loads(line.strip())
                    if e.get("ts", 0) >= cutoff:
                        kept.append(line.strip())
                except (json.JSONDecodeError, KeyError):
                    continue
        with open(path, "w") as f:
            for line in kept:
                f.write(line + "\n")

    def emit_text(self, event_type: str, severity: str = "LOW",
                  text_he: str = "", text_en: str = ""):
        """Convenience: emit text-only alert (no images)."""
        return self.emit(event_type, severity, text_he=text_he, text_en=text_en)

    def emit_photo(self, event_type: str, severity: str = "LOW",
                   text_he: str = "", text_en: str = "",
                   image_path: str = "", image_importance: str = "medium",
                   image_caption: str = ""):
        """Convenience: emit alert with photo."""
        return self.emit(event_type, severity, text_he=text_he, text_en=text_en,
                         image_path=image_path, image_importance=image_importance,
                         image_caption=image_caption)

    def get_outputs_for(self, event_type: str, severity: str = "LOW") -> list:
        """Get list of outputs that would receive this event (for pinned status etc.)."""
        return [o for o in self.outputs if should_send(o, event_type, severity)]

    def get_output_by_id(self, output_id: str) -> dict:
        """Get a specific output by its id."""
        for o in self.outputs:
            if o.get("id") == output_id:
                return o
        return {}


# ─── CLI: pipe JSON events via stdin ───

def main():
    """CLI mode: read JSON event from stdin, dispatch to all outputs."""
    if len(sys.argv) < 2:
        print("Usage: echo '{...}' | python3 dispatch.py config.json", file=sys.stderr)
        sys.exit(1)

    config_path = sys.argv[1]
    dispatcher = Dispatcher(config_path)

    raw = sys.stdin.read().strip()
    if not raw:
        sys.exit(0)

    event = json.loads(raw)

    results = dispatcher.emit(
        event_type=event.get("type", "unknown"),
        severity=event.get("severity", "LOW"),
        text_he=event.get("text_he", ""),
        text_en=event.get("text_en", ""),
        image_path=event.get("image", None),
        image_importance=event.get("image_importance", "low"),
        image_caption=event.get("image_caption", ""),
        image_caption_he=event.get("image_caption_he", ""),
        gif_path=event.get("gif", None),
        gif_caption=event.get("gif_caption", ""),
    )

    # Output results as JSON for the caller
    print(json.dumps(results))


if __name__ == "__main__":
    main()
