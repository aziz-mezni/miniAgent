"""Character widget — procedural QPainter drawing + sprite sheet support."""

from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal, QRect, QPoint, QSize
from PySide6.QtGui import (
    QColor, QPainter, QPainterPath, QLinearGradient, QRadialGradient,
    QBrush, QPen, QPixmap, QFont,
)
from PySide6.QtWidgets import QWidget

# Render at 60 FPS for smooth animation regardless of logical frame count
RENDER_FPS = 60
RENDER_INTERVAL_MS = 1000 // RENDER_FPS


class CharacterWidget(QWidget):
    """Animated 2D character — procedural or sprite-sheet based."""

    clicked = Signal()

    def __init__(self, config_path: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Defaults
        self._config: dict[str, Any] = {}
        self._state = "idle"
        self._frame = 0
        self._start_time = time.monotonic()
        self._state_time = 0.0  # Time since state change

        # Smooth pupil animation
        self._pupil_target_x = 0.0
        self._pupil_target_y = 0.0
        self._pupil_x = 0.0
        self._pupil_y = 0.0

        # Load config
        if config_path:
            self._load_config(config_path)
        else:
            self._load_defaults()

        # Size from config
        w, h = self._config.get("size", [120, 140])
        self.setFixedSize(w, h)

        # Transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Single high-FPS render timer (60 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(RENDER_INTERVAL_MS)

        # Pupil wander timer (random eye target every 1.5-3s)
        self._pupil_timer = QTimer(self)
        self._pupil_timer.timeout.connect(self._wander_pupils)
        self._pupil_timer.start(1800)

        # Sprite sheet cache
        self._sprite_sheet: QPixmap | None = None
        if self._config.get("type") == "sprite_sheet" and self._config.get("sprite_sheet"):
            path = Path(self._config["sprite_sheet"])
            if path.exists():
                self._sprite_sheet = QPixmap(str(path))

    def _load_config(self, path: str) -> None:
        p = Path(path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        else:
            self._load_defaults()

    def _load_defaults(self) -> None:
        self._config = {
            "name": "Spark",
            "type": "procedural",
            "size": [120, 140],
            "body_color": "#4FC3F7",
            "body_color_dark": "#0288D1",
            "eye_color": "#FFFFFF",
            "pupil_color": "#1A237E",
            "accent_color": "#FF6F00",
            "mouth_color": "#1A237E",
            "cheek_color": "#F48FB1",
            "animations": {
                "idle": {"frames": 4, "fps": 2, "bounce_amplitude": 3},
                "talk": {"frames": 6, "fps": 8},
                "think": {"frames": 4, "fps": 3},
                "wave": {"frames": 6, "fps": 6},
                "error": {"frames": 2, "fps": 4},
            },
            "sprite_sheet": None,
        }

    def _get_anim_config(self) -> dict:
        anims = self._config.get("animations", {})
        return anims.get(self._state, {"frames": 4, "fps": 2})

    def _get_anim_fps(self) -> float:
        return float(self._get_anim_config().get("fps", 2))

    def _get_num_frames(self) -> int:
        return self._get_anim_config().get("frames", 4)

    def set_state(self, state: str) -> None:
        """Change animation state: idle, talk, think, wave, error."""
        if state != self._state:
            self._state = state
            self._frame = 0
            self._state_time = 0.0
            self._start_time = time.monotonic()
            self.update()

    def _tick(self) -> None:
        """60 FPS render tick — update continuous time and logical frame."""
        now = time.monotonic()
        dt = now - self._start_time
        self._state_time = dt

        # Compute logical frame from continuous time + state FPS
        anim_fps = self._get_anim_fps()
        num_frames = self._get_num_frames()
        if anim_fps > 0 and num_frames > 0:
            self._frame = int(dt * anim_fps) % num_frames

        # Smooth pupil interpolation (lerp toward target)
        lerp = 0.08
        self._pupil_x += (self._pupil_target_x - self._pupil_x) * lerp
        self._pupil_y += (self._pupil_target_y - self._pupil_y) * lerp

        self.update()

    def _wander_pupils(self) -> None:
        """Set a new random pupil target for smooth interpolation."""
        if self._state == "idle":
            self._pupil_target_x = random.uniform(-3.5, 3.5)
            self._pupil_target_y = random.uniform(-2.5, 2.5)
        elif self._state == "talk":
            self._pupil_target_x = random.uniform(-1, 2.5)
            self._pupil_target_y = random.uniform(-3.5, -1)
        elif self._state == "think":
            self._pupil_target_x = random.uniform(-1, 1)
            self._pupil_target_y = random.uniform(-4, -2)
        else:
            self._pupil_target_x = 0
            self._pupil_target_y = 0

        # Randomize next wander interval
        self._pupil_timer.setInterval(random.randint(1200, 3000))

    # ── Painting ──────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if self._config.get("type") == "sprite_sheet" and self._sprite_sheet:
            self._draw_sprite_sheet(painter)
        else:
            self._draw_procedural(painter)

        painter.end()

    def _draw_procedural(self, painter: QPainter) -> None:
        """Draw the character procedurally using QPainter with smooth animation."""
        w = self.width()
        h = self.height()
        t = self._state_time  # Continuous time for smooth animation

        # ── Smooth animation offsets ──
        bounce_y = 0.0
        shake_x = 0.0
        squash = 1.0  # Vertical squash/stretch factor
        body_tilt = 0.0

        if self._state == "idle":
            amp = self._config.get("animations", {}).get("idle", {}).get("bounce_amplitude", 3)
            # Smooth sinusoidal bounce
            bounce_y = math.sin(t * math.pi * 1.2) * amp
            # Subtle breathing squash
            squash = 1.0 + math.sin(t * math.pi * 0.8) * 0.015
            # Gentle body sway
            body_tilt = math.sin(t * 0.7) * 1.5

        elif self._state == "talk":
            # Small bounce while talking
            bounce_y = math.sin(t * math.pi * 3) * 1.5
            squash = 1.0 + math.sin(t * math.pi * 4) * 0.02

        elif self._state == "think":
            # Slow gentle tilt
            body_tilt = math.sin(t * 1.5) * 3
            bounce_y = math.sin(t * math.pi * 0.8) * 1

        elif self._state == "error":
            # Damped shake that settles
            decay = math.exp(-t * 2) + 0.3
            shake_x = math.sin(t * math.pi * 12) * 5 * decay

        elif self._state == "wave":
            bounce_y = math.sin(t * math.pi * 1.5) * 2

        # Colors from config
        body_color = QColor(self._config.get("body_color", "#4FC3F7"))
        body_dark = QColor(self._config.get("body_color_dark", "#0288D1"))
        eye_color = QColor(self._config.get("eye_color", "#FFFFFF"))
        pupil_color = QColor(self._config.get("pupil_color", "#1A237E"))
        accent_color = QColor(self._config.get("accent_color", "#FF6F00"))
        mouth_color = QColor(self._config.get("mouth_color", "#1A237E"))
        cheek_color = QColor(self._config.get("cheek_color", "#F48FB1"))

        cx = w / 2 + shake_x
        cy = h / 2 + bounce_y + 10  # Shift down for antenna room

        # ── Apply body tilt ──
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(body_tilt)
        painter.translate(-cx, -cy)

        # ── Body (rounded rectangle with gradient) ──
        body_w = w * 0.7
        body_h = h * 0.55 * squash
        body_rect = QRect(
            int(cx - body_w / 2), int(cy - body_h / 2),
            int(body_w), int(body_h)
        )

        grad = QLinearGradient(cx, cy - body_h / 2, cx, cy + body_h / 2)
        grad.setColorAt(0, body_color)
        grad.setColorAt(1, body_dark)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(body_rect, 20, 20)

        # ── Subtle highlight on body ──
        highlight = QRadialGradient(cx - body_w * 0.15, cy - body_h * 0.25, body_w * 0.4)
        highlight.setColorAt(0, QColor(255, 255, 255, 50))
        highlight.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(highlight))
        painter.drawRoundedRect(body_rect, 20, 20)

        # ── Shadow under body ──
        shadow_alpha = max(10, int(30 - abs(bounce_y) * 3))
        shadow_color = QColor(0, 0, 0, shadow_alpha)
        shadow_scale = max(0.6, 1.0 - abs(bounce_y) * 0.02)
        painter.setBrush(QBrush(shadow_color))
        sw = body_w * 0.8 * shadow_scale
        painter.drawEllipse(
            int(cx - sw / 2), int(cy + body_h / 2 + 5 + abs(bounce_y) * 0.5),
            int(sw), 8
        )

        # ── Antenna ──
        antenna_base_y = cy - body_h / 2
        antenna_tip_y = antenna_base_y - 22 + math.sin(t * 3.5) * 4
        antenna_tip_x = cx + math.sin(t * 2.3) * 3

        pen = QPen(body_dark, 2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        # Curved antenna using quadratic bezier
        antenna_path = QPainterPath()
        antenna_path.moveTo(cx, antenna_base_y)
        antenna_path.quadTo(
            cx + math.sin(t * 1.8) * 5, antenna_base_y - 12,
            antenna_tip_x, antenna_tip_y
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(antenna_path)

        # Antenna ball
        ball_size = 10 + math.sin(t * 4) * 1.5
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(accent_color))
        painter.drawEllipse(
            int(antenna_tip_x - ball_size / 2), int(antenna_tip_y - ball_size / 2),
            int(ball_size), int(ball_size)
        )

        # Glow on antenna (pulsing)
        glow_alpha = int(80 + math.sin(t * 3) * 40)
        glow = QRadialGradient(antenna_tip_x, antenna_tip_y, 12)
        glow.setColorAt(0, QColor(255, 255, 255, glow_alpha))
        glow.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(int(antenna_tip_x - 12), int(antenna_tip_y - 12), 24, 24)

        # ── Eyes ──
        eye_y = cy - body_h * 0.08
        eye_spacing = body_w * 0.22
        eye_radius = 12

        # Blink every ~4 seconds
        blink_cycle = t % 4.0
        blink_squash = 1.0
        if 3.7 < blink_cycle < 3.85:
            blink_squash = max(0.1, 1.0 - (blink_cycle - 3.7) / 0.075)
        elif 3.85 < blink_cycle < 4.0:
            blink_squash = min(1.0, (blink_cycle - 3.85) / 0.075)

        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            er_h = eye_radius * blink_squash

            # White of eye
            painter.setBrush(QBrush(eye_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                int(ex - eye_radius), int(eye_y - er_h),
                int(eye_radius * 2), int(er_h * 2)
            )

            if blink_squash > 0.3:
                # Pupil (smooth interpolated position)
                px = ex + self._pupil_x + side * 1
                py = eye_y + self._pupil_y
                pupil_r = 5

                painter.setBrush(QBrush(pupil_color))
                painter.drawEllipse(
                    int(px - pupil_r), int(py - pupil_r),
                    int(pupil_r * 2), int(pupil_r * 2)
                )

                # Highlight
                painter.setBrush(QBrush(QColor(255, 255, 255, 210)))
                painter.drawEllipse(int(px - 2), int(py - 3), 4, 4)

        # ── Cheeks ──
        cheek_color_alpha = QColor(cheek_color)
        cheek_color_alpha.setAlpha(70)
        painter.setBrush(QBrush(cheek_color_alpha))
        cheek_y = eye_y + eye_radius + 4
        for side in [-1, 1]:
            cx_cheek = cx + side * (eye_spacing + eye_radius + 2)
            painter.drawEllipse(int(cx_cheek - 7), int(cheek_y - 4), 14, 9)

        # ── Mouth ──
        mouth_y = eye_y + eye_radius + 14
        painter.setPen(QPen(mouth_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self._state == "talk":
            # Smooth mouth open/close using sine wave
            mouth_open = (math.sin(t * math.pi * 6) + 1) / 2  # 0 to 1
            mouth_h = int(4 + mouth_open * 8)
            mouth_w = int(8 + mouth_open * 4)
            painter.setPen(QPen(mouth_color, 1.5))
            painter.setBrush(QBrush(QColor(mouth_color)))
            painter.drawEllipse(
                int(cx - mouth_w / 2), int(mouth_y - mouth_h / 2),
                mouth_w, mouth_h
            )
        elif self._state == "error":
            # Wavy worried mouth
            path = QPainterPath()
            path.moveTo(cx - 10, mouth_y)
            wobble = math.sin(t * 6) * 2
            path.cubicTo(
                cx - 5, mouth_y + 4 + wobble,
                cx + 5, mouth_y - 4 - wobble,
                cx + 10, mouth_y
            )
            painter.drawPath(path)
        else:
            # Gentle smile
            painter.drawArc(
                int(cx - 8), int(mouth_y - 8), 16, 12,
                200 * 16, 140 * 16
            )

        # ── Think dots ──
        if self._state == "think":
            dot_y = cy - body_h / 2 - 28
            num_dots = 3
            for i in range(num_dots):
                # Phase-offset pulsing
                phase = t * 3 - i * 0.8
                alpha = int((math.sin(phase) + 1) / 2 * 195 + 60)
                scale = 0.8 + (math.sin(phase) + 1) / 2 * 0.4
                dot_color = QColor(accent_color)
                dot_color.setAlpha(alpha)
                painter.setBrush(QBrush(dot_color))
                painter.setPen(Qt.PenStyle.NoPen)
                dx = cx - 12 + i * 12
                r = int(3 * scale)
                painter.drawEllipse(int(dx - r), int(dot_y - r), r * 2, r * 2)

        # ── Wave hand ──
        if self._state == "wave":
            hand_angle = math.sin(t * math.pi * 3) * 35
            hand_x = cx + body_w / 2 + 5
            hand_y = cy - 8

            painter.save()
            painter.translate(hand_x, hand_y)
            painter.rotate(hand_angle)

            # Arm
            painter.setPen(QPen(body_dark, 4, cap=Qt.PenCapStyle.RoundCap))
            painter.drawLine(0, 0, 0, -22)

            # Hand circle
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(body_color))
            painter.drawEllipse(-7, -29, 14, 14)

            painter.restore()

        # ── Feet ──
        foot_y = cy + body_h / 2 - 2
        # Subtle foot wiggle
        foot_offset = math.sin(t * 2) * 1
        for i, side in enumerate([-1, 1]):
            fx = cx + side * body_w * 0.2 + (foot_offset if i == 0 else -foot_offset)
            painter.setBrush(QBrush(body_dark))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(fx - 10), int(foot_y), 20, 10)

        painter.restore()  # Undo body tilt

    def _draw_sprite_sheet(self, painter: QPainter) -> None:
        """Draw from a sprite sheet. Rows = states, columns = frames."""
        if not self._sprite_sheet:
            return

        state_order = ["idle", "talk", "think", "wave", "error"]
        row = state_order.index(self._state) if self._state in state_order else 0

        w, h = self._config.get("size", [120, 140])
        num_frames = self._get_num_frames()
        col = self._frame % num_frames

        source_rect = QRect(col * w, row * h, w, h)
        dest_rect = QRect(0, 0, w, h)

        painter.drawPixmap(dest_rect, self._sprite_sheet, source_rect)

    # ── Mouse events ──────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
