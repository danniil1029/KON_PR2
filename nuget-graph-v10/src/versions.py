"""Сравнение версий и подбор по диапазону из манифеста NuGet."""

import re

VERSION = re.compile(
    r"(\d+(?:\.\d+){0,3})(?:-([\w-]+(?:\.[\w-]+)*))?"
    r"(?:\+[\w-]+(?:\.[\w-]+)*)?",
    re.ASCII,
)
VERSION_PARTS = 4


def version_key(text):
    """Вернуть ключ с учётом числовых частей и метки prerelease."""
    match = VERSION.fullmatch(text)
    if not match:
        raise ValueError(f"Некорректная версия NuGet: {text!r}")
    release, prerelease = match.groups()
    numbers = [int(part) for part in release.split(".")]
    numbers.extend([0] * (VERSION_PARTS - len(numbers)))
    labels = tuple(
        (0, int(part)) if part.isdigit() else (1, part.lower())
        for part in prerelease.split(".")
    ) if prerelease else ()
    return tuple(numbers), not prerelease, labels


def version_bounds(requirement):
    """Извлечь границы и признаки включения границ."""
    if not requirement:
        return None, None, False, False
    if requirement[0] not in "[(":
        return version_key(requirement), None, True, False
    if requirement[-1] not in "])":
        raise ValueError(f"Некорректный диапазон NuGet: {requirement!r}")
    low, separator, high = requirement[1:-1].partition(",")
    if not separator:
        if requirement[0] == "[" and requirement[-1] == "]":
            exact = version_key(low.strip())
            return exact, exact, True, True
        raise ValueError(f"Некорректный диапазон NuGet: {requirement!r}")
    lower = version_key(low.strip()) if low.strip() else None
    upper = version_key(high.strip()) if high.strip() else None
    return lower, upper, requirement[0] == "[", requirement[-1] == "]"


def range_contains(key, bounds):
    """Проверить, что версия попадает в заданные границы."""
    low, high, include_low, include_high = bounds
    lower_ok = low is None or key > low or (include_low and key == low)
    upper_ok = high is None or key < high or (include_high and key == high)
    return lower_ok and upper_ok


def lowest_version(versions, requirement):
    """Выбрать минимальную подходящую версию для одного ребра графа."""
    bounds = version_bounds(requirement.strip())
    allow_preview = any(bound and not bound[1] for bound in bounds[:2])
    for version in sorted(versions, key=version_key):
        key = version_key(version)
        if (key[1] or allow_preview) and range_contains(key, bounds):
            return version
    return None


def root_version(versions, requested):
    """Найти указанную версию или взять последнюю стабильную."""
    if requested is not None:
        wanted = version_key(requested)
        matches = (value for value in versions if version_key(value) == wanted)
        return next(matches, None)
    stable = [value for value in versions if version_key(value)[1]]
    return max(stable or versions, key=version_key, default=None)
