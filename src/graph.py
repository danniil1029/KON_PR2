"""Чтение тестового графа и обход в ширину."""

import json
import re
from collections import deque

from src.nuget import Package

TEST_ID = re.compile(r"[A-Z]+")


def excluded_name(name, text):
    """Проверить подстроку имени без учёта регистра."""
    return text is not None and text.casefold() in name.casefold()


def read_test_graph(path):
    """Прочитать JSON вида {"A": ["B"], "B": []}."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Тестовый файл должен содержать объект JSON")
    graph = {
        Package(name): parse_test_dependencies(name, children)
        for name, children in data.items()
    }
    for children in list(graph.values()):
        for child in children:
            graph.setdefault(child, [])
    return graph


def parse_test_dependencies(name, children):
    """Проверить запись одного пакета и преобразовать список зависимостей."""
    if not TEST_ID.fullmatch(name) or not isinstance(children, list):
        raise ValueError(f"Некорректная запись для пакета {name!r}")
    if any(not isinstance(child, str) or not TEST_ID.fullmatch(child)
           for child in children):
        raise ValueError(f"{name}: имена зависимостей должны быть A–Z")
    return [Package(child) for child in children]


def build_graph(root, dependencies, max_depth=None, exclude=None):
    """Собрать достижимые узлы и рёбра за один обход BFS."""
    queue = deque([(root, 0)])
    graph = {root: []}
    while queue:
        package, depth = queue.popleft()
        if max_depth is not None and depth >= max_depth:
            continue
        for child in dict.fromkeys(dependencies(package)):
            if excluded_name(child.name, exclude):
                continue
            graph[package].append(child)
            if child not in graph:
                graph[child] = []
                queue.append((child, depth + 1))
    return graph

def reverse_edges(graph):
    """Построить список смежности с обратным направлением рёбер."""
    reversed_graph = {package: [] for package in graph}
    for parent, children in graph.items():
        for child in dict.fromkeys(children):
            reversed_graph[child].append(parent)
    return reversed_graph
