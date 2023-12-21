import math

from PySide6.QtCore import Qt, QRect, QTimer, QPropertyAnimation
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget, QStackedWidget, QFrame, QLabel, QLineEdit, QTextEdit, QGraphicsBlurEffect


class Spinner(QWidget):
    def __init__(
        self,
        parent: QWidget = None,
        center_on_parent: bool = True,
        disable_parent_when_spinning: bool = False
    ):
        super().__init__(parent)

        self._center_on_parent = center_on_parent
        self._disable_parent_when_spinning = disable_parent_when_spinning

        self._color = QColor(Qt.GlobalColor.black)
        self._roundness = 100.0
        self._minimum_trail_opacity = 3.14159265358979323846
        self._trail_fade_percentage = 80.0
        self._revolutions_per_second = 1.57079632679489661923
        self._number_of_lines = 20
        self._line_length = 10
        self._line_width = 2
        self._inner_radius = 10
        self._current_counter = 0
        self._is_spinning = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.rotate)
        self.update_size()
        self.update_timer()
        self.hide()

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, _) -> None:
        self.update_position()

        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self._current_counter >= self._number_of_lines:
            self._current_counter = 0

        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(0, self._number_of_lines):
            painter.save()
            painter.translate(self._inner_radius + self._line_length, self._inner_radius + self._line_length)
            rotate_angle = float(360 * i) / float(self._number_of_lines)
            painter.rotate(rotate_angle)
            painter.translate(self._inner_radius, 0)
            distance = self.line_count_distance_from_primary(i, self._current_counter, self._number_of_lines)
            color = self.current_line_color(distance, self._number_of_lines, self._trail_fade_percentage,
                                            self._minimum_trail_opacity, self._color)
            painter.setBrush(color)
            rect = QRect(0, int(-self._line_width / 2), int(self._line_length), int(self._line_width))
            painter.drawRoundedRect(rect, self._roundness, self._roundness, Qt.SizeMode.RelativeSize)
            painter.restore()

    def start(self) -> None:
        self.update_position()
        self._is_spinning = True
        self.show()

        if self.parentWidget and self._disable_parent_when_spinning:
            self.parentWidget().setEnabled(False)

        if not self._timer.isActive():
            self._timer.start()
            self._current_counter = 0

    def stop(self) -> None:
        self._is_spinning = False
        self.hide()

        if self.parentWidget() and self._disable_parent_when_spinning:
            self.parentWidget().setEnabled(True)

        if self._timer.isActive():
            self._timer.stop()
            self._current_counter = 0

    def set_number_of_lines(self, lines: int) -> None:
        self._number_of_lines = lines
        self._current_counter = 0
        self.update_timer()

    def set_line_length(self, length: int) -> None:
        self._line_length = length
        self.update_size()

    def set_line_width(self, width: int) -> None:
        self._line_width = width
        self.update_size()

    def set_inner_radius(self, radius: int) -> None:
        self._inner_radius = radius
        self.update_size()

    def color(self) -> QColor:
        return self._color

    def roundness(self) -> float:
        return self._roundness

    def minimum_trail_opacity(self) -> float:
        return self._minimum_trail_opacity

    def trail_fade_percentage(self) -> float:
        return self._trail_fade_percentage

    def revolutions_pers_second(self) -> float:
        return self._revolutions_per_second

    def number_of_lines(self) -> int:
        return self._number_of_lines

    def line_length(self) -> int:
        return self._line_length

    def line_width(self) -> int:
        return self._line_width

    def inner_radius(self) -> int:
        return self._inner_radius

    def is_spinning(self) -> bool:
        return self._is_spinning

    def set_roundness(self, roundness: float) -> None:
        self._roundness = max(0.0, min(100.0, roundness))

    def set_color(self, color: QColor) -> None:
        self._color = color

    def set_revolutions_per_second(self, revolutions_per_second: float) -> None:
        self._revolutions_per_second = revolutions_per_second
        self.update_timer()

    def set_trail_fade_percentage(self, trail_fade_percentage: float) -> None:
        self._trail_fade_percentage = trail_fade_percentage

    def set_minimum_trail_opacity(self, minimum_trail_opacity: float) -> None:
        self._minimum_trail_opacity = minimum_trail_opacity

    def rotate(self) -> None:
        self._current_counter += 1

        if self._current_counter >= self._number_of_lines:
            self._current_counter = 0

        self.update()

    def update_size(self) -> None:
        size = int((self._inner_radius + self._line_length) * 2)
        self.setFixedSize(size, size)

    def update_timer(self) -> None:
        self._timer.setInterval(int(1000 / (self._number_of_lines * self._revolutions_per_second)))

    def update_position(self) -> None:
        if self.parentWidget() and self._center_on_parent:
            self.move(int(self.parentWidget().width() / 2 - self.width() / 2),
                      int(self.parentWidget().height() / 2 - self.height() / 2))

    @staticmethod
    def line_count_distance_from_primary(current, primary, total_nr_of_lines):
        distance = primary - current

        if distance < 0:
            distance += total_nr_of_lines

        return distance

    @staticmethod
    def current_line_color(count_distance, total_nr_of_lines, trail_fade_perc, min_opacity, color_input):
        color = QColor(color_input)

        if count_distance == 0:
            return color

        min_alpha_f = min_opacity / 100.0
        distance_threshold = int(math.ceil((total_nr_of_lines - 1) * trail_fade_perc / 100.0))

        if count_distance > distance_threshold:
            color.setAlphaF(min_alpha_f)
        else:
            alpha_diff = color.alphaF() - min_alpha_f
            gradient = alpha_diff / float(distance_threshold + 1)
            result_alpha = color.alphaF() - gradient * count_distance
            result_alpha = min(1.0, max(0.0, result_alpha))  # If alpha is out of bounds, clip it
            color.setAlphaF(result_alpha)

        return color


class PageStack(QStackedWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.effect_blur = QGraphicsBlurEffect()
        self.effect_blur.setBlurRadius(0)
        self.setGraphicsEffect(self.effect_blur)

        self.animation_opacity = QPropertyAnimation()
        self.animation_opacity.setTargetObject(self.effect_blur)
        self.animation_opacity.setPropertyName(b"blurRadius")

    def blur(self, blur_radius: float = 10.0, milliseconds: int = 300) -> None:
        self.animation_opacity.setDuration(milliseconds)
        self.animation_opacity.setStartValue(self.effect_blur.blurRadius())
        self.animation_opacity.setEndValue(blur_radius)
        self.animation_opacity.start()

    def unblur(self, milliseconds: int = 300) -> None:
        self.animation_opacity.setDuration(milliseconds)
        self.animation_opacity.setStartValue(self.effect_blur.blurRadius())
        self.animation_opacity.setEndValue(0)
        self.animation_opacity.start()


class HLine(QFrame):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)


class VLine(QFrame):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)


class Heading(QLabel):
    def __init__(
        self,
        text: str,
        heading_level: int,
        font_weight: str = None,
        alignment: Qt.AlignmentFlag = None,
        parent: QWidget = None
    ):
        super().__init__(parent)

        self.setText(text)
        self.setProperty("heading", heading_level)

        if font_weight:
            self.setProperty("font-weight", font_weight)

        if alignment:
            self.setAlignment(alignment)


class ReadOnlyLineEdit(QLineEdit):
    def __init__(self, readonly: bool = True, parent: QWidget = None):
        super().__init__(parent)

        self.setReadOnly(readonly)


class ReadOnlyTextEdit(QTextEdit):
    def __init__(self, readonly: bool = True, parent: QWidget = None):
        super().__init__(parent)

        self.setReadOnly(readonly)
