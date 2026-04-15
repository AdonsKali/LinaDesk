from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QComboBox, QLabel, 
                               QVBoxLayout, QHBoxLayout, QGridLayout, QCheckBox)

class AdvancedSettings(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.label = QLabel()
        self.label.setText(self.tr("Advanced settings"))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logic_mode = QHBoxLayout()
        self.label_logic = QLabel()
        self.label_logic.setText(self.tr("Behavior mode"))
        
    
        self.list = QComboBox()
        self.list.addItem(self.tr("None"))
        self.list.addItem(self.tr("Default"))
        self.list.addItem(self.tr("Self mind"))
        self.list.setToolTip(
            self.tr("<b>Behavior mode</b><br>"
                   "Данный режим определяет как Лина будет себя вести:<br>"
                   "<i> • Self mind - за все действия Лины отвечает языковая модель (может потребоваться больше ресурсов)"
                   "<i> • Default - все действия лины случайны и не зависят от языковой модели</i>"
                   "<i> • None - Лина будет ничего не делать, оставаясь в IDLE режиме всегда</i>"

                   "\n<p style='color:red;'>Sandbox обязателен !</p></i><br>"
                   )
        )

        logic_mode.addWidget(self.label_logic)
        logic_mode.addWidget(self.list)

        grid = QGridLayout()
        self.sandbox = QCheckBox(self.tr("Sandbox"), self)
        self.sandbox.setToolTip(
            self.tr("<b>Sandbox</b><br>"
                   "Данный режим не позволяет Лине вылезать за рамки своей временной директории. Это значительно увеличивает безопасность вашей системы и данных<br>"
                   "<i style='color:green;'> Рекомендуется к использованию</i>")
        )
        grid.addWidget(self.sandbox, 0, 0)


        layout.addLayout(logic_mode)
        layout.addLayout(grid)
        layout.addStretch()


    def mousePressEvent(self, event):
        ...


    def mouseMoveEvent(self, event):
        ...


        


