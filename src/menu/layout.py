"""环形菜单的纯几何排版：保证相邻按钮不重叠，整组按钮位于工作区内。"""

import math


def radial_layout(center, bounds, count, scale=1.0, base_size=70):
    """返回实际缩放与 (左上 x, 左上 y, 角度) 列表，坐标相对菜单窗口。

    对上、下、左、右四种半圆分别计算；优先保留大小，再选择移动最少的
    方案。靠角落时平移整组菜单，避免把很多按钮硬塞进四分之一圆造成重叠。
    """
    if count <= 0:
        return scale, []
    width, height = bounds
    requested = max(0.4, min(4.0, float(scale)))
    candidates = []
    for start, sweep in ((math.pi, -math.pi), (math.pi, math.pi),
                         (math.pi / 2, -math.pi), (math.pi / 2, math.pi)):
        angles = [math.pi / 2] if count == 1 else [start + sweep * i / (count - 1) for i in range(count)]
        radius = 120 if count <= 1 else max(120, (base_size + 14) / (2 * math.sin(math.pi / (2 * (count - 1)))))
        raw = [(radius * math.cos(a), -radius * math.sin(a)) for a in angles]
        min_x, max_x = min(x for x, y in raw), max(x for x, y in raw)
        min_y, max_y = min(y for x, y in raw), max(y for x, y in raw)
        actual = min(requested, (width - 24) / (max_x - min_x + base_size),
                     (height - 24) / (max_y - min_y + base_size))
        actual = max(0.1, actual)
        half = base_size * actual / 2
        left = center[0] + min_x * actual - half
        right = center[0] + max_x * actual + half
        top = center[1] + min_y * actual - half
        bottom = center[1] + max_y * actual + half
        dx = max(12 - left, min(0, width - 12 - right))
        dy = max(12 - top, min(0, height - 12 - bottom))
        score = (requested - actual) * 10000 + abs(dx) + abs(dy)
        positions = [(center[0] + x * actual - half + dx,
                      center[1] + y * actual - half + dy, angle)
                     for (x, y), angle in zip(raw, angles)]
        candidates.append((score, actual, positions))
    _, actual, positions = min(candidates, key=lambda item: item[0])
    return actual, positions
