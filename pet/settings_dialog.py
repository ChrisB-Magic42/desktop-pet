"""The settings window opened from the pet's right-click menu."""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from pet.config import BEHAVIOURS, LIMITS, NAME_MAX, Settings

BEHAVIOUR_LABELS = {
    "wander": "Wander around",
    "follow": "Follow the mouse",
    "stay": "Stay in one place",
}


class SettingsDialog(QDialog):
    applied = pyqtSignal(object)

    def __init__(self, settings):
        super().__init__()
        self.setWindowTitle("Pet settings")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)

        self.name = QLineEdit()
        self.name.setMaxLength(NAME_MAX)
        self.scale = QDoubleSpinBox()
        self.scale.setRange(*LIMITS["scale"])
        self.scale.setSingleStep(0.25)
        self.scale.setSuffix(" x")
        self.speed = QSpinBox()
        self.speed.setRange(*LIMITS["speed"])
        self.speed.setSingleStep(10)
        self.speed.setSuffix(" px/s")
        self.behaviour = QComboBox()
        for key in BEHAVIOURS:
            self.behaviour.addItem(BEHAVIOUR_LABELS[key], key)
        self.sleepy = QCheckBox("Sleep when nothing is happening")
        self.always_on_top = QCheckBox("Stay on top of other windows")
        self.hide_fullscreen = QCheckBox("Hide when a full-screen app is open")
        self.speech_bubbles = QCheckBox("Show speech bubbles (Claude answered, and so on)")
        self.break_minutes = QSpinBox()
        self.break_minutes.setRange(*LIMITS["break_minutes"])
        self.break_minutes.setSingleStep(5)
        self.break_minutes.setSuffix(" min")
        self.break_minutes.setSpecialValueText("Off")
        self.autostart = QCheckBox("Start when I log in")
        self.bounciness = QSpinBox()
        self.bounciness.setRange(*LIMITS["bounciness"])
        self.bounciness.setSingleStep(5)
        self.bounciness.setSuffix(" %")
        self.gravity = QSpinBox()
        self.gravity.setRange(*LIMITS["gravity"])
        self.gravity.setSingleStep(10)
        self.gravity.setSuffix(" %")

        form = QFormLayout()
        form.addRow("Name", self.name)
        form.addRow("Size", self.scale)
        form.addRow("Speed", self.speed)
        form.addRow("Behaviour", self.behaviour)
        form.addRow(self.sleepy)
        form.addRow("Bounciness when thrown", self.bounciness)
        form.addRow("Gravity when thrown", self.gravity)
        form.addRow("Break reminder every", self.break_minutes)
        form.addRow(self.always_on_top)
        form.addRow(self.speech_bubbles)
        form.addRow(self.hide_fullscreen)
        form.addRow(self.autostart)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok
            | QDialogButtonBox.Apply
            | QDialogButtonBox.Cancel
            | QDialogButtonBox.RestoreDefaults
        )
        buttons.accepted.connect(self.accept_and_apply)
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(lambda button: self.handle_button(buttons, button))

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.load(settings)

    def load(self, settings):
        self.name.setText(settings.name)
        self.scale.setValue(settings.scale)
        self.speed.setValue(settings.speed)
        self.behaviour.setCurrentIndex(self.behaviour.findData(settings.behaviour))
        self.sleepy.setChecked(settings.sleepy)
        self.always_on_top.setChecked(settings.always_on_top)
        self.hide_fullscreen.setChecked(settings.hide_fullscreen)
        self.speech_bubbles.setChecked(settings.speech_bubbles)
        self.break_minutes.setValue(settings.break_minutes)
        self.bounciness.setValue(settings.bounciness)
        self.gravity.setValue(settings.gravity)
        self.autostart.setChecked(settings.autostart)

    def current(self):
        return Settings(
            name=self.name.text().strip() or Settings().name,
            scale=self.scale.value(),
            speed=self.speed.value(),
            behaviour=self.behaviour.currentData(),
            sleepy=self.sleepy.isChecked(),
            always_on_top=self.always_on_top.isChecked(),
            hide_fullscreen=self.hide_fullscreen.isChecked(),
            speech_bubbles=self.speech_bubbles.isChecked(),
            break_minutes=self.break_minutes.value(),
            bounciness=self.bounciness.value(),
            gravity=self.gravity.value(),
            autostart=self.autostart.isChecked(),
        )

    def handle_button(self, buttons, button):
        role = buttons.buttonRole(button)
        if role == QDialogButtonBox.ApplyRole:
            self.applied.emit(self.current())
        elif role == QDialogButtonBox.ResetRole:
            self.load(Settings())

    def accept_and_apply(self):
        self.applied.emit(self.current())
        self.accept()
