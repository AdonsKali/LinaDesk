def get_stylesheet():
    return """
    QWidget {
        color: white;
        font-size: 14px;
    }

    #panel {
        background: rgba(0,0,0,0.55);
        border-radius: 16px;           
        padding: 14px;
    }

    QLineEdit {
        background: rgba(255,255,255,0.3);
        padding:6px;
        border-radius: 8px;
    }

    QComboBox {
        background: rgba(255,255,255,0.3);
        padding:6px;
        border-radius: 8px;
    }

    QPushButton {
        background: rgba(255,255,255,0.2);
        padding:8px;
        border-radius: 10px;        
    }
    QPushButton:hover {
        background: rgba(255,255,255,0.6);
    }
    
    QPushButton:pressed {
        background: rgba(255,255,255,0.5);
    }
    QToolTip#panel_tooltip {
        background: rgba(0, 0, 0, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        padding: 16px;
        font-size: 13px;
    }

    """