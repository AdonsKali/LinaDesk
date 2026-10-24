from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QCheckBox

PERMISSION_LABELS = {
    "read": "Чтение", "write": "Изменение файлов",
    "network": "Доступ к сети", "execute": "Запуск программ",
}


class ToolPermissionDialog(QMessageBox):
    def __init__(self, request, parent=None):
        super().__init__(parent)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowTitle("Лина — разрешение для плагина")
        self.setIcon(QMessageBox.Icon.Question)
        self.setTextFormat(Qt.TextFormat.PlainText)
        names = ", ".join(PERMISSION_LABELS.get(p, p) for p in request["permissions"])
        self.setText(f"Плагин '{request['plugin_name']}' требует разрешение на '{names}'. Разрешить ?")
        self.setInformativeText(f"Инструмент: {request['tool_name']}")
        self.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        self.button(QMessageBox.StandardButton.Yes).setText("Разрешить")
        self.button(QMessageBox.StandardButton.No).setText("Отказать")
        self.setDefaultButton(QMessageBox.StandardButton.No)
        self.setEscapeButton(QMessageBox.StandardButton.No)
        self.remember = QCheckBox("Запомнить для этого инструмента", self)
        self.setCheckBox(self.remember)
