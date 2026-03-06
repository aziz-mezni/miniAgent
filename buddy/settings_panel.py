"""Settings dialog for Buddy assistant — LLM provider, model, system prompt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QTextEdit, QSlider, QPushButton, QGroupBox,
    QFormLayout, QWidget,
)

if TYPE_CHECKING:
    from pilot.config import Config


# ── Provider presets ──────────────────────────────────────────────────

PROVIDERS = [
    {
        "name": "LM Studio (Local)",
        "base_url": "http://localhost:1234/v1",
        "needs_key": False,
    },
    {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434/v1",
        "needs_key": False,
    },
    {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "needs_key": True,
    },
    {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "needs_key": True,
    },
    {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "needs_key": True,
    },
    {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "needs_key": True,
    },
    {
        "name": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "needs_key": True,
    },
    {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "needs_key": True,
    },
    {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "needs_key": True,
    },
    {
        "name": "Custom",
        "base_url": "",
        "needs_key": True,
    },
]


class SettingsDialog(QDialog):
    """Modal settings dialog for configuring LLM provider and agent."""

    settings_applied = Signal()

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._needs_client_refresh = False

        self.setWindowTitle("Buddy Settings")
        self.setFixedSize(420, 540)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )

        # ── Global stylesheet ──
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 18px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #333;
            }
            QLabel {
                color: #555;
                font-size: 12px;
                background: transparent;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 5px 8px;
                background: white;
                color: #1A1A1A;
                font-family: "Segoe UI";
                font-size: 12px;
                min-height: 18px;
            }
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 4px 8px;
                background: white;
                color: #1A1A1A;
                font-family: "Segoe UI";
                font-size: 11px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 1px solid #4FC3F7;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background: white;
                border: 1px solid #ccc;
                selection-background-color: #E3F2FD;
                color: #1A1A1A;
            }
        """)

        self._setup_ui()
        self._load_from_config()

    # ── UI ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        # Title
        title = QLabel("⚙  Settings")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #333; font-size: 16px; padding: 0 0 4px 0;")
        layout.addWidget(title)

        # ── Provider group ──
        provider_group = QGroupBox("LLM Provider")
        p_layout = QFormLayout(provider_group)
        p_layout.setContentsMargins(12, 8, 12, 12)
        p_layout.setSpacing(8)

        self._provider_combo = QComboBox()
        for p in PROVIDERS:
            self._provider_combo.addItem(p["name"])
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        p_layout.addRow("Provider:", self._provider_combo)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("http://localhost:1234/v1")
        p_layout.addRow("Base URL:", self._url_input)

        self._key_label = QLabel("API Key:")
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("sk-...")
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        p_layout.addRow(self._key_label, self._key_input)

        self._model_input = QLineEdit()
        self._model_input.setPlaceholderText("e.g., gpt-4o, qwen2.5-coder-32b")
        p_layout.addRow("Model:", self._model_input)

        layout.addWidget(provider_group)

        # ── Agent group ──
        agent_group = QGroupBox("Agent")
        a_layout = QFormLayout(agent_group)
        a_layout.setContentsMargins(12, 8, 12, 12)
        a_layout.setSpacing(8)

        # Temperature
        temp_widget = QWidget()
        temp_hlayout = QHBoxLayout(temp_widget)
        temp_hlayout.setContentsMargins(0, 0, 0, 0)
        temp_hlayout.setSpacing(8)

        self._temp_slider = QSlider(Qt.Orientation.Horizontal)
        self._temp_slider.setRange(0, 100)
        self._temp_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #ddd;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #4FC3F7;
                border: none;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #4FC3F7;
                border-radius: 2px;
            }
        """)

        self._temp_label = QLabel("0.7")
        self._temp_label.setFixedWidth(30)
        self._temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._temp_slider.valueChanged.connect(
            lambda v: self._temp_label.setText(f"{v / 100:.1f}")
        )

        temp_hlayout.addWidget(self._temp_slider, 1)
        temp_hlayout.addWidget(self._temp_label)
        a_layout.addRow("Temperature:", temp_widget)

        # System prompt
        self._prompt_edit = QTextEdit()
        self._prompt_edit.setFixedHeight(100)
        self._prompt_edit.setPlaceholderText("System prompt for the agent...")
        a_layout.addRow("System Prompt:", self._prompt_edit)

        layout.addWidget(agent_group)

        layout.addStretch()

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(80, 32)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1px solid #ccc;
                border-radius: 6px;
                color: #555;
                font-size: 12px;
            }
            QPushButton:hover { background: #f0f0f0; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setFixedSize(80, 32)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #4FC3F7;
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background: #03A9F4; }
            QPushButton:pressed { background: #0288D1; }
        """)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    # ── Provider switching ────────────────────────────────────────────

    def _on_provider_changed(self, index: int) -> None:
        if 0 <= index < len(PROVIDERS):
            provider = PROVIDERS[index]
            if provider["name"] != "Custom":
                self._url_input.setText(provider["base_url"])

            needs_key = provider["needs_key"]
            self._key_label.setVisible(needs_key)
            self._key_input.setVisible(needs_key)

            if not needs_key:
                self._key_input.setText("not-needed")

    # ── Load / Save ───────────────────────────────────────────────────

    def _load_from_config(self) -> None:
        """Populate fields from current config."""
        current_url = self._config.api.base_url
        matched = len(PROVIDERS) - 1  # Default to "Custom"
        for i, p in enumerate(PROVIDERS):
            if p["base_url"] and current_url.rstrip("/").startswith(
                p["base_url"].rstrip("/")
            ):
                matched = i
                break

        self._provider_combo.setCurrentIndex(matched)
        self._url_input.setText(self._config.api.base_url)
        self._key_input.setText(self._config.api.api_key)
        self._model_input.setText(self._config.api.model)

        temp_val = int(self._config.agent.temperature * 100)
        self._temp_slider.setValue(temp_val)
        self._temp_label.setText(f"{self._config.agent.temperature:.1f}")

        self._prompt_edit.setPlainText(self._config.agent.system_prompt)

    def _save(self) -> None:
        """Apply settings to the runtime config and close."""
        old_url = self._config.api.base_url
        old_key = self._config.api.api_key

        self._config.api.base_url = self._url_input.text().strip()
        self._config.api.api_key = self._key_input.text().strip()
        self._config.api.model = self._model_input.text().strip()
        self._config.agent.temperature = self._temp_slider.value() / 100.0
        self._config.agent.system_prompt = self._prompt_edit.toPlainText()

        self._needs_client_refresh = (
            old_url != self._config.api.base_url
            or old_key != self._config.api.api_key
        )

        self.settings_applied.emit()
        self.accept()

    @property
    def needs_client_refresh(self) -> bool:
        return self._needs_client_refresh
