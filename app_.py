def start_app():

    from app.src.ui.init_components import root, chat, message, voice_button, lina
    from app.src.controller.init_controller import controller

    #init base ui widgets 
    lina.setParent(root)
    chat.setParent(root)
    message.setParent(root)
    voice_button.setParent(root) 

    chat.hide()
    voice_button.hide()

    #base placement 
    lina.move(lina.x(), lina.y()+100)
    message.move(lina.x()+lina.size().width(), -1*lina.y()+lina.size().width() - 80)
    chat.move(lina.size().width()//2-chat.width(), lina.y() + lina.size().height()+10)
    voice_button.move(chat.size().width() + 10, chat.y() + (chat.size().height() - voice_button.sizeHint().height())//2)
    root.sizeHint()
    root.show()
    
    