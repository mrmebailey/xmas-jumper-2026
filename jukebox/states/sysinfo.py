import threading

import pygame

from .. import config
from ..sysinfo import SystemInfo
from ..widgets import Button, draw_text, fit_text, render_text
from .base import State

LEFT = 20
VALUE_X = 140
ROW_TOP = 82
ROW_H = 28
QR_X = config.SCREEN_W - 20 - config.QR_CODE_SIZE
QR_Y = 82


class SysInfoState(State):
    """System details on the left, the QR code on the right. The details are
    gathered on a background thread (some come from running commands) so the
    screen never stalls waiting for them."""

    def __init__(self, app):
        super().__init__(app)
        self._qr = None
        try:
            image = pygame.image.load(str(config.QR_CODE_FILE)).convert()
            # Plain scale (no smoothing) keeps the squares sharp for scanning.
            self._qr = pygame.transform.scale(image, (config.QR_CODE_SIZE, config.QR_CODE_SIZE))
        except (pygame.error, FileNotFoundError):
            pass
        self._info = SystemInfo()
        self._stop = threading.Event()
        self._thread = None
        self.rows = []

    def on_enter(self):
        app = self.app
        self.buttons = [
            Button((QR_X, 395, config.QR_CODE_SIZE, 70), "Back", lambda: app.change_state("menu"), app.font_medium),
        ]
        self.rows = [(label, "...") for label, _ in self.rows] or [("Reading", "...")]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._refresh_loop, args=(self._stop,), daemon=True)
        self._thread.start()

    def on_exit(self):
        self._stop.set()

    def _refresh_loop(self, stop):
        while not stop.is_set():
            try:
                rows = self._info.read()
            except Exception as e:  # never let a bad reading kill the thread silently
                rows = [("Error", str(e))]
            if not stop.is_set():
                self.rows = rows
            stop.wait(config.SYSINFO_REFRESH_MS / 1000)

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def draw(self, surface):
        self.draw_background(surface, "System Info")
        font = self.app.font_tiny
        value_w = QR_X - 20 - VALUE_X
        for i, (label, value) in enumerate(self.rows):
            y = ROW_TOP + i * ROW_H
            surface.blit(render_text(font, label, config.TITLE_COLOR), (LEFT, y))
            surface.blit(fit_text(font, value, value_w), (VALUE_X, y))
        if config.FRONTIER_FINDINGS:
            # Its own highlighted line under the details, boxed in red.
            y = ROW_TOP + len(self.rows) * ROW_H + 8
            label = render_text(font, "Frontier Findings", config.TITLE_COLOR)
            value_x = LEFT + label.get_width() + 14
            value = fit_text(font, config.FRONTIER_FINDINGS, QR_X - 26 - value_x, config.WARNING_COLOR)
            box = pygame.Rect(LEFT - 8, y - 6, value_x + value.get_width() + 8 - (LEFT - 8), font.get_linesize() + 10)
            pygame.draw.rect(surface, config.WARNING_COLOR, box, width=2, border_radius=6)
            surface.blit(label, (LEFT, y))
            surface.blit(value, (value_x, y))
        if self._qr is not None:
            pygame.draw.rect(surface, (255, 255, 255), (QR_X - 6, QR_Y - 6, config.QR_CODE_SIZE + 12,
                                                        config.QR_CODE_SIZE + 12), border_radius=6)
            surface.blit(self._qr, (QR_X, QR_Y))
            draw_text(surface, "Scan me!", self.app.font_small, QR_X + config.QR_CODE_SIZE // 2,
                      QR_Y + config.QR_CODE_SIZE + 16, config.QR_CODE_SIZE + 20, config.TITLE_COLOR)
        else:
            draw_text(surface, "No qr-code.png", font, QR_X + config.QR_CODE_SIZE // 2, QR_Y + 90,
                      config.QR_CODE_SIZE)
        for button in self.buttons:
            button.draw(surface)
