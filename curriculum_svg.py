"""
Parses the vector (SVG) version of the Adaptive Curricula diagram and provides
a function to produce a filtered copy of it, showing/hiding specific exercise
nodes and the arrows (edges) connecting them.

The source SVG (exported from the diagramming tool) has no element IDs, so
nodes and edges are identified purely from geometry:

  - Each exercise NODE is drawn as a single <path> tracing a circle (4 cubic
    Bezier curves -> 26 numeric values in "d"), with a solid pastel fill.
    A separate <text> element (positioned via a translate() transform) holds
    the node's abbreviation label.

  - Each EDGE (arrow) is drawn as a single <path> containing a curve subpath
    (its start point sits on the source node's boundary) followed by a small
    triangular arrowhead subpath (whose centroid sits on the destination
    node's boundary).

Usage:
    from curriculum_svg import CurriculumDiagram

    diagram = CurriculumDiagram(SVG_PATH)
    svg_text = diagram.build_filtered_svg(visible_nodes={"pnp", "pb1", "pb2"})
    with open("out.svg", "w", encoding="utf-8") as f:
        f.write(svg_text)
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

_SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", _SVG_NS)

_NUM_RE = re.compile(r"-?\d+\.?\d*")
_TRANSFORM_RE = re.compile(r"(translate|matrix)\(([^)]+)\)", re.IGNORECASE)


def _parse_transform(transform: str | None) -> tuple[float, float, float, float, float, float]:
    """Parse an SVG transform attribute into matrix coefficients (a,b,c,d,e,f)."""
    if not transform:
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    s = transform.strip()
    m = _TRANSFORM_RE.search(s)
    if not m:
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    kind, body = m.group(1).lower(), m.group(2).strip()
    parts = [float(x) for x in re.split(r"[,\s]+", body) if x]
    if kind == "translate":
        tx = parts[0] if len(parts) > 0 else 0.0
        ty = parts[1] if len(parts) > 1 else 0.0
        return (1.0, 0.0, 0.0, 1.0, tx, ty)
    if kind == "matrix" and len(parts) == 6:
        return (parts[0], parts[1], parts[2], parts[3], parts[4], parts[5])
    return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _apply_transform(
    x: float,
    y: float,
    a: float,
    b: float,
    c: float,
    d: float,
    e: float,
    f: float,
) -> tuple[float, float]:
    return (a * x + c * y + e, b * x + d * y + f)


def _tag(el: ET.Element) -> str:
    return el.tag.split("}")[-1]


@dataclass
class _Node:
    abbreviation: str
    cx: float
    cy: float
    r: float
    circle_el: ET.Element
    text_el: ET.Element


@dataclass
class _Edge:
    src: str
    dst: str
    fit_score: float  # combined match confidence (lower = better); for diagnostics
    path_el: ET.Element


@dataclass
class CurriculumDiagram:
    svg_path: str
    tree: ET.ElementTree = field(init=False, repr=False)
    root: ET.Element = field(init=False, repr=False)
    nodes: dict[str, _Node] = field(init=False, default_factory=dict)
    edges: list[_Edge] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self.tree = ET.parse(self.svg_path)
        self.root = self.tree.getroot()
        self._parse()

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def _all_paths(self) -> list[ET.Element]:
        return [el for el in self.root.iter() if _tag(el) == "path"]

    @staticmethod
    def _bbox(nums: list[float]) -> tuple[float, float, float, float]:
        xs = nums[0::2]
        ys = nums[1::2]
        return min(xs), min(ys), max(xs), max(ys)

    def _is_node_circle(self, nums: list[float], fill: str) -> tuple[float, float, float] | None:
        """Return (cx, cy, r) if this path's numbers describe a node circle."""
        if len(nums) != 26 or fill == "none":
            return None
        x0, y0, x1, y1 = self._bbox(nums)
        w, h = x1 - x0, y1 - y0
        if h <= 0 or not (0.85 < w / h < 1.18):
            return None
        return (x0 + x1) / 2, (y0 + y1) / 2, w / 2

    def _normalize_text_element(self, text_el: ET.Element, tx: float, ty: float) -> None:
        """Rewrite the text element so its final position comes from a plain
        translate() on the text node itself, with no per-tspan x/y offsets.

        Qt's SVG renderer does not reliably honour `x`/`y` on `<tspan>`, which
        can cause every label to collapse to the text origin.  Moving the
        position into the text transform keeps the SVG valid for both browsers
        and Qt.
        """
        text_el.set("transform", f"translate({tx:.3f} {ty:.3f})")
        for attr in ("x", "y"):
            if attr in text_el.attrib:
                del text_el.attrib[attr]
        for child in text_el:
            if _tag(child) == "tspan":
                for attr in ("x", "y"):
                    if attr in child.attrib:
                        del child.attrib[attr]

    def _parse(self) -> None:
        paths = self._all_paths()

        # 1) Node circles
        circle_paths: list[tuple[ET.Element, float, float, float]] = []
        for el in paths:
            nums = [float(x) for x in _NUM_RE.findall(el.get("d", ""))]
            if not nums:
                continue
            circ = self._is_node_circle(nums, el.get("fill", ""))
            if circ is not None:
                cx, cy, r = circ
                tf = _parse_transform(el.get("transform"))
                cx, cy = _apply_transform(cx, cy, *tf)
                circle_paths.append((el, cx, cy, r))

        # 2) Text labels -> nearest unused circle
        texts: list[tuple[str, float, float, float, ET.Element]] = []
        for el in self.root.iter():
            if _tag(el) != "text":
                continue
            label = "".join(el.itertext()).strip()
            if not label:
                continue
            fs = float(el.get("font-size", "20"))
            tf = _parse_transform(el.get("transform"))

            # Prefer tspan position; fall back to the text element itself
            pos_el = el
            for child in el:
                if _tag(child) == "tspan":
                    pos_el = child
                    break
            x_str = pos_el.get("x", "0")
            y_str = pos_el.get("y", "0")

            def _first_float(s: str) -> float:
                m = _NUM_RE.search(s)
                return float(m.group(0)) if m else 0.0

            tx_local = _first_float(x_str)
            ty_local = _first_float(y_str)
            tx, ty = _apply_transform(tx_local, ty_local, *tf)
            texts.append((label, tx, ty, fs, el))

        used: set[int] = set()
        for label, tx, ty, fs, text_el in texts:
            approx_cx = tx + len(label) * fs * 0.28
            approx_cy = ty - fs * 0.32
            best_i, best_d = None, float("inf")
            for i, (_el, cx, cy, _r) in enumerate(circle_paths):
                if i in used:
                    continue
                d = (cx - approx_cx) ** 2 + (cy - approx_cy) ** 2
                if d < best_d:
                    best_d, best_i = d, i
            if best_i is None:
                continue
            used.add(best_i)
            circle_el, cx, cy, r = circle_paths[best_i]
            self._normalize_text_element(text_el, tx, ty)
            self.nodes[label] = _Node(label, cx, cy, r, circle_el, text_el)

        # 3) Edges: every other colored path
        node_circle_ids = {id(n.circle_el) for n in self.nodes.values()}
        for el in paths:
            if id(el) in node_circle_ids:
                continue
            fill = el.get("fill", "")
            stroke = el.get("stroke", "")
            if fill == "none" and not stroke:
                continue  # stray non-drawing artifact (no fill AND no stroke)
            d = el.get("d", "")
            nums = [float(x) for x in _NUM_RE.findall(d)]
            if not nums:
                continue

            subpaths = [sp for sp in re.split(r"(?=M)", d) if sp.strip()]
            sub_pts: list[list[tuple[float, float]]] = []
            for sp in subpaths:
                n = [float(x) for x in _NUM_RE.findall(sp)]
                sub_pts.append(list(zip(n[0::2], n[1::2])))
            if not sub_pts or not sub_pts[0]:
                continue

            start = sub_pts[0][0]
            if len(sub_pts) >= 2 and len(sub_pts[-1]) >= 2:
                ah = sub_pts[-1]
                end = (sum(p[0] for p in ah) / len(ah), sum(p[1] for p in ah) / len(ah))
            else:
                end = sub_pts[0][-1]

            tf = _parse_transform(el.get("transform"))
            start = _apply_transform(start[0], start[1], *tf)
            end = _apply_transform(end[0], end[1], *tf)

            src, s_score = self._nearest_node(*start)
            dst, d_score = self._nearest_node(*end)
            if src is None or dst is None:
                continue
            self.edges.append(_Edge(src, dst, s_score + d_score, el))

    def _nearest_node(self, px: float, py: float) -> tuple[str | None, float]:
        best_abb, best_score = None, float("inf")
        for abb, node in self.nodes.items():
            dist = ((node.cx - px) ** 2 + (node.cy - py) ** 2) ** 0.5
            score = abs(dist - node.r)
            if score < best_score:
                best_score, best_abb = score, abb
        return best_abb, best_score

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------
    def _fresh_copy(self) -> "CurriculumDiagram":
        """Re-parse the SVG from disk into a brand-new tree/element set, so the
        original (self) instance is left untouched and can be reused for
        further renders."""
        tree = ET.parse(self.svg_path)
        root = tree.getroot()
        fresh = CurriculumDiagram.__new__(CurriculumDiagram)
        fresh.svg_path = self.svg_path
        fresh.tree = tree
        fresh.root = root
        fresh.nodes = {}
        fresh.edges = []
        fresh._parse()
        return fresh

    @staticmethod
    def _remove_elements(root: ET.Element, elements: list[ET.Element]) -> None:
        # Removing elements outright (rather than setting display="none") is
        # used because QSvgRenderer (Qt) does not reliably honor the SVG
        # "display" presentation attribute.
        parent_map = {child: parent for parent in root.iter() for child in parent}
        for el in elements:
            parent = parent_map.get(el)
            if parent is not None:
                try:
                    parent.remove(el)
                except ValueError:
                    pass

    def build_filtered_svg(
        self,
        visible_nodes: set[str],
        edge_rule: str = "both_visible",
    ) -> str:
        """Return SVG markup with only the given nodes (and their labels) shown.

        edge_rule:
            "both_visible"  - show an edge only if BOTH endpoints are visible (default)
            "either_visible" - show an edge if AT LEAST ONE endpoint is visible
        """
        fresh = self._fresh_copy()
        to_remove: list[ET.Element] = []

        for abb, node in fresh.nodes.items():
            if abb not in visible_nodes:
                to_remove.extend((node.circle_el, node.text_el))

        for edge in fresh.edges:
            src_visible = edge.src in visible_nodes
            dst_visible = edge.dst in visible_nodes
            show = (src_visible and dst_visible) if edge_rule == "both_visible" else (src_visible or dst_visible)
            if not show:
                to_remove.append(edge.path_el)

        self._remove_elements(fresh.root, to_remove)
        return ET.tostring(fresh.root, encoding="unicode")

    def build_progress_svg(self, path_sequence: list[str]) -> str:
        """Return SVG markup for an ordered curriculum path.

        Every exercise in `path_sequence` is shown, but only the single edge
        connecting each exercise to the exercise immediately BEFORE it in the
        sequence is shown (i.e. the actual traversed connection) — not every
        edge that happens to connect two visible nodes.
        """
        fresh = self._fresh_copy()
        visible_nodes = set(path_sequence)
        # Use unordered pairs: some connections (e.g. lateral moves) are
        # logically traversable in either direction, but the SVG artwork
        # only draws a single arrow for the pair. We still want to show
        # that arrow regardless of which direction the subject moved.
        traversed_pairs = {
            frozenset((path_sequence[i], path_sequence[i + 1])) for i in range(len(path_sequence) - 1)
        }

        to_remove: list[ET.Element] = []
        for abb, node in fresh.nodes.items():
            if abb not in visible_nodes:
                to_remove.extend((node.circle_el, node.text_el))

        for edge in fresh.edges:
            if frozenset((edge.src, edge.dst)) not in traversed_pairs:
                to_remove.append(edge.path_el)

        self._remove_elements(fresh.root, to_remove)
        return ET.tostring(fresh.root, encoding="unicode")

    def node_abbreviations(self) -> list[str]:
        return sorted(self.nodes.keys())
