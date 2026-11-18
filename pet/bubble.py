"""Speech bubbles that float above the pet."""
from collections import deque

from PyQt5.QtCore import QRectF, Qt, QTimer, QUrl
from PyQt5.QtGui import QColor, QDesktopServices, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QWidget

MAX_TEXT_WIDTH = 220
PADDING = 10
TAIL_HEIGHT = 12
TAIL_HALF_WIDTH = 8
RADIUS = 12
LINK_SECONDS = 10
MAX_QUEUE = 10
LINK_HINT = "Click to open the link"


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
        self.hint = ""
        self.tail_x = 0.0
        self.text_font = self.font()
        self.text_font.setPointSize(11)
        self.text_font.setBold(True)
        self.hint_font = self.font()
        self.hint_font.setPointSize(8)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.expire)

    def expire(self):
        self.hide()

    def hint_height(self):
        return QFontMetrics(self.hint_font).height() if self.hint else 0

    def say(self, text, seconds, hint=""):
        self.text = text
        self.hint = hint
        box = QFontMetrics(self.text_font).boundingRect(0, 0, MAX_TEXT_WIDTH, 1000, Qt.TextWordWrap, text)
        width = max(box.width(), QFontMetrics(self.hint_font).horizontalAdvance(hint) if hint else 0)
        self.setFixedSize(width + 2 * PADDING, box.height() + self.hint_height() + 2 * PADDING + TAIL_HEIGHT)
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
        hint_height = self.hint_height()
        text_area = QRectF(
            PADDING, PADDING, self.width() - 2 * PADDING, self.height() - TAIL_HEIGHT - 2 * PADDING - hint_height
        )
        painter.drawText(text_area, Qt.AlignCenter | Qt.TextWordWrap, self.text)
        if self.hint:
            painter.setFont(self.hint_font)
            painter.setPen(QColor("#0b5ed7"))
            hint_area = QRectF(PADDING, body.bottom() - PADDING - hint_height, text_area.width(), hint_height)
            painter.drawText(hint_area, Qt.AlignCenter, self.hint)


class LinkBubble(SpeechBubble):
    """A bubble you can click. Messages wait in a queue, and each one opens its link when clicked."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.queue = deque()
        self.url = None

    def pop_up(self, text, url):
        """Show a message now, or after the ones already showing."""
        if len(self.queue) < MAX_QUEUE:
            self.queue.append((text, url))
        if not self.isVisible():
            self.show_next()

    def show_next(self):
        if not self.queue:
            self.hide_timer.stop()
            self.hide()
            return
        text, self.url = self.queue.popleft()
        self.setCursor(Qt.PointingHandCursor if self.url else Qt.ArrowCursor)
        self.say(text, LINK_SECONDS, LINK_HINT if self.url else "")

    def expire(self):
        self.show_next()

    def clear(self):
        self.queue.clear()
        self.hide_timer.stop()
        self.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.url:
            QDesktopServices.openUrl(QUrl(self.url))
        self.show_next()
