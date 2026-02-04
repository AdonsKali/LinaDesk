from PySide6.QtWidgets import QLineEdit, QToolButton
from PySide6.QtGui import QAction, QIcon, QCursor
from PySide6.QtCore import Signal, QTimer, QEvent, Qt
from settings import _
from random import randint
from paths import MEDIA


class Chat(QLineEdit):
    
    prompt_submitted = Signal(list)
    set_text = Signal(str)
    update_signal = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(300, 50)
        self.random_placeholder =  _("QLineEditor_placeholder")[randint(0, len(_("QLineEditor_placeholder"))-1)]
        self.setPlaceholderText(self.random_placeholder)
        self._i = 0
        self.setStyleSheet(
        """QLineEdit {
                background: rgba(82, 156, 247, 80);
                border: 1px solid gray;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Comic Sans MS', cursive;
                font-size: 20px;
                color: white;          
        }"""
        )
        self._enter_button = QAction()
        self._enter_button = self.addAction(QIcon(f"{MEDIA}/chat_components/send-1.svg"), QLineEdit.ActionPosition.TrailingPosition)
        self._enter_button.triggered.connect(self.__send_prompt)
        self.update_signal.connect(self.reset_progress)
        self.returnPressed.connect(self.__send_prompt)
        self.update_signal.connect(self.reset_progress)
        self.set_text.connect(lambda str: self.prompt_submitted.emit([self ,str]))

        self._timer = QTimer()
        self._timer.timeout.connect(self.__update_progress)

        for child in self.findChildren(QToolButton):
            if child.defaultAction() == self._enter_button:
                self.button = child
                break
        self.button.installEventFilter(self)


    def __send_prompt(self):
        if self.text():
            self.setEnabled(False)
            self._timer.start(150)
            self.prompt_submitted.emit([self ,self.text()])
        self.clear()


    def __update_progress(self):
        if self._i <= 3:
            self.setPlaceholderText(". "*self._i)
            self._i+=1
        else:
            self._i = 0


    def _cancel_generation(self):
        self.reset_generation.emit()


    def reset_progress(self):
        self._timer.stop()
        self.setPlaceholderText(self.random_placeholder)
        self.setEnabled(True)


    def eventFilter(self, obj, event: QEvent):
        if obj == self.button:
            if event.type() == QEvent.Enter:
                self.button.setCursor(QCursor(Qt.PointingHandCursor))
                self._enter_button.setIcon(QIcon(f"{MEDIA}/chat_components/send-2.svg"))
            elif event.type() == QEvent.Leave or event.type() == QEvent.MouseButtonRelease:
                self.button.setCursor(QCursor(Qt.ArrowCursor))
                self._enter_button.setIcon(QIcon(f"{MEDIA}/chat_components/send-1.svg"))
            elif event.type() == QEvent.MouseButtonPress:
                self.button.setCursor(QCursor(Qt.PointingHandCursor))
                self._enter_button.setIcon(QIcon(f"{MEDIA}/chat_components/send-3.svg"))
        return super().eventFilter(obj, event)
    

    def _translation(self, arr: list[str]) -> str:
        return arr[randint(0, len(arr))]
