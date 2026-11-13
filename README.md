# Вариант 10. Граф зависимостей NuGet

## Этап 1. Консольный прототип

Программа на Python принимает семь параметров через `argparse`. При
правильном вводе она печатает каждое значение в виде `ключ=значение`.
Для запуска нужен Python 3.10 или новее.

| Ключ | Значение |
| --- | --- |
| `--package` | Имя пакета. |
| `--repo` | URL индекса NuGet V3 или путь к тестовому файлу. |
| `--test` | Флаг локального режима. |
| `--output` | Путь к выходному SVG. |
| `--tree` | Флаг вывода ASCII-дерева. |
| `--depth` | Максимальная глубина, целое число от нуля. |
| `--exclude` | Непустая подстрока имени для исключения пакетов. |

```powershell
python -m src.main --package Example.Package --output demo.svg --tree --depth 2 --exclude Abstractions
python -m src.main --package Example.Package --repo=
python -m src.main --package Example.Package --depth -1
python -m unittest discover -s tests -v
```

`argument_parser` объявляет параметры, `parse_args` запускает проверку,
`validate_repository` и `valid_source` проверяют источник, `validate_output`
проверяет путь для SVG, `nonnegative` проверяет глубину. `main` печатает
конфигурацию. Тесты проверяют значения по умолчанию, вывод и ошибки ввода.
