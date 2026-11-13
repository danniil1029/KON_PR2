# Конфигурационное управление · вариант 10

Консольная программа на Python строит граф зависимостей пакетов NuGet.
Стрелка `A → B` означает, что пакет `A` зависит от пакета `B`.
В рабочем режиме программа получает данные через NuGet V3 и разбирает
XML-манифесты `.nuspec` стандартной библиотекой Python.

## Запуск

Распакуй весь ZIP и открой папку `nuget-graph-v10`. Для программы нужен
Python 3.10 или новее. DOT и SVG создаются средствами Python. Тестовый
режим работает локально. Для запросов к NuGet нужен доступ в интернет
или адрес доступного сервера NuGet V3.

На Windows можно дважды щёлкнуть по `run.bat`. Запустится локальный
пример с пакетом `A`, а окно останется открытым до нажатия клавиши.
Файлы `A.svg` и `A.dot` появятся в папке проекта.

Открой терминал в папке `nuget-graph-v10` и выполни команды.

```powershell
python -m src.main --test --repo tests/fixtures/graph.json --package A --tree
python -m unittest discover -s tests -v
```

В Windows команду `python` можно заменить на `py -3`. В Linux и macOS
можно использовать `python3` или `./run.sh` с теми же параметрами.
Код запускается напрямую из исходников. SVG открывается в браузере,
DOT — в текстовом редакторе.

## Как открыть этап в Git

Каждому этапу соответствует отдельный коммит и тег. Команда
`git log --oneline --decorate` показывает их в истории.
Команды ниже выполняются в папке проекта. После демонстрации вернись
к итоговой версии командой `git switch main`. Из любого этапа полный
README можно посмотреть командой `git show main:README.md`.

| Тег | Результат запуска |
| --- | --- |
| `stage-1` | Параметры в формате `ключ=значение`. |
| `stage-2` | Список прямых зависимостей NuGet. |
| `stage-3` | Список смежности после обхода BFS. |
| `stage-4` | Обратные зависимости по флагу `--reverse`. |
| `stage-5` | DOT, SVG и ASCII-дерево по флагу `--tree`. |

## Этап 1. Консольный прототип

В `src/main.py` библиотека `argparse` читает семь параметров. После
проверки `main` печатает каждую настройку на отдельной строке.

| Параметр | Назначение и значение по умолчанию |
| --- | --- |
| `--package ИМЯ` | Обязательное имя исходного пакета. |
| `--repo ИСТОЧНИК` | URL индекса NuGet V3 или путь к JSON. Без флага `--test` по умолчанию используется `https://api.nuget.org/v3/index.json`. |
| `--test` | Включить локальный режим. В этом режиме путь к файлу обязателен. |
| `--output ФАЙЛ.svg` | Путь к SVG в существующей папке. В прототипе по умолчанию `graph.svg`, на этапе 5 — `A.svg`. |
| `--tree` | Включить ASCII-дерево. Передаётся как флаг. |
| `--depth ЧИСЛО` | Неотрицательная глубина. Без параметра обход идёт по всем достижимым узлам. |
| `--exclude ПОДСТРОКА` | Исключить зависимости по непустой подстроке имени без учёта регистра. По умолчанию фильтр выключен. |

```powershell
git switch --detach stage-1
python -m src.main --package Example.Package --output A.svg --tree --depth 2 --exclude Abstractions
```

В выводе будут `package=Example.Package`, `output=A.svg`, `tree=True`
и остальные параметры. Для демонстрации ошибок выполни команды по одной.
Каждая команда выдаёт сообщение о неправильном вводе.

```powershell
python -m src.main --package "bad name"
python -m src.main --package A --repo=
python -m src.main --package A --test true
python -m src.main --package A --test
python -m src.main --package A --output A.png
python -m src.main --package A --tree true
python -m src.main --package A --depth -1
python -m src.main --package A --exclude=
```

## Этап 2. Прямые зависимости NuGet

`NugetRepository` находит в индексе NuGet V3 адрес
`PackageBaseAddress`, получает список версий и загружает `.nuspec`.
Функция `read_dependencies` читает зависимости выбранной платформы.
На этом этапе программа печатает только непосредственные зависимости.

