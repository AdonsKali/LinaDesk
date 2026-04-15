import cv2

def list_cameras_opencv(max_test=5):
    """Проверяет доступные камеры через OpenCV"""
    available_cameras = []
    
    for i in range(max_test):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            codec = int(cap.get(cv2.CAP_PROP_FOURCC))
            
            codec_str = "".join([chr((codec >> 8 * i) & 0xFF) for i in range(4)])
            
            available_cameras.append({
                'index': i,
                'resolution': f"{width}x{height}",
                'fps': fps,
                'codec': codec_str,
                'backend': 'OpenCV'
            })
            
            cap.release()
    
    return available_cameras