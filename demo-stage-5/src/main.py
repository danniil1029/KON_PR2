"""Пятый этап. Анализ и визуализация зависимостей NuGet."""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlsplit

from src.graph import TEST_ID, build_graph, excluded_name, read_test_graph
from src.nuget import (
    DEFAULT_FRAMEWORK,
    PACKAGE_ID,
    NugetRepository,
    Package,
)
from src.render import ascii_tree, label_legend, node_labels, save_graph
from src.versions import version_key

DEFAULT_SOURCE = "https://api.nuget.org/v3/index.json"
ROOT_DEPTH = 0


def nonnegative(value):
    """Преобразовать введённую глубину в целое неотрицательное число."""
    try:
        depth = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("ожидается целое число") from error
    if depth < ROOT_DEPTH:
        raise argparse.ArgumentTypeError("глубина должна быть не меньше 0")
    return depth


def valid_source(value):
    """Проверить схему, имя сервера и номер порта HTTP(S)-адреса."""
    try:
        url = urlsplit(value)
        _ = url.port
    except ValueError:
        return False
    return (
        url.scheme in {"http", "https"}
        and bool(url.hostname)
        and not any(character.isspace() for character in value)
    )


def argument_parser():
    """Объявить параметры программы."""
    parser = argparse.ArgumentParser(
        description="Визуализация зависимостей NuGet. Вариант 10.",
        allow_abbrev=False,
    )
    parser.add_argument("--package", required=True, help="Имя пакета")
    parser.add_argument("--repo", help="URL NuGet V3 или путь к JSON-файлу")
    parser.add_argument("--test", action="store_true", help="Локальный режим")
    parser.add_argument(
        "--output", type=Path, default=Path("A.svg"), help="Путь к SVG"
    )
    parser.add_argument("--tree", action="store_true", help="ASCII-дерево")
    parser.add_argument(
        "--depth", type=nonnegative, help="Максимальная глубина"
    )
    parser.add_argument("--exclude", help="Подстрока для исключения пакетов")
    parser.add_argument("--version", help="Версия корневого пакета")
    parser.add_argument(
        "--framework", default=DEFAULT_FRAMEWORK, help="Целевая платформа .NET"
    )
    return parser


def validate_test_output(parser, args):
    """Проверить настройки локального режима и защитить исходный файл."""
    if args.version is not None:
        parser.error("--version: используется только с NuGet")
    source_path = Path(args.repo).resolve()
    for output in (args.output, args.output.with_suffix(".dot")):
        if output.resolve() == source_path:
            parser.error("--output: путь совпадает с тестовым файлом")


def validate_repository(parser, args):
    """Проверить имя пакета и источник выбранного режима."""
    name_pattern = TEST_ID if args.test else PACKAGE_ID
    if not name_pattern.fullmatch(args.package):
        parser.error("--package: неверное имя для выбранного режима")
    if args.test:
        if not args.repo or not Path(args.repo).is_file():
            parser.error("--repo: нужен существующий тестовый файл")
        validate_test_output(parser, args)
        return
    if args.repo is None:
        args.repo = DEFAULT_SOURCE
    if not valid_source(args.repo):
        parser.error("--repo: нужен корректный URL HTTP или HTTPS")


def validate_output(parser, output):
    """Проверить расширение файла SVG и наличие его папки."""
    if output.suffix.lower() != ".svg" or output.is_dir():
        parser.error("--output: укажите путь к файлу с расширением .svg")
    if not output.parent.is_dir():
        parser.error("--output: папка для SVG должна существовать")
    if output.with_suffix(".dot").is_dir():
        parser.error("--output: рядом с SVG нужен путь для файла .dot")


def validate_nuget_options(parser, args):
    """Проверить версию пакета и целевую платформу."""
    if args.version is not None:
        try:
            version_key(args.version)
        except ValueError as error:
            parser.error(f"--version: {error}")
    if not args.framework.strip():
        parser.error("--framework: укажите целевую платформу")


def parse_args(argv=None):
    """Прочитать опции и проверить значения."""
    parser = argument_parser()
    args = parser.parse_args(argv)
    validate_output(parser, args.output)
    validate_repository(parser, args)
    if args.exclude is not None and not args.exclude.strip():
        parser.error("--exclude: подстрока должна быть непустой")
    validate_nuget_options(parser, args)
    return args


def analyze(args):
    """Выбрать источник и обойти зависимости в ширину."""
    if args.test:
        source = read_test_graph(Path(args.repo))
        root = Package(args.package)
        if root not in source:
            raise ValueError(f"В тестовом файле нет пакета {root}")
        dependencies = source.__getitem__
    else:
        source = NugetRepository(args.repo, args.framework)
        root = source.root(args.package, args.version)

        def dependencies(package):
            """Пропустить исключённые имена до поиска версий."""
            return source.dependencies(
                package, lambda name: not excluded_name(name, args.exclude)
            )

    return root, build_graph(root, dependencies, args.depth, args.exclude)


def main(argv=None):
    """Сохранить DOT и SVG и при необходимости вывести дерево."""
    args = parse_args(argv)
    try:
        root, graph = analyze(args)
        labels = node_labels(graph)
        save_graph(graph, args.output, labels)
    except (ValueError, OSError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    if args.tree:
        print(ascii_tree(root, graph, labels))
        for item in label_legend(labels):
            print(item)
    print(f"SVG: {args.output}")
    print(f"DOT: {args.output.with_suffix('.dot')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