```powershell
git switch --detach stage-2
python -m src.main --package Microsoft.Extensions.Logging --version 8.0.0 --framework net8.0
```

На `net8.0` прямые зависимости — `Microsoft.Extensions.DependencyInjection`,
`Microsoft.Extensions.Logging.Abstractions` и `Microsoft.Extensions.Options`.
Для каждого из этих пакетов выбирается версия `8.0.0`.

| Параметр | Назначение |
| --- | --- |
| `--version ВЕРСИЯ` | Версия исходного пакета. По умолчанию берётся последняя стабильная, а при её отсутствии последняя предварительная. |
| `--framework TFM` | Целевая платформа для выбора группы зависимостей. По умолчанию `net8.0`. |

## Этап 3. Прямые и транзитивные зависимости

`build_graph` обходит зависимости в ширину с помощью очереди
`collections.deque`. Корень находится на глубине 0. Вершина добавляется в
очередь при первом обнаружении. Повторная встреча сохраняет ребро, поэтому
циклическая зависимость остаётся в графе, а обход завершается.
При фильтрации проверяется имя зависимости. Корень сохраняется.

Тестовый репозиторий — `tests/fixtures/graph.json`. Ключи JSON — имена
из заглавных латинских букв, значения — списки прямых зависимостей.
Пакет, указанный только в списке, считается вершиной без зависимостей.

```json
{"A": ["B"], "B": ["C"], "C": []}
```

```powershell
git switch --detach stage-3
python -m src.main --test --repo tests/fixtures/graph.json --package A
python -m src.main --test --repo tests/fixtures/graph.json --package A --depth 1
python -m src.main --test --repo tests/fixtures/graph.json --package A --exclude ext
python -m src.main --test --repo tests/fixtures/graph.json --package F
```

| Сценарий | Ожидаемый результат |
| --- | --- |
| Полный граф от `A` | Есть цикл `A → B → D → A` и связи `B → D` и `C → D`. |
| Глубина 1 | Остаются `A`, `B` и `C`. |
| Фильтр `ext` | Исключается ветка `EXTRA → E`. |
| Корень `F` | У пакета нет зависимостей. |

## Этап 4. Обратные зависимости

`reverse_edges` меняет направление связей в локальном репозитории.
После этого та же функция `build_graph` находит пакеты, которые
зависят от заданного пакета прямо или через другие пакеты.
Флаг `--reverse` доступен в версии `stage-4` вместе с `--test`.

```powershell
git switch --detach stage-4
python -m src.main --test --repo tests/fixtures/graph.json --package D --reverse
python -m src.main --test --repo tests/fixtures/graph.json --package F --reverse
```

Для `D` выводятся `B, C, A`. Пакеты `B` и `C` зависят от него
напрямую, `A` — транзитивно. Для изолированного `F` выводится `(нет)`.

## Этап 5. Визуализация

`dot_source` формирует описание на языке Graphviz DOT.
`svg_document` размещает узлы по глубине и рисует стрелки средствами
Python. `save_graph` сохраняет два файла с одним именем и расширениями
`.dot` и `.svg`. Флаг `--tree` выводит ASCII-дерево. Метка `[cycle]`
означает возврат к узлу текущей ветки, `[shown]` — уже показанный узел.

Имена узлов локального графа берутся из JSON. Для NuGet обозначения
`A`, `B`, `C`, …, `Z`, `AA`, … назначаются в порядке BFS.
Обозначения совпадают в DOT, SVG и ASCII-дереве. Полное имя и версия
видны при наведении на узел SVG, в атрибуте `tooltip` файла DOT и
в расшифровке под деревом в консоли.

```powershell
git switch --detach stage-5
python -m src.main --test --repo tests/fixtures/graph.json --package A --tree
```

### Три пакета NuGet

Готовые пары `A.svg`/`A.dot`, `B.svg`/`B.dot`, `C.svg`/`C.dot`
и результаты сравнения находятся в папке `examples` рядом с проектом.
Буквы нумеруются заново в каждом графе, поэтому корень каждой схемы
обозначен `A`.

