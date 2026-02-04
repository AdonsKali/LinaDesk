import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor, pipeline
from io import BytesIO
import soundfile as sf
import numpy as np
import librosa

torch_dtype = torch.float32  # bfloat16 на CPU может давать мусор

device = 'cpu'
if torch.cuda.is_available():
    device = 'cuda'
device = torch.device(device)

whisper = WhisperForConditionalGeneration.from_pretrained(
    "./model/models/recognition/whisper",
    torch_dtype=torch_dtype,
    low_cpu_mem_usage=True,
    use_safetensors=True,
)

processor = WhisperProcessor.from_pretrained("./server/model/models/recognition/whisper")

asr_pipeline = pipeline(
    "automatic-speech-recognition",
    model=whisper,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    max_new_tokens=256,
    chunk_length_s=30,
    batch_size=16,
    return_timestamps=True,
    torch_dtype=torch_dtype,
    device=device,
)

# Чтение и ресемплинг
with open('./0127.mp3', 'rb') as f:
    media = f.read()

data, samplerate = sf.read(BytesIO(media))  # data: np.ndarray, samplerate: int

# Конвертируем в моно
if data.ndim > 1:
    data = np.mean(data, axis=1)

# Ресемплинг в 16000 Гц
if samplerate != 16000:
    data = librosa.resample(data.astype(np.float32), orig_sr=samplerate, target_sr=16000)
else:
    data = data.astype(np.float32)

# Транскрипция
asr = asr_pipeline(data, generate_kwargs={"max_new_tokens": 256}, return_timestamps=True)
print(asr['text'])
