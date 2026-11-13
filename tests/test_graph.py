"""Проверки обхода в ширину на тестовом репозитории."""

import unittest
from pathlib import Path

from src.graph import build_graph, read_test_graph
from src.nuget import Package

FIXTURE = Path(__file__).parent / "fixtures" / "graph.json"


class GraphTests(unittest.TestCase):
    """Проверить порядок, цикл, ограничения и изолированный узел."""

    def setUp(self):
        """Загрузить локальные данные."""
        self.source = read_test_graph(FIXTURE)
        self.root = Package("A")

    def test_cycle_and_shared_dependency(self):
        """Сохранить все связи, но раскрыть каждый узел один раз."""
        seen = []

        def dependencies(package):
            """Запомнить фактический порядок посещения."""
            seen.append(package.name)
            return self.source[package]

        graph = build_graph(self.root, dependencies)
        self.assertEqual(seen, ["A", "B", "C", "D", "EXTRA", "E"])
        self.assertEqual(graph[Package("D")], [self.root])
        self.assertIn(Package("D"), graph[Package("B")])
        self.assertIn(Package("D"), graph[Package("C")])

    def test_max_depth(self):
        """Показать узлы предельного уровня без их потомков."""
        graph = build_graph(self.root, self.source.__getitem__, max_depth=1)
        self.assertEqual(list(graph), list(map(Package, "ABC")))
        self.assertEqual(graph[Package("B")], [])
        self.assertEqual(graph[Package("C")], [])

    def test_exclusion(self):
        """Исключить ветку, доступную только через отфильтрованный узел."""
        graph = build_graph(self.root, self.source.__getitem__, exclude="ext")
        self.assertNotIn(Package("EXTRA"), graph)
        self.assertNotIn(Package("E"), graph)
        self.assertEqual(graph[Package("C")], [Package("D")])

    def test_isolated_package(self):
        """Вернуть граф из одного узла для пакета без зависимостей."""
        package = Package("F")
        self.assertEqual(build_graph(package, self.source.__getitem__),
                         {package: []})
