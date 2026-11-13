"""Получение версий и прямых зависимостей через NuGet V3."""

import json
import re
import xml.etree.ElementTree as xml
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from src.versions import lowest_version, root_version

PACKAGE_ID = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}")
DEFAULT_FRAMEWORK = "net8.0"
HTTP_TIMEOUT = 20
MODERN_NET_MIN = (5, 0)
LAST_NETCORE = (3, 1)
NETSTANDARD_21 = (2, 1)
CORE_STANDARD_LIMITS = (((3, 0), NETSTANDARD_21),
                        ((2, 0), (2, 0)),
                        ((1, 0), (1, 6)))
FRAMEWORK_PATTERN = re.compile(r"net(standard|coreapp)?(\d+)\.(\d+)")


@dataclass(frozen=True)
class Package:
    """Узел графа с именем и, для NuGet, версией."""

    name: str
    version: str = ""

    def __str__(self):
        """Получить подпись для консоли и DOT."""
        return f"{self.name}@{self.version}" if self.version else self.name


def normalize_framework(text):
    """Привести известные длинные имена платформ к кратким TFM."""
    text = text.lower().strip()
    for prefix, short in (
        (".netstandard", "netstandard"),
        (".netcoreapp", "netcoreapp"),
        (".netframework", "net"),
    ):
        if text.startswith(prefix):
            version = text[len(prefix):].removeprefix(",version=v")
            if prefix == ".netframework":
                version = version.replace(".", "")
            if prefix == ".netcoreapp":
                major, _, _ = version.partition(".")
                if major.isdigit() and int(major) >= MODERN_NET_MIN[0]:
                    short = "net"
            return short + version
    return text


def compatible_frameworks(family, version):
    """Вернуть приоритеты и верхние границы совместимых семейств."""
    limits = {family: (3, version)}
    if family is None and version >= MODERN_NET_MIN:
        limits["coreapp"] = 2, LAST_NETCORE
        limits["standard"] = 1, NETSTANDARD_21
    if family == "coreapp":
        for minimum, maximum in CORE_STANDARD_LIMITS:
            if version >= minimum:
                limits["standard"] = 1, maximum
                break
    return limits


def framework_rank(candidate, target):
    """Оценить точную группу или поддерживаемую совместимую группу."""
    if candidate == target:
        return 4, ()
    if not candidate:
        return 0, ()
    requested = FRAMEWORK_PATTERN.fullmatch(target)
    offered = FRAMEWORK_PATTERN.fullmatch(candidate)
    if not (requested and offered):
        return None
    target_family, major, minor = requested.groups()
    offered_family, other_major, other_minor = offered.groups()
    limits = compatible_frameworks(target_family, (int(major), int(minor)))
    if offered_family not in limits:
        return None
    priority, maximum = limits[offered_family]
    offered_version = int(other_major), int(other_minor)
    return (priority, offered_version) if offered_version <= maximum else None


def read_dependencies(content, framework):
    """Прочитать зависимости из плоского списка или подходящей группы."""
    root = xml.fromstring(content)
    if root.find("./{*}metadata") is None:
        raise ValueError("В манифесте NuGet отсутствует элемент metadata")
    dependencies = root.find("./{*}metadata/{*}dependencies")
    if dependencies is None:
        return []
    target = normalize_framework(framework)
    ranked_groups = []
    for group in dependencies.findall("./{*}group"):
        candidate = normalize_framework(group.get("targetFramework", ""))
        rank = framework_rank(candidate, target)
        if rank is not None:
            ranked_groups.append((rank, group))
    if ranked_groups:
        _, dependencies = max(ranked_groups, key=lambda item: item[0])
    elif dependencies.find("./{*}group") is not None:
        raise ValueError(f"В манифесте нет группы для {framework}")
    return [
        (item.get("id", ""), item.get("version", ""))
        for item in dependencies.findall("./{*}dependency")
    ]


def fetch(url):
    """Скачать один ресурс и сообщить причину ошибки HTTP."""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Ожидался URL HTTP или HTTPS: {url}")
    try:
        with urlopen(url, timeout=HTTP_TIMEOUT) as response:
            return response.read()
    except HTTPError as error:
        raise ValueError(f"HTTP {error.code} при загрузке {url}") from error
    except (URLError, TimeoutError) as error:
        raise ValueError(f"Не удалось загрузить {url}: {error}") from error


def index_list(url, field):
    """Прочитать массив из JSON-индекса NuGet."""
    index = json.loads(fetch(url))
    values = index.get(field) if isinstance(index, dict) else None
    if not isinstance(values, list):
        raise ValueError(f"Индекс {url} не содержит массив {field}")
    return values


def package_base(source):
    """Найти PackageBaseAddress в индексе NuGet V3."""
    for resource in index_list(source, "resources"):
        if not isinstance(resource, dict):
            continue
        kind = resource.get("@type")
        url = resource.get("@id")
        if isinstance(kind, str) and kind.split("/")[0] == "PackageBaseAddress":
            if isinstance(url, str) and url:
                return url.rstrip("/")
    raise ValueError("Индекс NuGet не содержит PackageBaseAddress")


class NugetRepository:
    """Источник пакетов с кэшем списков версий на время запуска."""

    def __init__(self, source, framework=DEFAULT_FRAMEWORK):
        """Открыть индекс NuGet и запомнить целевую платформу."""
        self.base = package_base(source)
        self.framework = framework
        self.versions_cache = {}

    def versions(self, name):
        """Получить список версий пакета, обращаясь к сети один раз."""
        if not PACKAGE_ID.fullmatch(name):
            raise ValueError(f"Некорректное имя пакета в манифесте: {name!r}")
        if name not in self.versions_cache:
            url = f"{self.base}/{name}/index.json"
            versions = index_list(url, "versions")
            if any(not isinstance(version, str) for version in versions):
                raise ValueError(f"Некорректный список версий для {name}")
            self.versions_cache[name] = versions
        return self.versions_cache[name]

    def root(self, name, requested=None):
        """Найти версию пакета, с которого начинается анализ."""
        name = name.lower()
        version = root_version(self.versions(name), requested)
        if version is None:
            raise ValueError(f"Пакет {name}: версия {requested!r} не найдена")
        return Package(name, version)

    def dependencies(self, package, include=None):
        """Получить список прямых зависимостей указанной версии."""
        folder = f"{self.base}/{package.name}/{package.version}"
        url = f"{folder}/{package.name}.nuspec"
        try:
            declared = read_dependencies(fetch(url), self.framework)
        except (ValueError, xml.ParseError) as error:
            raise ValueError(f"{package}: {error}") from error
        result = []
        for name, requirement in declared:
            name = name.lower()
            if include is not None and not include(name):
                continue
            version = lowest_version(self.versions(name), requirement)
            if version is None:
                raise ValueError(f"{package}: нет версии {name} {requirement}")
            result.append(Package(name, version))
        return result
