"""A speech bubble that floats above the pet."""
from PyQt5.QtCore import QRectF, Qt, QTimer
from PyQt5.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QWidget

MAX_TEXT_WIDTH = 220
PADDING = 10
TAIL_HEIGHT = 12
TAIL_HALF_WIDTH = 8
RADIUS = 12


class SpeechBubble(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.text = ""
        self.tail_x = 0.0
        self.text_font = self.font()
        self.text_font.setPointSize(11)
        self.text_font.setBold(True)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def say(self, text, seconds):
        self.text = text
        box = QFontMetrics(self.text_font).boundingRect(0, 0, MAX_TEXT_WIDTH, 1000, Qt.TextWordWrap, text)
        self.setFixedSize(box.width() + 2 * PADDING, box.height() + 2 * PADDING + TAIL_HEIGHT)
        self.hide_timer.start(int(seconds * 1000))
        self.show()
        self.update()

    def place(self, anchor_x, anchor_bottom, area):
        """Put the bubble above the anchor point, kept inside the screen area."""
        x = min(max(anchor_x - self.width() / 2, area.left()), area.right() + 1 - self.width())
        y = max(anchor_bottom - self.height(), area.top())
        margin = RADIUS + TAIL_HALF_WIDTH
        tail_x = min(max(anchor_x - x, margin), self.width() - margin)
        if tail_x != self.tail_x:
            self.tail_x = tail_x
            self.update()
        self.move(round(x), round(y))

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        body = QRectF(1, 1, self.width() - 2, self.height() - TAIL_HEIGHT - 2)
        shape = QPainterPath()
        shape.addRoundedRect(body, RADIUS, RADIUS)
        tail = QPainterPath()
        tail.moveTo(self.tail_x - TAIL_HALF_WIDTH, body.bottom())
        tail.lineTo(self.tail_x, self.height() - 1)
        tail.lineTo(self.tail_x + TAIL_HALF_WIDTH, body.bottom())
        tail.closeSubpath()
        painter.setPen(QPen(QColor("#333333"), 2))
        painter.setBrush(QColor("#ffffff"))
        painter.drawPath(shape.united(tail))
        painter.setFont(self.text_font)
        painter.setPen(QColor("#222222"))
        text_area = QRectF(PADDING, PADDING, self.width() - 2 * PADDING, self.height() - TAIL_HEIGHT - 2 * PADDING)
        painter.drawText(text_area, Qt.AlignCenter | Qt.TextWordWrap, self.text)