```powershell
python -m src.main --package Microsoft.Extensions.DependencyInjection --version 8.0.0 --tree --output A.svg
python -m src.main --package Microsoft.Extensions.Options --version 8.0.0 --tree --output B.svg
python -m src.main --package Microsoft.Extensions.Logging --version 8.0.0 --tree --output C.svg
```

| Граф | Корневой пакет NuGet 8.0.0 | Узлы с корнем | Рёбра |
| --- | --- | ---: | ---: |
| `A` | `Microsoft.Extensions.DependencyInjection` | 2 | 1 |
| `B` | `Microsoft.Extensions.Options` | 3 | 2 |
| `C` | `Microsoft.Extensions.Logging` | 6 | 7 |

Ниже приведена расшифровка. Общий префикс имён — `Microsoft.Extensions.`.
Версия всех узлов в этих трёх примерах — `8.0.0`.

| Буква | Граф A | Граф B | Граф C |
| --- | --- | --- | --- |
| A | DependencyInjection | Options | Logging |
| B | DependencyInjection.Abstractions | DependencyInjection.Abstractions | DependencyInjection |
| C | | Primitives | Logging.Abstractions |
| D | | | Options |
| E | | | DependencyInjection.Abstractions |
| F | | | Primitives |

### Сравнение со штатными инструментами .NET

Эталон в `examples/dotnet-comparison.txt` получен на .NET SDK 8.0.408
для `net8.0`. В каждом проверочном проекте использован один корневой
`PackageReference` с точной версией `[8.0.0]`. Имена и версии сверены
по `dotnet list package --include-transitive`, связи — по
`obj/project.assets.json` после `dotnet restore`. Вывод
`dotnet nuget why` показывает пути к общей зависимости.
После введения буквенных обозначений повторно проверены наборы узлов
и рёбер относительно сохранённых результатов. Новые графы получены
через локальный HTTP-репозиторий с тестовыми манифестами по метаданным
NuGet Gallery для `net8.0`. У трёх графов узлы и рёбра совпали.
В дереве программы повторная общая зависимость помечается `[shown]`,
а штатный вывод может повторять её в каждом пути.

Для повторения сравнения создай по одному отдельному проекту
`net8.0` на каждый из трёх корневых пакетов и добавь ссылку на версию
`[8.0.0]`. В папке каждого проекта выполни команды.

```powershell
dotnet restore
dotnet list package --include-transitive
dotnet nuget why Microsoft.Extensions.DependencyInjection.Abstractions
```

Для других пакетов результаты могут различаться. Программа подбирает
минимальную подходящую версию для каждого ребра. При конфликтующих
диапазонах в её графе возможны разные версии одного пакета. NuGet
разрешает версии для проекта целиком и учитывает больше правил выбора
платформ и сред выполнения. Здесь используются обычные диапазоны
версий и выбор точной или совместимой группы для поддерживаемых TFM.

## Функции и классы

### `src/main.py`

| Имя | Назначение |
| --- | --- |
| `nonnegative` | Проверяет целочисленную неотрицательную глубину. |
| `valid_source` | Проверяет структуру HTTP(S)-адреса. |
| `argument_parser` | Объявляет параметры командной строки и справку. |
| `validate_repository` | Проверяет имя пакета и источник, подставляет URL по умолчанию. |
| `validate_test_output` | Проверяет настройки локального режима и защищает исходный файл от перезаписи. |
| `validate_output` | Проверяет расширение SVG и выходные пути. |
| `validate_nuget_options` | Проверяет введённые версию и целевую платформу. |
| `parse_args` | Разбирает и проверяет конфигурацию. |
| `analyze` | Выбирает источник, определяет корень и вызывает BFS. |
| `dependencies` внутри `analyze` | Получает прямые зависимости из NuGet с учётом фильтра. |
| `print_graph` в этапах 3 и 4 | Печатает список смежности графа. |
| `main` | Запускает нужное действие этапа и возвращает код завершения. |

### `src/graph.py`

