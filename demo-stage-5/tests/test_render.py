"""Проверки ASCII, DOT и SVG."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from src.graph import build_graph, read_test_graph
from src.nuget import Package
from src.render import (
    SVG_NAMESPACE,
    ascii_tree,
    dot_source,
    label_legend,
    node_labels,
    svg_document,
)

FIXTURE = Path(__file__).parent / "fixtures" / "graph.json"


class RenderTests(unittest.TestCase):
    """Проверить сохранение рёбер и корректное дерево для циклов."""

    def prepare_fixture(self):
        """Построить граф тестового пакета A."""
        source = read_test_graph(FIXTURE)
        self.root = Package("A")
        self.graph = build_graph(self.root, source.__getitem__)

    def test_dot(self):
        """Сохранить обе связи с общим узлом и обратное ребро цикла."""
        self.prepare_fixture()
        dot = dot_source(self.graph)
        for edge in ['"B" -> "D"', '"C" -> "D"', '"D" -> "A"']:
            self.assertIn(edge, dot)

    def test_ascii(self):
        """Отдельно пометить цикл и общую зависимость."""
        self.prepare_fixture()
        tree = ascii_tree(self.root, self.graph)
        self.assertTrue(tree.isascii())
        self.assertIn("A [cycle]", tree)
        self.assertIn("D [shown]", tree)

    def test_svg_edges_and_labels(self):
        """Сохранить все связи, включая цикл, и все подписи."""
        self.prepare_fixture()
        svg = svg_document(self.graph)
        expected = {
            f"{parent} → {child}"
            for parent, children in self.graph.items()
            for child in children
        }
        self.assertEqual(
            {title.text for title in svg.findall("./g/path/title")}, expected
        )
        self.assertEqual(
            {label.text for label in svg.findall("./g/text")},
            {str(node) for node in self.graph},
        )
        self.assertIsNotNone(svg.find("./g/path[@stroke-dasharray]"))

    def test_nuget_aliases(self):
        """Показать буквы во всех форматах и сохранить полные имена."""
        root = Package("example.root", "1.0.0")
        child = Package("example.child", "1.0.0")
        other_version = Package("example.child", "2.0.0")
        graph = {root: [child, other_version], child: [], other_version: []}
        labels = node_labels(graph)
        self.assertEqual(labels, {root: "A", child: "B", other_version: "C"})
        self.assertEqual(ascii_tree(root, graph), "A\n|-- B\n`-- C")
        self.assertIn('"A" -> "B"', dot_source(graph))
        svg = svg_document(graph)
        self.assertEqual(
            [label.text for label in svg.findall("./g/text")], list("ABC")
        )
        self.assertIn("C = example.child@2.0.0", label_legend(labels))
        self.assertIn("A = example.root@1.0.0", svg.findtext("desc"))

    def test_aliases_after_z(self):
        """Продолжить нумерацию после Z без дублирования подписей."""
        packages = [Package(f"example.{index}", "1.0.0") for index in range(28)]
        labels = list(node_labels(dict.fromkeys(packages)).values())
        self.assertEqual(labels[-3:], ["Z", "AA", "AB"])

    def test_cli_without_graphviz(self):
        """Запустить весь проект с пустым PATH и проверить оба файла."""
        self.prepare_fixture()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test graph.svg"
            command = [
                sys.executable, "-m", "src.main", "--test",
                "--repo", str(FIXTURE.resolve()), "--package", "A",
                "--tree", "--output", str(output),
            ]
            result = subprocess.run(
                command, cwd=FIXTURE.resolve().parents[2],
                env={**os.environ, "PATH": "", "PYTHONIOENCODING": "utf-8"},
                capture_output=True, encoding="utf-8", check=True,
            )
            self.assertIn("A [cycle]", result.stdout)
            self.assertEqual(ElementTree.parse(output).getroot().tag,
                             f"{{{SVG_NAMESPACE}}}svg")
            dot = output.with_suffix(".dot").read_text(encoding="utf-8")
            self.assertEqual(dot, dot_source(self.graph))
