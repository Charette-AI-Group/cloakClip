"""The Help > About dialog.

A plain QDialog rather than a QMessageBox: the message box positions its
buttons by role, which varies with the platform style, and Donate needs to
sit on the left regardless.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cloakClip import appConfig

donateStyle = f"""
    QPushButton {{
        background-color: {appConfig.donateColor};
        color: {appConfig.donateTextColor};
        border: none;
        border-radius: 6px;
        padding: 6px 18px;
        font-weight: 600;
    }}
    QPushButton:hover, QPushButton:pressed {{
        background-color: {appConfig.donatePressedColor};
    }}
"""


class AboutDialog(QDialog):
    def __init__(self, aboutText: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {appConfig.appName}")
        # Read back by the caller instead of connecting to the click, so the
        # browser opens after this dialog has closed rather than behind it.
        self.donateRequested = False

        layout = QVBoxLayout(self)

        self.aboutLabel = QLabel(aboutText)
        self.aboutLabel.setTextFormat(Qt.TextFormat.RichText)
        self.aboutLabel.setMinimumWidth(420)
        self.aboutLabel.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.aboutLabel.setOpenExternalLinks(True)
        layout.addWidget(self.aboutLabel)
        layout.addSpacing(8)

        self.donateButton = QPushButton("Donate")
        self.donateButton.setStyleSheet(donateStyle)
        self.donateButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.donateButton.clicked.connect(self.onDonateClicked)

        self.closeButton = QPushButton("Close")
        self.closeButton.clicked.connect(self.reject)
        # Enter closes the dialog; it must not open a payment page.
        self.closeButton.setDefault(True)
        self.closeButton.setAutoDefault(True)
        self.donateButton.setAutoDefault(False)

        buttonRow = QHBoxLayout()
        buttonRow.addWidget(self.donateButton)
        buttonRow.addStretch()
        buttonRow.addWidget(self.closeButton)
        layout.addLayout(buttonRow)

    def onDonateClicked(self) -> None:
        self.donateRequested = True
        self.accept()
