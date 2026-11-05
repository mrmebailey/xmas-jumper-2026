from .. import config
from ..widgets import Button, Slider, draw_text
from .base import State


class MusicState(State):
    def on_enter(self):
        app = self.app
        self.play_button = Button((40, 380, 160, 60), "Play", app.audio.play_pause, app.font_medium)
        self.buttons = [
            self.play_button,
            Button((220, 380, 120, 60), "Prev", app.audio.prev_track, app.font_medium),
            Button((360, 380, 120, 60), "Next", app.audio.next_track, app.font_medium),
            Button((500, 380, 100, 60), "Back", lambda: app.change_state("menu"), app.font_medium),
        ]
        self.slider = Slider((40, 300, 560, 24), app.audio_volume, self._on_volume_change)

    def _on_volume_change(self, percent):
        self.app.audio_volume = percent
        self.app.audio.set_volume(percent)

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)
        self.slider.handle_event(event)

    def update(self):
        self.play_button.label = "Pause" if self.app.audio.playing else "Play"

    def draw(self, surface):
        self.draw_background(surface, "Christmas Tunes")
        draw_text(surface, self.app.audio.current_track_name, self.app.font_medium, config.SCREEN_W // 2, 110,
                  config.SCREEN_W - 60)

        volume_label = self.app.font_small.render(
            f"Volume: {int(self.slider.value)}%", True, config.TEXT_COLOR
        )
        surface.blit(volume_label, (40, 258))
        self.slider.draw(surface)

        for button in self.buttons:
            button.draw(surface)
