"""环形菜单的纯几何排版：圆心固定在桌宠，只调整展开方向、弧度和缩放。"""

import math


_SCREEN_PADDING = 12
_MIN_SCALE = 0.4
# 沿用旧菜单的方向与阅读顺序：上/下从左到右，左/右从上到下。
# 四个对角方向用于靠近角落时向屏幕内部展开。
_DIRECTIONS = (
    (math.pi / 2, -1), (3 * math.pi / 2, 1),
    (0, -1), (math.pi, 1),
    (math.pi / 4, -1), (3 * math.pi / 4, 1),
    (-math.pi / 4, -1), (5 * math.pi / 4, 1),
)


def _fitting_scale(center, bounds, extents, requested):
    """求固定圆心下的缩放区间；不能通过平移按钮来修正越界。

    每个边界都满足 padding <= 圆心 + 偏移 * scale <= 屏幕边界。
    圆心恰好贴边时还存在缩放下限，不能只按菜单包围盒的宽高缩小。
    """
    minimum, maximum = 0.0, requested
    for origin, length, offsets in zip(center, bounds, extents):
        for offset in offsets:
            if abs(offset) < 1e-9:
                if not _SCREEN_PADDING <= origin <= length - _SCREEN_PADDING:
                    return None
                continue
            limits = sorted(((_SCREEN_PADDING - origin) / offset,
                             (length - _SCREEN_PADDING - origin) / offset))
            minimum = max(minimum, limits[0])
            maximum = min(maximum, limits[1])
            if maximum < minimum:
                return None
    return maximum if maximum >= _MIN_SCALE else None


def radial_layout(center, bounds, count, scale=1.0, base_size=70):
    """返回实际缩放与 (左上 x, 左上 y, 角度) 列表，使用菜单窗口局部坐标。

    优先保留按钮大小，再选择半径最小的可见扇形。靠边改向、靠角收拢
    扇形并增大半径，空间不足才缩小按钮；所有按钮始终共用桌宠圆心。
    """
    if count <= 0:
        return scale, []
    requested = max(_MIN_SCALE, min(4.0, float(scale)))
    best = None
    fallback = None
    half = base_size / 2
    # 2° 的有限搜索兼顾边角空间与布局速度，不依赖 Qt 或像素逐点试探。
    sweeps = (180,) if count == 1 else range(180, 19, -2)
    for degrees in sweeps:
        sweep = math.radians(degrees)
        # 用相邻按钮的弦长留出间隙，避免旧版四分之一圆内的按钮相互遮挡。
        radius = 120 if count == 1 else max(
            120, (base_size + 14) / (2 * math.sin(sweep / (2 * (count - 1))))
        )
        for direction, (middle, order) in enumerate(_DIRECTIONS):
            angles = [middle] if count == 1 else [
                middle + order * (sweep * i / (count - 1) - sweep / 2)
                for i in range(count)
            ]
            raw = [(radius * math.cos(a), -radius * math.sin(a)) for a in angles]
            extents = tuple((min(p[axis] for p in raw) - half,
                             max(p[axis] for p in raw) + half) for axis in (0, 1))
            actual = _fitting_scale(center, bounds, extents, requested)
            if actual is not None:
                score = (-actual, radius, direction)
                if best is None or score < best[0]:
                    best = (score, actual, raw, angles)
            else:
                # 极小工作区无法容纳最小按钮时，保留可点击尺寸与固定圆心，
                # 选择越界最少的扇形；绝不返回低于按钮实际下限的虚假缩放。
                overflow = sum(
                    max(0, _SCREEN_PADDING - (origin + offsets[0] * _MIN_SCALE))
                    + max(0, origin + offsets[1] * _MIN_SCALE - (length - _SCREEN_PADDING))
                    for origin, length, offsets in zip(center, bounds, extents)
                )
                score = (overflow, radius, direction)
                if fallback is None or score < fallback[0]:
                    fallback = (score, _MIN_SCALE, raw, angles)

    _, actual, raw, angles = best if best is not None else fallback
    positions = [(center[0] + x * actual - half * actual,
                  center[1] + y * actual - half * actual, angle)
                 for (x, y), angle in zip(raw, angles)]
    return actual, positions
