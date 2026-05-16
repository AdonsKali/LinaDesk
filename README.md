# <div align="center">🌸 Lina AI - Чиби-ассистент</div>

<div align="center">

![Lina AI Banner](splash_git.png)

</div>

<div align="center">
  <strong>Локальный AI-агент в форме очаровательного чиби-помощника</strong>
</div>



<br>

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.10.6-informational?style=flat&logo=python&logoColor=white&color=lightgray" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Windows-informational?style=flat&logo=windows&logoColor=white&color=lightgray" alt="Platform">
  <img src="https://img.shields.io/badge/Status-Development-important?style=flat&logo=github&logoColor=white&color=orange" alt="Development Status">
</div>

<br>

<div align="center">
  <h3>✨ Особенности</h3>
</div>

| Функция | Описание |
|--------|----------|
| 💬 **Общение в чате** | Естественный диалог с ИИ-ассистентом |
| 🎤 **Голосовое управление** | Голосовое управление для удобства |
| ⚙️ **Выполнение задач** | Исполнение системных команд и приложений |
| 🔍 **Поиск в интернете** | Доступ к актуальной информации онлайн |
| 🎨 **Красивый интерфейс** | Эстетичный дизайн с анимациями |

<br>

<div align="center">
  <h3>🚀 Технологии</h3>
</div>

| Технология | Назначение | Преимущество |
|------------|------------|--------------|
| <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/250px-Python-logo-notext.svg.png" width="50" height="50"><br>**Python** | Язык программирования | Надежность и простота |
| <img src="https://qt-wiki-uploads.s3.amazonaws.com/images/e/ed/Qtforpython2023.png" width="50" height="50"><br>**PySide6** | UI и анимации | Современный интерфейс |
| <img src="https://raw.githubusercontent.com/abetlen/llama-cpp-python/main/docs/icon.svg" width="50" height="50"><br>**LLaMA.cpp** | Работа с LLM | Локальная обработка ИИ |
| <img src="https://alphacephei.com/img/vosk.png" width="50" height="50"><br>**Vosk** | Распознавание речи | Локальное преобразование речи в текст |
| <img src="https://avatars.githubusercontent.com/u/156354296?s=200&v=4" width="50" height="50"><br>**FastAPI** | Взаимодействие между клиентом и сервером | Высокая производительность |

<br>

<div align="center">
  <h3>🖥️ Интерфейс</h3>
</div>

Lina AI предоставляет интуитивно понятный интерфейс с возможностью:

- Лаунчер для управления клиентом и сервером
- Системный трей для быстрого доступа
- Анимированный чиби-персонаж для взаимодействия
- Настройка параметров ИИ и голосового управления

<br>

<div align="center">
  <h3>🛠️ Установка</h3>
</div>


> Приложение тестировалось на Python 3.10.6

#### 1. Клонирование репозитория:
```bash
git clone -b dev https://github.com/AdonsKali/LinaDesk
cd LinaAI
```

#### 2. Установка зависимостей:
```bash
# Запустите скрипт обновления
update.bat  # Для Windows
```

#### 3. (Опционально) Установка CUDA для GPU-ускорения (NVIDIA):
```bash
# Удалите старую версию, если существует
pip uninstall llama-cpp-python -y

# Клонируйте репозиторий для компиляции с CUDA
git clone --recursive https://github.com/abetlen/llama-cpp-python
cd llama-cpp-python

# Установите переменные сборки и соберите
$env:CMAKE_ARGS = "-DGGML_CUDA=ON -DLLAMA_BLAS=ON"  # Для PowerShell!
$env:FORCE_CMAKE = "1"

pip install -e . --no-build-isolation --no-cache-dir --force-reinstall
```

> **Примечание:** Убедитесь, что у вас установлен NodeJS (или его аналоги BunJS, DenoJS), чтобы использовать функции поиска в сети.

<br>

<div align="center">
  <h3>🎮 Запуск</h3>
</div>

После первой установки через `update.bat`, вы можете запускать приложение через `run.bat`.

```bash
# Простой запуск после установки
run.bat
```

<div align="center">
  <h3> 🔁 Обновление </h3>
</div>

```bash
# Запускаете update.bat
update.bat  
```

<div align="center">
  <h3>⚠️ Важная информация</h3>
</div>


> Приложение использует около 1 ГБ оперативной памяти и до 2 ГБ видеопамяти в зависимости от выбранной модели ИИ.


> Не экспериментируйте с командами, которые могут изменить системные настройки (например, форматирование дисков), так как ассистент имеет доступ к PowerShell и командной строке.


> Автор не несет ответственности за поврежденные системы!

<br>

<div align="center">
  <h3>🌟 Вклад в развитие проекта</h3>
</div>

Приветствуется ваш вклад в развитие Lina AI! Создавайте issue и pull request, если хотите улучшить функциональность или исправить ошибки.

<div align="center">
  <sub>Сделано с ❤️ для лучшего взаимодействия человека и ИИ</sub>
</div>