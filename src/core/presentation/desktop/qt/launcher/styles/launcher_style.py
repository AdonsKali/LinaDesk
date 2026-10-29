def get_stylesheet():
    return """
    QWidget {
        color: white;
        font-size: 14px;
    }

    QTabWidget::pane { border: 0; }
    QTabBar::tab { padding: 10px 16px; background: #2c333d; }
    QTabBar::tab:selected { background: #43546a; }
    QScrollArea, QScrollArea > QWidget > QWidget { background: #20252b; }
    QGroupBox { border: 1px solid #49515c; border-radius: 8px; margin-top: 12px; padding-top: 14px; }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; }
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