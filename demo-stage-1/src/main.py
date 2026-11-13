"""Первый этап. Проверка и вывод настроек командной строки."""

import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_SOURCE = "https://api.nuget.org/v3/index.json"
PACKAGE_ID = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}")
TEST_ID = re.compile(r"[A-Z]+")
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
    """Объявить семь параметров из задания."""
    parser = argparse.ArgumentParser(
        description="Визуализация зависимостей NuGet. Вариант 10.",
        allow_abbrev=False,
    )
    parser.add_argument("--package", required=True, help="Имя пакета")
    parser.add_argument("--repo", help="URL NuGet V3 или путь к JSON-файлу")
    parser.add_argument("--test", action="store_true", help="Локальный режим")
    parser.add_argument(
        "--output", type=Path, default=Path("graph.svg"), help="Путь к SVG"
    )
    parser.add_argument("--tree", action="store_true", help="ASCII-дерево")
    parser.add_argument(
        "--depth", type=nonnegative, help="Максимальная глубина"
    )
    parser.add_argument("--exclude", help="Подстрока для исключения пакетов")
    return parser


def validate_repository(parser, args):
    """Проверить имя пакета и источник выбранного режима."""
    name_pattern = TEST_ID if args.test else PACKAGE_ID
    if not name_pattern.fullmatch(args.package):
        parser.error("--package: неверное имя для выбранного режима")
    if args.test:
        if not args.repo or not Path(args.repo).is_file():
            parser.error("--repo: нужен существующий тестовый файл")
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


def parse_args(argv=None):
    """Прочитать опции и проверить значения."""
    parser = argument_parser()
    args = parser.parse_args(argv)
    validate_repository(parser, args)
    validate_output(parser, args.output)
    if args.exclude is not None and not args.exclude.strip():
        parser.error("--exclude: подстрока должна быть непустой")
    return args


def main(argv=None):
    """Вывести семь параметров в формате ключ=значение."""
    args = parse_args(argv)
    for name, value in vars(args).items():
        print(f"{name}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
