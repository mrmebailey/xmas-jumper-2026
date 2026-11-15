import pygame

from .. import art, config
from ..widgets import Button, fit_text
from .base import State

LIST_TOP, LIST_BOTTOM = 77, 377
ROW_H = 60
THUMB = 52
DRAG_PX = 12  # a touch that moves further than this scrolls instead of picking


class SongsState(State):
    """Every song in a scrolling list with its cover: drag or use Up/Down to
    scroll, tap a song to play it."""

    def on_enter(self):
        app = self.app
        self.buttons = [
            Button((20, 385, 140, 75), "Up", lambda: self._page(-1), app.font_medium),
            Button((170, 385, 140, 75), "Down", lambda: self._page(1), app.font_medium),
            Button((510, 385, 110, 75), "Back", lambda: app.change_state("music"), app.font_medium),
        ]
        self._drag = None  # (start y, scroll at start, moved?)
        # Open with the current song in view, near the top.
        self.scroll = self._clamp((self.app.audio.track_index - 1) * ROW_H)

    def _max_scroll(self):
        return max(0, len(self.app.audio.playlist) * ROW_H - (LIST_BOTTOM - LIST_TOP))

    def _clamp(self, scroll):
        return max(0, min(self._max_scroll(), scroll))

    def _page(self, direction):
        self.scroll = self._clamp(self.scroll + direction * 4 * ROW_H)

    def _in_list(self, pos):
        return LIST_TOP <= pos[1] < LIST_BOTTOM

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and self._in_list(event.pos):
            self._drag = (event.pos[1], self.scroll, False)
        elif event.type == pygame.MOUSEMOTION and self._drag is not None:
            start_y, start_scroll, moved = self._drag
            dy = event.pos[1] - start_y
            if moved or abs(dy) > DRAG_PX:
                self._drag = (start_y, start_scroll, True)
                self.scroll = self._clamp(start_scroll - dy)
        elif event.type == pygame.MOUSEBUTTONUP and self._drag is not None:
            moved = self._drag[2]
            self._drag = None
            if not moved and self._in_list(event.pos):
                index = (event.pos[1] - LIST_TOP + self.scroll) // ROW_H
                if 0 <= index < len(self.app.audio.playlist):
                    self.app.audio.play_track(index)
                    self.app.change_state("music")

    def draw(self, surface):
        self.draw_background(surface, "Pick a Song")
        audio = self.app.audio
        playlist = audio.playlist
        if not playlist:
            text = fit_text(self.app.font_medium, "No music found", config.SCREEN_W - 40)
            surface.blit(text, text.get_rect(center=(config.SCREEN_W // 2, 200)))
        surface.set_clip(pygame.Rect(0, LIST_TOP, config.SCREEN_W, LIST_BOTTOM - LIST_TOP))
        first = self.scroll // ROW_H
        last = min(len(playlist), (self.scroll + LIST_BOTTOM - LIST_TOP) // ROW_H + 1)
        for index in range(first, last):
            track = playlist[index]
            top = LIST_TOP + index * ROW_H - self.scroll
            row = pygame.Rect(10, top + 2, config.SCREEN_W - 20, ROW_H - 4)
            if index == audio.track_index:
                pygame.draw.rect(surface, config.ACCENT_COLOR, row, border_radius=8)
            cover = art.cover(track.path, THUMB)
            thumb_pos = (row.x + 4, row.centery - THUMB // 2)
            if cover is not None:
                surface.blit(cover, thumb_pos)
            else:
                surface.fill(config.BUTTON_COLOR, (*thumb_pos, THUMB, THUMB))
            text_x = row.x + THUMB + 16
            width = row.right - text_x - 8
            surface.blit(fit_text(self.app.font_small, track.title, width), (text_x, row.y + 6))
            surface.blit(fit_text(self.app.font_tiny, track.artist, width, config.TITLE_COLOR),
                         (text_x, row.y + 32))
        surface.set_clip(None)
        for button in self.buttons:
            button.draw(surface)
