from .. import art, config
from ..widgets import Button, Slider, draw_text, render_text
from .base import State

ART_SIZE = 200


class MusicState(State):
    def on_enter(self):
        app = self.app
        audio = app.audio
        self.play_button = Button((20, 385, 120, 75), "Play", audio.play_pause, app.font_medium)
        self.shuffle_button = Button((250, 215, 210, 55), "", audio.toggle_shuffle, app.font_small)
        self.buttons = [
            self.play_button,
            Button((150, 385, 100, 75), "Prev", audio.prev_track, app.font_medium),
            Button((260, 385, 100, 75), "Next", audio.next_track, app.font_medium),
            Button((370, 385, 130, 75), "Songs", lambda: app.change_state("songs"), app.font_medium),
            Button((510, 385, 110, 75), "Back", self._back, app.font_medium),
            self.shuffle_button,
        ]
        self.slider = Slider((30, 330, 580, 24), app.audio_volume, self._on_volume_change)
        self._art_for = None
        self._art = None

    def _back(self):
        # Leaving the music screen stops the music rather than leaving it playing.
        self.app.audio.stop()
        self.app.change_state("menu")

    def _on_volume_change(self, percent):
        self.app.audio_volume = percent
        self.app.audio.set_volume(percent)

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)
        self.slider.handle_event(event)

    def update(self):
        audio = self.app.audio
        self.play_button.label = "Pause" if audio.playing else "Play"
        self.shuffle_button.label = f"Shuffle: {'On' if audio.shuffle else 'Off'}"
        track = audio.current_track
        if track is not None and track.path != self._art_for:
            self._art_for = track.path
            self._art = art.cover(track.path, ART_SIZE)

    def draw(self, surface):
        self.draw_background(surface, "Christmas Tunes")
        track = self.app.audio.current_track
        art_rect = (30, 75, ART_SIZE, ART_SIZE)
        if self._art is not None:
            surface.blit(self._art, art_rect[:2])
        else:
            surface.fill(config.ACCENT_COLOR, art_rect)
        if track is None:
            draw_text(surface, "No music found", self.app.font_medium, 435, 90, 360)
        else:
            y = draw_text(surface, track.title, self.app.font_medium, 435, 85, 360)
            draw_text(surface, track.artist, self.app.font_small, 435, y + 4, 360, config.TITLE_COLOR)

        volume_label = render_text(self.app.font_small, f"Volume: {int(self.slider.value)}%")
        surface.blit(volume_label, (30, 290))
        self.slider.draw(surface)

        for button in self.buttons:
            button.draw(surface)
