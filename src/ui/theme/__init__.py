"""维维美主题公共入口：窗口只引用语义颜色，不自行维护调色板。"""

import sys
from dataclasses import asdict, dataclass
from string import Template

from src.config import ConfigError, load_dialog_theme as _load_dialog_theme


@dataclass(frozen=True)
class Palette:
    """取自角色的银发、黑衣、红饰带与琥珀眼睛；强调色只用于重点。"""

    canvas: str = "#F2F1EF"
    surface: str = "#FCFBF9"
    inset: str = "#EAE8E5"
    line: str = "#D9D5D1"
    ink: str = "#262527"
    muted: str = "#716B6C"
    faint: str = "#ABA4A2"
    charcoal: str = "#29272B"
    charcoal_hover: str = "#3B353B"
    accent: str = "#982D3D"
    accent_hover: str = "#B43B4E"
    accent_pressed: str = "#792131"
    accent_soft: str = "#F2E3E5"
    amber: str = "#94631B"
    amber_soft: str = "#F5ECD9"
    completed: str = "#777176"
    completed_bg: str = "#E9E6E8"
    weekend: str = "#8b0000"
    white: str = "#FFFFFF"


P = Palette()


def default_ui_font_family():
    if sys.platform == "darwin":
        return "PingFang SC"
    if sys.platform == "win32":
        return "Microsoft YaHei"
    return "Noto Sans CJK SC"


def qss(source, **values):
    """用固定色值替换 QSS 占位符；不把用户输入插入样式表。"""
    return Template(source).substitute(asdict(P), font=default_ui_font_family(), **values)


def load_dialog_theme():
    """所有界面统一读取配置；错误时使用可用的默认主题。"""
    try:
        return _load_dialog_theme()
    except ConfigError as error:
        print(f"读取 dialog_style.yaml 失败: {error}")
        return {}
