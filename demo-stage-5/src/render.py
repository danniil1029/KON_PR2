"""Вывод ASCII-дерева и экспорт графа в DOT и SVG."""

import json
from pathlib import Path
from string import ascii_uppercase
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

MARGIN = 28
NODE_HEIGHT = 36
ROW_GAP = 30
COLUMN_GAP = 70
FONT_SIZE = 14
CHAR_WIDTH = 9
TEXT_PADDING = 14
EDGE_INSET = 16
LANE_GAP = 20
SVG_NAMESPACE = "http://www.w3.org/2000/svg"


def letter_label(number):
    """Преобразовать порядковый номер в A, B, …, Z, AA, AB, …"""
    letters = []
    while number:
        number, index = divmod(number - 1, len(ascii_uppercase))
        letters.append(ascii_uppercase[index])
    return "".join(reversed(letters))


def node_labels(graph):
    """Присвоить пакетам NuGet буквы в порядке обнаружения BFS."""
    if not any(node.version for node in graph):
        return {node: node.name for node in graph}
    return {
        node: letter_label(number)
        for number, node in enumerate(graph, start=1)
    }


def label_legend(labels):
    """Сопоставить буквенные подписи с полными именами и версиями."""
    return [
        f"{label} = {node}"
        for node, label in labels.items()
        if label != str(node)
    ]


