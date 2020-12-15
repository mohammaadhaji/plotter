from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QStyle,
    QStyleOptionComboBox,
)

class ComboBox(QComboBox):
    arrowClicked = pyqtSignal()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        sc = self.style().hitTestComplexControl(
            QStyle.CC_ComboBox, opt, self.mapFromGlobal(event.globalPos()), self
        )
        if sc == QStyle.SC_ComboBoxArrow:
            self.arrowClicked.emit()