| Имя | Назначение |
| --- | --- |
| `excluded_name` | Проверяет, содержит ли имя подстроку фильтра. |
| `read_test_graph` | Читает JSON и строит словарь смежности. |
| `parse_test_dependencies` | Проверяет одну запись JSON и создаёт список узлов. |
| `build_graph` | Обходит зависимости с помощью BFS. |
| `reverse_edges` в этапе 4 | Разворачивает рёбра локального графа. |

### `src/nuget.py`

| Имя | Назначение |
| --- | --- |
| `Package` | Хранит имя и версию узла. Метод `__str__` формирует полную подпись. |
| `normalize_framework` | Приводит известные длинные имена платформ к коротким TFM. |
| `compatible_frameworks` | Возвращает поддерживаемые семейства и пределы версий платформ. |
| `framework_rank` | Оценивает пригодность группы для целевой платформы. |
| `read_dependencies` | Извлекает пары «имя и диапазон версии» из XML. |
| `fetch` | Загружает ресурс по HTTP(S) и сообщает о сетевых ошибках. |
| `index_list` | Читает массив из JSON-ответа. |
| `package_base` | Находит URL ресурса `PackageBaseAddress`. |
| `NugetRepository.__init__` | Запоминает URL, целевую платформу и создаёт кэш. |
| `NugetRepository.versions` | Загружает или берёт из кэша список версий. |
| `NugetRepository.root` | Выбирает версию корня и создаёт узел. |
| `NugetRepository.dependencies` | Загружает манифест и подбирает версии прямых зависимостей. |

### `src/versions.py`

| Имя | Назначение |
| --- | --- |
| `version_key` | Формирует ключ сравнения версий и предварительных выпусков. |
| `version_bounds` | Разбирает нижнюю и верхнюю границы диапазона версий. |
| `range_contains` | Проверяет попадание версии в диапазон. |
| `lowest_version` | Выбирает наименьшую подходящую версию. |
| `root_version` | Находит указанную версию корня или выбирает версию по умолчанию. |

### `src/render.py`

| Имя | Назначение |
| --- | --- |
| `letter_label` | Преобразует номер узла в буквенную подпись. |
| `node_labels` | Назначает подписи всем узлам. |
| `label_legend` | Формирует расшифровку букв. |
| `dot_source` | Записывает вершины, рёбра и подсказки в синтаксисе DOT. |
| `ascii_tree` | Форматирует дерево для консоли. |
| `graph_columns` | Группирует узлы по расстоянию от корня. |
| `layout_nodes` | Рассчитывает размеры и позиции узлов. |
| `edge_path` | Строит путь стрелки между узлами. |
| `draw_edges` | Добавляет стрелки и их подписи в SVG. |
| `draw_nodes` | Рисует блоки, буквенные подписи и подсказки. |
| `svg_document` | Собирает XML-документ SVG. |
| `save_graph` | Записывает файлы DOT и SVG. |

## Проверка и сдача

```powershell
git switch main
python -m unittest discover -s tests -v
git log --oneline --decorate
```

Тесты в `tests` проверяют ввод CLI, чтение манифеста, выбор версий,
BFS, циклы, фильтрацию, формат DOT и SVG, буквенные подписи и запуск
без команды `dot`. Тесты обратного обхода находятся в `stage-4`.
Папка `examples` находится за пределами Git-репозитория. Она содержит
готовые результаты для показа на защите.

Для публикации создай пустой публичный репозиторий и укажи его адрес
вместо `URL_РЕПОЗИТОРИЯ`. Выполни команды в папке проекта.

```powershell
git remote add origin URL_РЕПОЗИТОРИЯ
git push -u origin main --tags
```

### Документация

- [NuGet V3 PackageBaseAddress](https://learn.microsoft.com/nuget/api/package-base-address-resource)
- [Формат манифеста .nuspec](https://learn.microsoft.com/nuget/reference/nuspec)
- [Команда dotnet nuget why](https://learn.microsoft.com/dotnet/core/tools/dotnet-nuget-why)
- [Язык DOT](https://graphviz.org/doc/info/lang.html)
