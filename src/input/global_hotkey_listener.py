from __future__ import annotations

import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal


class GlobalInputBridge(QObject):
    toggle_requested = pyqtSignal(str)
    listener_error = pyqtSignal(str)

    def __init__(self, hold_ms: int = 1000, parent=None):
        super().__init__(parent)
        self.hold_seconds = max(0.2, float(hold_ms) / 1000.0)

        self._lock = threading.Lock()
        self._space_pressed = False
        self._space_triggered = False
        self._space_pressed_at = 0.0
        self._space_timer = None

        self._keyboard_mod = None
        self._mouse_mod = None
        self._keyboard_listener = None
        self._mouse_listener = None
        self._running = False

    def start(self) -> bool:
        if self._running:
            return True

        try:
            from pynput import keyboard, mouse
        except Exception as exc:
            self.listener_error.emit(f"全局输入监听初始化失败：{exc}")
            return False

        self._keyboard_mod = keyboard
        self._mouse_mod = mouse

        try:
            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release,
                suppress=False,
            )
            self._mouse_listener = mouse.Listener(
                on_click=self._on_mouse_click,
                suppress=False,
            )

            self._keyboard_listener.start()
            self._mouse_listener.start()
        except Exception as exc:
            self.listener_error.emit(f"全局输入监听启动失败：{exc}")
            self.stop()
            return False

        self._running = True
        return True

    def stop(self):
        self._running = False
        self._cancel_space_timer()

        listeners = [self._keyboard_listener, self._mouse_listener]
        self._keyboard_listener = None
        self._mouse_listener = None

        for listener in listeners:
            if listener is None:
                continue
            try:
                listener.stop()
            except Exception:
                pass

        with self._lock:
            self._space_pressed = False
            self._space_triggered = False
            self._space_pressed_at = 0.0

    def _on_key_press(self, key):
        if not self._is_space_key(key):
            return

        with self._lock:
            if self._space_pressed:
                return
            self._space_pressed = True
            self._space_triggered = False
            self._space_pressed_at = time.monotonic()

        self._cancel_space_timer()
        timer = threading.Timer(self.hold_seconds, self._on_space_hold_timeout)
        timer.daemon = True
        self._space_timer = timer
        timer.start()

    def _on_key_release(self, key):
        if not self._is_space_key(key):
            return

        self._cancel_space_timer()

        with self._lock:
            self._space_pressed = False
            self._space_triggered = False
            self._space_pressed_at = 0.0

    def _on_space_hold_timeout(self):
        with self._lock:
            if not self._space_pressed or self._space_triggered:
                return

            held = time.monotonic() - self._space_pressed_at
            if held < self.hold_seconds:
                return

            self._space_triggered = True

        self.toggle_requested.emit("space_hold")

    def _on_mouse_click(self, _x, _y, button, pressed):
        if not pressed:
            return

        mouse_mod = self._mouse_mod
        if mouse_mod is None:
            return

        if button == mouse_mod.Button.middle:
            self.toggle_requested.emit("middle_click")

    def _is_space_key(self, key) -> bool:
        keyboard_mod = self._keyboard_mod
        if keyboard_mod is None:
            return False
        return key == keyboard_mod.Key.space

    def _cancel_space_timer(self):
        timer = self._space_timer
        self._space_timer = None
        if timer is None:
            return
        try:
            timer.cancel()
        except Exception:
            pass
