Эта страница описывает, как собирать и запускать отдельные Docker-образы для компонентов: `nlp`, `bim`, `mcp-client`.

> Примечание: MCP (FreeCAD) не запускается в контейнере — MCP-client (контейнер) отправляет `stubs.json` на MCP, работающий локально в FreeCAD.

---

## 1. Подготовка
- Установи Docker Desktop (Windows/macOS) или Docker Engine (Linux).
- Убедись, что Docker работает: `docker version` и `docker info`.
- В Windows лучше иметь WSL2 включённым (рекомендуется).

---

## 2. Сборка образов (в корне репо)
```(powershell)```

*Перейди в корень проекта*

```cd C:\draftai```

- NLP

```docker build -f Dockerfile.nlp -t draftai/nlp:local .```

- BIM

```docker build -f Dockerfile.bim -t draftai/bim:local .```

- MCP-client (отправитель)

```docker build -f Dockerfile.mcp-client -t draftai/mcp-client:local .```

*Если Docker Desktop даёт ошибку при build — убедись, что в команде указан контекст . в конце (последний аргумент), и Docker Desktop запущен.*

Посмотреть список контейнеров (чтобы найти нужный)
docker ps -a

## 3. Запуск Docker NLP
```app/nlp_core``` — это путь внутри контейнера, а не папка на вашем Windows-диске. Docker создаёт изолированную файловую систему для контейнера: если вы не смонтировали хост-папку в контейнер через ```-v```, файлы остаются в контейнере и не видны на хосте.

**Как получить результаты из контейнера**

Контейнеры по-умолчанию работают в изолированной файловой системе — чтобы увидеть результаты на хосте, монтируй ```volume.```

*Пример: запуск NLP и сохранение результата в папку на хосте*

**Создаём хостовую папку**
```New-Item -ItemType Directory -Path C:\draftai\nlp_core\OUT -Force```

**Запускаем контейнер и монтируем** ```OUT → /workspace/output```

```docker run --rm \```

  ```-v "C:\draftai\nlp_core\input:/app/nlp_core/input:ro" \```

  ```-v "C:\draftai\nlp_core\OUT:/workspace/output" \```

  ```draftai/nlp:local \```

  ```python /app/nlp_core/nlp_core/run_cli.py --out /workspace/output/result.json -v```

После завершения файл ```C:\draftai\nlp_core\OUT\result.json``` будет содержать результат.

*либо:*
 
Запуск Docker NLP (создаём ```result.json``` на хосте)

Это важный шаг: NLP должен записать ```result.json``` в хостовую папку C```:\draftai\nlp_core\OUT.``` Выполни:

```$repo = "C:\draftai"```

```docker run --rm ` ```

  ```-v "${repo}\nlp_core\OUT:/workspace/output" ` ```

  ```draftai/nlp:local ` ```

  ```sh -c "python -m pip install --upgrade pip || true; python -m spacy download ru_core_news_sm || true; python /app/nlp_core/nlp_core/run_cli.py --out /workspace/output/result.json -v"```


**Пояснения:**

```-v "${repo}\nlp_core\OUT:/workspace/output"``` — результат будет доступен в ```C:\draftai\nlp_core\OUT.```


Команда внутри контейнера: обновление pip (без ошибок), попытка скачать spaCy-модель (если не включена в образ), затем запуск ```run_cli.py.```

**Проверка успешности:**

```Test-Path "C:\draftai\nlp_core\OUT\result.json"```        
```Get-Content "C:\draftai\nlp_core\OUT\result.json"```

*Если не появилась строка про созданный файл — смотри логи контейнера (см. раздел «Отладка» ниже).*


## 4. Запуск Docker BIM (вход — результат NLP, выход — папка runs на хосте)

После успешного шага 3 запускаем BIM. Важно — монтируем ```nlp_core/OUT``` так, чтобы BIM видел файл под тем путём, который он ожидает.

```docker run --rm ` ```

  ```-v "${repo}\nlp_core\OUT:/workspace/input:ro" ` ```

  ```-v "${repo}\bim_core\runs:/workspace/output" ` ```

  ```-v "${repo}\bim_core\runs:/app/bim_core/runs" ` ```

  ```draftai/bim:local ` ```

  ```python /app/bim_core/bim_core/run_cli.py --tz /workspace/input/result.json --out /workspace/output -v ```

## 5. Запуск Docker MCP-client (отправка в локальный MCP)

MCP-сервер у тебя запускается локально в FreeCAD (он слушает порт 9090 на хосте). 
```exec(open(r"C:\draftai\mcp_server\mcp_serverV3.py", encoding="utf-8").read())```

**Отправка примитивов (stubs)**
```docker run --rm ` ```

  ```-v "${repo}\bim_core\runs:/workspace/runs:ro" ` ```

  ```draftai/mcp-client:local ` ```

  ``` python /app/send_stubs_cli.py --stubs /workspace/runs/stubs.json --host host.docker.internal --port 9090 -v```

