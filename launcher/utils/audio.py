import pyaudio

def get_microphones():
    """Получает список доступных микрофонов"""
    p = pyaudio.PyAudio()
    microphones = []
    
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        if 'microphone' in device_info['name'].lower():
            microphones.append({
                'index': i,
                'name': device_info['name']
            })
    
    p.terminate()
    return microphones