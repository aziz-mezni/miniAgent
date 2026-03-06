"""Character widget — procedural QPainter drawing + sprite sheet support."""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal, QRect, QPoint, QSize
from PySide6.QtGui import (
    QColor, QPainter, QPainterPath, QLinearGradient, QRadialGradient,
    QBrush, QPen, QPixmap, QFont,
)
from PySide6.QtWidgets import QWidget


class CharacterWidget(QWidget):
    """Animated 2D character — procedural or sprite-sheet based."""

    clicked = Signal()

    def __init__(self, config_path: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Defaults
        self._config: dict[str, Any] = {}
        self._state = "idle"
        self._frame = 0
        self._time = 0.0  # Continuous time for smooth animation
        self._pupil_offset_x = 0.0
        self._pupil_offset_y = 0.0

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

        # Animation timer
        fps = self._get_anim_fps()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(int(1000 / max(fps, 1)))

        # Pupil wander timer (random eye movement)
        self._pupil_timer = QTimer(self)
        self._pupil_timer.timeout.connect(self._wander_pupils)
        self._pupil_timer.start(2000)

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

    def _get_anim_fps(self) -> int:
        return self._get_anim_config().get("fps", 2)

    def _get_num_frames(self) -> int:
        return self._get_anim_config().get("frames", 4)

    def set_state(self, state: str) -> None:
        """Change animation state: idle, talk, think, wave, error."""
        if state != self._state:
            self._state = state
            self._frame = 0
            self._time = 0.0
            fps = self._get_anim_fps()
            self._timer.setInterval(int(1000 / max(fps, 1)))
            self.update()

    def _animate(self) -> None:
        """Advance animation frame."""
        num_frames = self._get_num_frames()
        self._frame = (self._frame + 1) % num_frames
        self._time += 1.0 / max(self._get_anim_fps(), 1)
        self.update()

    def _wander_pupils(self) -> None:
        """Randomly shift pupils for liveliness."""
        if self._state == "idle":
            self._pupil_offset_x = random.uniform(-3, 3)
            self._pupil_offset_y = random.uniform(-2, 2)
        elif self._state == "talk":
            # Look slightly toward where the bubble would be
            self._pupil_offset_x = random.uniform(-1, 2)
            self._pupil_offset_y = random.uniform(-3, -1)

    # ── Painting ──────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._config.get("type") == "sprite_sheet" and self._sprite_sheet:
            self._draw_sprite_sheet(painter)
        else:
            self._draw_procedural(painter)

        painter.end()

    def _draw_procedural(self, painter: QPainter) -> None:
        """Draw the character procedurally using QPainter."""
        w = self.width()
        h = self.height()

        # Animation offsets
        bounce_y = 0.0
        shake_x = 0.0

        if self._state == "idle":
            amp = self._config.get("animations", {}).get("idle", {}).get("bounce_amplitude", 3)
            bounce_y = math.sin(self._time * math.pi * 2 * 0.5) * amp

        elif self._state == "error":
            shake_x = math.sin(self._time * math.pi * 2 * 8) * 5

        # Colors from config
        body_color = QColor(self._config.get("body_color", "#4FC3F7"))
        body_dark = QColor(self._config.get("body_color_dark", "#0288D1"))
        eye_color = QColor(self._config.get("eye_color", "#FFFFFF"))
        pupil_color = QColor(self._config.get("pupil_color", "#1A237E"))
        accent_color = QColor(self._config.get("accent_color", "#FF6F00"))
        mouth_color = QColor(self._config.get("mouth_color", "#1A237E"))
        cheek_color = QColor(self._config.get("cheek_color", "#F48FB1"))

        cx = w / 2 + shake_x
        cy = h / 2 + bounce_y + 10  # Shift down to leave room for antenna

        # ── Body (rounded rectangle with gradient) ──
        body_w = w * 0.7
        body_h = h * 0.55
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

        # ── Shadow under body ──
        shadow_color = QColor(0, 0, 0, 30)
        painter.setBrush(QBrush(shadow_color))
        painter.drawEllipse(
            int(cx - body_w * 0.4), int(cy + body_h / 2 + 5),
            int(body_w * 0.8), 8
        )

        # ── Antenna ──
        antenna_base_y = cy - body_h / 2
        antenna_tip_y = antenna_base_y - 20 + math.sin(self._time * 3) * 3
        antenna_tip_x = cx + math.sin(self._time * 2) * 2

        pen = QPen(body_dark, 3)
        painter.setPen(pen)
        painter.drawLine(
            int(cx), int(antenna_base_y),
            int(antenna_tip_x), int(antenna_tip_y)
        )

        # Antenna ball
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(accent_color))
        painter.drawEllipse(int(antenna_tip_x - 6), int(antenna_tip_y - 6), 12, 12)

        # Glow on antenna
        glow = QRadialGradient(antenna_tip_x, antenna_tip_y, 10)
        glow.setColorAt(0, QColor(255, 255, 255, 120))
        glow.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(int(antenna_tip_x - 10), int(antenna_tip_y - 10), 20, 20)

        # ── Eyes ──
        eye_y = cy - body_h * 0.1
        eye_spacing = body_w * 0.22
        eye_radius = 12

        for side in [-1, 1]:
            ex = cx + side * eye_spacing

            # White of eye
            painter.setBrush(QBrush(eye_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                int(ex - eye_radius), int(eye_y - eye_radius),
                int(eye_radius * 2), int(eye_radius * 2)
            )

            # Pupil
            px = ex + self._pupil_offset_x + side * 1
            py = eye_y + self._pupil_offset_y
            pupil_r = 5

            painter.setBrush(QBrush(pupil_color))
            painter.drawEllipse(
                int(px - pupil_r), int(py - pupil_r),
                int(pupil_r * 2), int(pupil_r * 2)
            )

            # Highlight
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
            painter.drawEllipse(int(px - 2), int(py - 3), 4, 4)

        # ── Cheeks ──
        cheek_color_alpha = QColor(cheek_color)
        cheek_color_alpha.setAlpha(80)
        painter.setBrush(QBrush(cheek_color_alpha))
        cheek_y = eye_y + eye_radius + 4
        for side in [-1, 1]:
            cx_cheek = cx + side * (eye_spacing + eye_radius + 2)
            painter.drawEllipse(int(cx_cheek - 6), int(cheek_y - 4), 12, 8)

        # ── Mouth ──
        mouth_y = eye_y + eye_radius + 12
        painter.setPen(QPen(mouth_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self._state == "talk":
            # Open mouth — alternates between open and half-open
            if self._frame % 2 == 0:
                painter.setBrush(QBrush(QColor(mouth_color)))
                painter.drawEllipse(int(cx - 6), int(mouth_y - 4), 12, 10)
            else:
                painter.drawArc(
                    int(cx - 8), int(mouth_y - 6), 16, 12,
                    200 * 16, 140 * 16
                )
        elif self._state == "error":
            # Wavy worried mouth
            path = QPainterPath()
            path.moveTo(cx - 10, mouth_y)
            path.cubicTo(cx - 5, mouth_y + 4, cx + 5, mouth_y - 4, cx + 10, mouth_y)
            painter.drawPath(path)
        else:
            # Smile
            painter.drawArc(
                int(cx - 8), int(mouth_y - 8), 16, 12,
                200 * 16, 140 * 16
            )

        # ── Think dots ──
        if self._state == "think":
            dot_y = cy - body_h / 2 - 30
            num_dots = 3
            active = self._frame % (num_dots + 1)
            for i in range(num_dots):
                alpha = 255 if i < active else 60
                dot_color = QColor(accent_color)
                dot_color.setAlpha(alpha)
                painter.setBrush(QBrush(dot_color))
                painter.setPen(Qt.PenStyle.NoPen)
                dx = cx - 10 + i * 10
                painter.drawEllipse(int(dx), int(dot_y), 6, 6)

        # ── Wave hand ──
        if self._state == "wave":
            hand_angle = math.sin(self._time * math.pi * 2 * 2) * 30
            hand_x = cx + body_w / 2 + 5
            hand_y = cy - 5

            painter.save()
            painter.translate(hand_x, hand_y)
            painter.rotate(hand_angle)

            # Arm
            painter.setPen(QPen(body_dark, 4))
            painter.drawLine(0, 0, 0, -20)

            # Hand circle
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(body_color))
            painter.drawEllipse(-6, -26, 12, 12)

            painter.restore()

        # ── Feet ──
        foot_y = cy + body_h / 2 - 2
        for side in [-1, 1]:
            fx = cx + side * body_w * 0.2
            painter.setBrush(QBrush(body_dark))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(fx - 10), int(foot_y), 20, 10)

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