*если ```ENTRYPOINT = python /app/send_stubs_cli.py``` или ```CMD``` уже это делает)*

Не передаём ```python /app/send_stubs_cli.py``` в командной строке — передаём только аргументы скрипта:

```$repo="C:\draftai"```

```docker run --rm ` ```

  ```-v "${repo}\bim_core\runs:/workspace/runs:ro" ` ```

  ```draftai/mcp-client:local ` ```

  ```--stubs /workspace/runs/stubs.json --host host.docker.internal --port 9090 -v ```

*или если образ использует CMD:*

```docker run --rm -v "${repo}\bim_core\runs:/app/bim_core/runs:ro" draftai/mcp-client:local```

**Полная команда вручную (переопределить ENTRYPOINT)**

Можно временно обнулить ENTRYPOINT и передать команду целиком:

```docker run --rm --entrypoint "" ` ```

  ```-v "${repo}\bim_core\runs:/workspace/runs:ro" ` ```

  ```draftai/mcp-client:local ` ```

  ```python /app/send_stubs_cli.py --stubs /workspace/runs/stubs.json --host host.docker.internal --port 9090 ```

## 6. Советы и типичные ошибки

Где искать файлы? — Если не монтируешь ```host-volume```, файлы останутся в контейнере и будут потеряны после ```--rm```. Всегда монтируй ```output``` в папку хоста.

Права доступа: при записи в смонтированную папку контейнер под пользователем ```appuser``` может не иметь прав. Решение: монтировать папку и выставлять подходящие права, или запускать контейнер от ```root``` (не рекомендуется для финального образа).

FreeCAD: запуск MCP сервера внутри контейнера нежелателен — FreeCAD GUI нужен на хосте; используем клиентский контейнер для отправки стубов.

## 7. Где хранить Dockerfile в репо

```Dockerfile.nlp, Dockerfile.bim, Dockerfile.mcp-client``` — лежат в корне репозитория. При билде указывай ```-f``` и контекст . (корень проекта)


## 8. Запуск Docker контейнеров через Docker Desktop (GUI)
- **Открыть Docker Desktop**

Запусти Docker Desktop → перейди во вкладку Images. Там появятся образы, которые ты собрал, например:

```draftai/nlp:local```

```draftai/bim:local```

```draftai/mcp-client:local.```

- **Запустить контейнер из образа**

Найди нужный образ, например ```draftai/nlp:local.```

Нажми **Run**.

Появится окно настройки запуска контейнера.

- **Настроить Volumes (маппинг папок)**

Нажми **+ Add Volume.**

Укажи ```Host path``` (путь на твоём ПК) и ```Container path``` (куда смонтировать в контейнере).
Например:

NLP:

```Host: C:\draftai\nlp_core\OUT```

```Container: /workspace/output```

BIM:

```Host: C:\draftai\nlp_core\OUT → Container: /workspace/input:ro```

```Host: C:\draftai\bim_core\runs → Container: /workspace/output```

- **Указать команду/аргументы**

В окне **Run** есть поле ```Optional settings → Command.```

Если образ уже имеет CMD (например NLP запускается по умолчанию), можно оставить пустым.

Если нужно передать аргументы (например BIM или MCP-client), впиши:

```python /app/bim_core/bim_core/run_cli.py --tz /workspace/input/result.json --out /workspace/output -v```


или

```python /app/send_stubs_cli.py --stubs /workspace/runs/stubs.json --host host.docker.internal --port 9090 -v```

- **Запустить и проверить**

Нажми **Run container.**

Перейди во вкладку ```Containers / Apps``` → выбери свой контейнер.

Внутри доступны вкладки:

**Logs** — посмотреть вывод.

**Files** — исследовать файловую систему контейнера.

**Exec (CLI)** — открыть терминал внутри контейнера.

Если контейнер сразу завершился, он отобразится как **Exited**. В этом случае:

посмотри логи;

при необходимости перезапусти контейнер с другим **Command.**