def dot_source(graph, labels=None):
    """Записать все узлы и рёбра графа на языке DOT."""
    if labels is None:
        labels = node_labels(graph)
    lines = [
        "digraph DEPENDENCIES {",
        "  rankdir=LR;",
        '  graph [bgcolor="white", pad=0.25, ranksep=0.45];',
        '  node [shape=box, style="rounded,filled", fontname="Arial",',
        '        fontsize=11, fillcolor="#edf4ff", color="#91a6bf"];',
        '  edge [color="#64748b"];',
    ]
    identifiers = {node: json.dumps(label) for node, label in labels.items()}
    root = next(iter(graph))
    for node, identifier in identifiers.items():
        attributes = [f"tooltip={json.dumps(str(node))}"]
        if node == root:
            attributes.append('fillcolor="#c8e0ff"')
        lines.append(f"  {identifier} [{', '.join(attributes)}];")
    for parent, children in graph.items():
        for child in children:
            lines.append(f"  {identifiers[parent]} -> {identifiers[child]};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def ascii_tree(root, graph, labels=None):
    """Сформировать ASCII-дерево с отметками циклов и повторов."""
    if labels is None:
        labels = node_labels(graph)
    lines = [labels[root]]
    expanded = {root}
    stack = [(iter(graph[root]), len(graph[root]), "", {root})]
    while stack:
        children, remaining, indent, path = stack.pop()
        if not remaining:
            continue
        child = next(children)
        remaining -= 1
        stack.append((children, remaining, indent, path))
        last = not remaining
        branch = "`-- " if last else "|-- "
        label = f"{indent}{branch}{labels[child]}"
        if child in path:
            lines.append(label + " [cycle]")
            continue
        if child in expanded:
            lines.append(label + " [shown]")
            continue
        lines.append(label)
        expanded.add(child)
        next_indent = indent + ("    " if last else "|   ")
        descendants = graph[child]
        stack.append((
            iter(descendants), len(descendants), next_indent, path | {child}
        ))
    return "\n".join(lines)


def graph_columns(graph):
    """Сгруппировать узлы по кратчайшему расстоянию от корня."""
    column = [next(iter(graph))]
    seen = set(column)
    columns = []
    while column:
        columns.append(column)
        next_column = []
        for parent in column:
            for child in graph[parent]:
                if child not in seen:
                    seen.add(child)
                    next_column.append(child)
        column = next_column
    return columns


def layout_nodes(columns, labels):
    """Расположить узлы слева направо и вернуть размеры области графа."""
    row_step = NODE_HEIGHT + ROW_GAP
    height = max(map(len, columns)) * row_step - ROW_GAP
    positions = {}
    x = MARGIN
    for column in columns:
        width = max(len(labels[node]) for node in column)
        width = width * CHAR_WIDTH + 2 * TEXT_PADDING
        column_height = len(column) * row_step - ROW_GAP
        y = MARGIN + (height - column_height) // 2
        for node in column:
            positions[node] = (x, y, width)
            y += row_step
        x += width + COLUMN_GAP
    return positions, x - COLUMN_GAP + MARGIN, height + 2 * MARGIN


def edge_path(parent, child, lane):
    """Провести стрелку между колонками или по нижнему обходному пути."""
    x, y, width = parent
    target_x, target_y, _ = child
    start_x = x + width
    start_y = y + NODE_HEIGHT // 2
    end_y = target_y + NODE_HEIGHT // 2
    if lane is not None:
        right = start_x + EDGE_INSET
        left = target_x - EDGE_INSET
        return (
            f"M {start_x} {start_y} H {right} V {lane} H {left} "
            f"V {end_y} H {target_x}"
        )
    middle = (start_x + target_x) // 2
    return (
        f"M {start_x} {start_y} C {middle} {start_y} {middle} {end_y} "
        f"{target_x} {end_y}"
    )


def draw_edges(svg, graph, positions, first_lane, labels):
    """Нарисовать по одной стрелке для каждого ребра."""
    group = ElementTree.SubElement(svg, "g", {
        "fill": "none", "stroke": "#526680", "stroke-width": "1.5",
        "marker-end": "url(#arrow)",
    })
    lane = first_lane
    for parent, children in graph.items():
        for child in children:
            start = positions[parent]
            end = positions[child]
            back_edge = end[0] <= start[0]
            path = edge_path(start, end, lane if back_edge else None)
            edge = ElementTree.SubElement(group, "path", {"d": path})
            ElementTree.SubElement(edge, "title").text = (
                f"{labels[parent]} → {labels[child]}"
            )
            if back_edge:
                edge.set("stroke-dasharray", "5 3")
                lane += LANE_GAP
    return lane - first_lane


def draw_nodes(svg, positions, root, labels):
    """Нарисовать прямоугольники пакетов и выделить корень."""
    group = ElementTree.SubElement(svg, "g", {
        "font-family": "monospace", "font-size": str(FONT_SIZE),
        "text-anchor": "middle", "dominant-baseline": "central",
    })
    for node, (x, y, width) in positions.items():
        fill = "#c8e0ff" if node == root else "#edf4ff"
        box = ElementTree.SubElement(group, "rect", {
            "x": str(x), "y": str(y), "width": str(width),
            "height": str(NODE_HEIGHT), "rx": "7",
            "fill": fill, "stroke": "#91a6bf",
        })
        ElementTree.SubElement(box, "title").text = str(node)
        label = ElementTree.SubElement(group, "text", {
            "x": str(x + width // 2), "y": str(y + NODE_HEIGHT // 2),
            "fill": "#172638", "pointer-events": "none",
        })
        label.text = labels[node]


def svg_document(graph, labels=None):
    """Построить SVG стандартными средствами Python."""
    if labels is None:
        labels = node_labels(graph)
    columns = graph_columns(graph)
    positions, width, height = layout_nodes(columns, labels)
    svg = ElementTree.Element("svg", {"xmlns": SVG_NAMESPACE})
    ElementTree.SubElement(svg, "title").text = "Граф зависимостей"
    legend = label_legend(labels)
    if legend:
        ElementTree.SubElement(svg, "desc").text = "\n".join(legend)
    definitions = ElementTree.SubElement(svg, "defs")
    marker = ElementTree.SubElement(definitions, "marker", {
        "id": "arrow", "viewBox": "0 0 10 10", "refX": "10", "refY": "5",
        "markerWidth": "6", "markerHeight": "6", "orient": "auto",
    })
    ElementTree.SubElement(marker, "path", {
        "d": "M 0 0 L 10 5 L 0 10 Z", "fill": "#526680",
    })
    ElementTree.SubElement(svg, "rect", {
        "width": "100%", "height": "100%", "fill": "white",
    })
    first_lane = height - MARGIN + LANE_GAP
    height += draw_edges(svg, graph, positions, first_lane, labels)
    draw_nodes(svg, positions, columns[0][0], labels)
    svg.set("width", str(width))
    svg.set("height", str(height))
    svg.set("viewBox", f"0 0 {width} {height}")
    ElementTree.indent(svg, space="  ")
    return svg


def save_graph(graph, output, labels=None):
    """Подготовить SVG и DOT во временной папке, затем сохранить файлы."""
    if labels is None:
        labels = node_labels(graph)
    with TemporaryDirectory(dir=output.parent) as folder:
        svg = Path(folder) / "graph.svg"
        dot = Path(folder) / "graph.dot"
        ElementTree.ElementTree(svg_document(graph, labels)).write(
            svg, encoding="utf-8", xml_declaration=True
        )
        dot.write_text(dot_source(graph, labels), encoding="utf-8")
        dot.replace(output.with_suffix(".dot"))
        svg.replace(output)
