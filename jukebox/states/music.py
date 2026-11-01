from .. import config
from ..widgets import Button, Slider
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
        surface.fill(config.BG_COLOR)
        name = self.app.audio.current_track_name
        text = self.app.font_medium.render(name, True, config.TEXT_COLOR)
        surface.blit(text, text.get_rect(center=(config.SCREEN_W // 2, 120)))

        volume_label = self.app.font_small.render(
            f"Volume: {int(self.slider.value)}%", True, config.TEXT_COLOR
        )
        surface.blit(volume_label, (40, 270))
        self.slider.draw(surface)

        for button in self.buttons:
            button.draw(surface)
