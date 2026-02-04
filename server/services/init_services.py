from . import *


#Initial llama.cpp inference
inference: Inference = Inference()
#Initial vosk recognize service
recognize: Recognize = Recognize()
#Initial tool manager service
tool_manager: Manager = Manager()