<img src="git/splash_git.png" alt="main_picture" style="border-radius: 20px"> 

<h1 style="text-shadow: 0 0 5px #ff96d5
 ">🌸 Lina AI</h1>
 <p style="">— это локальный AI-агент в виде чиби-помощника (доступный пока на Windows) .  
Она умеет общаться с пользователем, выполнять системные команды и помогать в повседневных задачах.</p>
  

``Проект разрабатывается на Python одним человеком с использованием современных AI-моделей на базе Qwen3 и локального бэкенда, поэтому он ещё очень и очень сырой``



## 🤖 Доступные на данный момент возможности

- 💬 Общение в чате
- ⚙️ Выполнение команд
- 🎙️ Голосовое управление
- 🔎 Поиск в интернете

---

## 🛠️ Технологии

- **Python 3.10.6**
- **PySide6** — UI и анимации
- **LLaMA.cpp** — интерфейс взаимодействия с LLM
- **Vosk** — распознавание речи
- **FastAPI** - взаимодействие клиента и сервера

---

## 🖼️ GUI

Приложение имеет лаунчер через который запускается и настраивается клиент и сервер. 
Также есть tray, в которое можно свернуть лаунчер.

## 🚀 Установка
<div style=" border-radius: 2px; display: flex; justify-content:center">
<p style="color:red; size:12px; font-size: 16px; font">! Нужен python 3.10.6 !</p>
</div>

```bash
# Клонировать репозиторий
git clone -b dev https://github.com/AdonsKali/LinaAI.git
cd LinaAI

# Создать окружение
python -m venv .venv
.venv\Scripts\activate      # Windows

# Установить зависимости
pip install -r requirements.txt

```

Билдинг Llama под Cuda (NVidia)
```bash
#Убираем старую сборку если есть
pip uninstall llama-cpp-python -y 

#Грузим по новой в проект
git clone --recursive https://github.com/abetlen/llama-cpp-python
cd llama-cpp-python


#Ставим флаги сборки и компилируем билд
$env:CMAKE_ARGS="-DGGML_CUDA=ON -DLLAMA_BLAS=OF" #Для powershell !!!
$env:FORCE_CMAKE="1"                             #Для powershell !!!

pip install -e . --no-build-isolation --no-cache-dir --force-reinstall
```
<h3 style="display: inline; color:green">2)</h3> Установите NodeJS или аналоги BunJS, DenoJS (это нужно для поиска по сети)

---
## 💡 Как запустить ?

Для начала вам необходимо загрузить модель Qwen3, можете взять 
вот отсюда (я использовал такую) https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/tree/main . Если у вас есть видеокарта (NVidia) с 2-3 гб видеопамяти то подойдут модели Q3 и Q4 (чем выше цифра, тем больше нужно памяти, но и качество будет лучше). Скачанную модель копируете в server/models/model.gguf 

- После этого просто запускаете `run.bat` либо `update.bat`
- Откроется консольное окно, после этого откроется лаунчер, и уже в нем есть кнопка запустить. `Сначала запускаете сервере, потом уже клиент (сервер может запускаться долго 2-3 минуты, все зависит от вашего железа)`
- Появится чиби, и вы можете уже взаимодействовать


---
Проект занимает около 1 гб памяти и около 2 гб видеопамяти. 
` Я вам настоятельно рекомендую не баловаться с запросами по типу "форматни мне винду", так как она имеет доступ к powershell и командной строки и в теории может поломать систему `