from datetime import datetime

import pygame

from .. import config, naughty_list
from ..games import sprites
from ..photos import load_for_screen
from ..widgets import Button, draw_text, fit_text, render_text
from .base import State

LIST_TOP, LIST_BOTTOM = 77, 377
ROW_H = 60
THUMB = (40, 52)
BIG_PHOTO = (285, 380)
DRAG_PX = 12
NAUGHTY_RED = (255, 90, 90)


def _when(entry):
    return datetime.fromtimestamp(entry["time"]).strftime("%-d %b, %H:%M")


class NaughtyListState(State):
    """Everyone the scanner found naughty, naughtiest first. Drag or use
    Up/Down to scroll; tap someone to see their photo big."""

    def on_enter(self):
        app = self.app
        self.list_buttons = [
            Button((20, 385, 140, 75), "Up", lambda: self._page(-1), app.font_medium),
            Button((170, 385, 140, 75), "Down", lambda: self._page(1), app.font_medium),
            Button((500, 385, 120, 75), "Back", lambda: app.change_state("naughty"), app.font_medium),
        ]
        self.close_button = Button((500, 385, 120, 75), "Back", self._close, app.font_medium)
        self.entries = naughty_list.ranked()
        self.scroll = 0
        self.selected = None  # index into entries when showing one big
        self.big = None
        self._drag = None
        self._thumbs = {}

    def _close(self):
        self.selected = None
        self.big = None

    def _max_scroll(self):
        return max(0, len(self.entries) * ROW_H - (LIST_BOTTOM - LIST_TOP))

    def _page(self, direction):
        self.scroll = max(0, min(self._max_scroll(), self.scroll + direction * 4 * ROW_H))

    def _path(self, entry):
        return config.PHOTOS_DIR / entry["photo"]

    def _thumb(self, entry):
        thumb = self._thumbs.get(entry["photo"])
        if thumb is None:
            try:
                thumb = load_for_screen(self._path(entry), THUMB)
            except (pygame.error, OSError):
                thumb = False
            self._thumbs[entry["photo"]] = thumb
        return thumb or None

    def handle_event(self, event):
        if self.selected is not None:
            self.close_button.handle_event(event)
            return
        for button in self.list_buttons:
            button.handle_event(event)
        in_list = hasattr(event, "pos") and LIST_TOP <= event.pos[1] < LIST_BOTTOM
        if event.type == pygame.MOUSEBUTTONDOWN and in_list:
            self._drag = (event.pos[1], self.scroll, False)
        elif event.type == pygame.MOUSEMOTION and self._drag is not None:
            start_y, start_scroll, moved = self._drag
            dy = event.pos[1] - start_y
            if moved or abs(dy) > DRAG_PX:
                self._drag = (start_y, start_scroll, True)
                self.scroll = max(0, min(self._max_scroll(), start_scroll - dy))
        elif event.type == pygame.MOUSEBUTTONUP and self._drag is not None:
            moved = self._drag[2]
            self._drag = None
            if not moved and in_list:
                index = (event.pos[1] - LIST_TOP + self.scroll) // ROW_H
                if 0 <= index < len(self.entries):
                    self.selected = index
                    try:
                        self.big = load_for_screen(self._path(self.entries[index]), BIG_PHOTO)
                    except (pygame.error, OSError):
                        self.big = None

    def draw(self, surface):
        if self.selected is not None:
            self._draw_one(surface)
            return
        self.draw_background(surface, "The Naughty List")
        if not self.entries:
            y = draw_text(surface, "Nobody's on the Naughty List yet!", self.app.font_medium,
                          config.SCREEN_W // 2, 150, config.SCREEN_W - 60, config.TITLE_COLOR)
            draw_text(surface, "Everyone's been good... so far. Scan someone to find out!",
                      self.app.font_small, config.SCREEN_W // 2, y + 16, config.SCREEN_W - 80)
        surface.set_clip(pygame.Rect(0, LIST_TOP, config.SCREEN_W, LIST_BOTTOM - LIST_TOP))
        first = self.scroll // ROW_H
        last = min(len(self.entries), (self.scroll + LIST_BOTTOM - LIST_TOP) // ROW_H + 1)
        for index in range(first, last):
            entry = self.entries[index]
            top = LIST_TOP + index * ROW_H - self.scroll
            row = pygame.Rect(10, top + 2, config.SCREEN_W - 20, ROW_H - 4)
            pygame.draw.rect(surface, (110, 25, 25) if index == 0 else (35, 35, 40), row, border_radius=8)
            rank = render_text(self.app.font_medium, f"#{index + 1}", config.TITLE_COLOR)
            surface.blit(rank, rank.get_rect(midleft=(row.x + 10, row.centery)))
            thumb = self._thumb(entry)
            thumb_x = row.x + 80
            if thumb is not None:
                surface.blit(thumb, thumb.get_rect(midleft=(thumb_x, row.centery)))
            text_x = thumb_x + THUMB[0] + 16
            surface.blit(fit_text(self.app.font_small, f"{entry['score']}% naughty", 260, NAUGHTY_RED),
                         (text_x, row.y + 6))
            surface.blit(render_text(self.app.font_tiny, _when(entry)), (text_x, row.y + 32))
            if index == 0:
                coal = sprites.get("coal", 44)
                surface.blit(coal, coal.get_rect(midright=(row.right - 12, row.centery)))
        surface.set_clip(None)
        for button in self.list_buttons:
            button.draw(surface)

    def _draw_one(self, surface):
        self.draw_background(surface)
        entry = self.entries[self.selected]
        box = pygame.Rect(20, 30, *BIG_PHOTO)
        if self.big is not None:
            surface.blit(self.big, self.big.get_rect(center=box.center))
        text_x = (box.right + config.SCREEN_W) // 2
        place = "Naughtiest of all!" if self.selected == 0 else f"Number {self.selected + 1}"
        y = draw_text(surface, f"#{self.selected + 1}", self.app.font_title,
                      text_x, 70, 300, config.TITLE_COLOR)
        y = draw_text(surface, place, self.app.font_medium, text_x, y + 6, 300)
        y = draw_text(surface, f"{entry['score']}% naughty", self.app.font_large, text_x, y + 16, 300, NAUGHTY_RED)
        draw_text(surface, _when(entry), self.app.font_small, text_x, y + 12, 300)
        self.close_button.draw(surface)
