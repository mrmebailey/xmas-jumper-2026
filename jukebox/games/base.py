import pygame

from .. import config, scores
from ..states.base import State
from ..widgets import Button, draw_text, render_text

PLAY_TOP = 64  # below the fairy lights and the score line


class GameState(State):
    """Shared parts of every game: score and best score along the top, a Back
    button, and a game-over panel offering another go. A game fills in
    reset(), step(dt_ms), draw_game(surface) and handle_game_event(event)."""

    name = ""  # key for the saved best score
    score_label = "Score"
    lower_is_better = False  # e.g. fewest moves
    over_title = "Game Over"

    def on_enter(self):
        app = self.app
        self.back_button = Button((540, 26, 92, 36), "Back", lambda: app.change_state("games"), app.font_tiny)
        self.over_buttons = [
            Button((140, 330, 190, 75), "Again", self.new_game, app.font_medium),
            Button((350, 330, 150, 75), "Back", lambda: app.change_state("games"), app.font_medium),
        ]
        self.new_game()

    @property
    def full_speed(self):
        return not self.over

    def new_game(self):
        self.score = 0
        self.over = False
        self.new_best = False
        self._last_ticks = pygame.time.get_ticks()
        self.reset()

    def end_game(self, title=None):
        self.over = True
        self.over_title = title or type(self).over_title
        self.new_best = scores.record(self.name, self.score, self.lower_is_better)

    def handle_event(self, event):
        if self.over:
            for button in self.over_buttons:
                button.handle_event(event)
            return
        self.back_button.handle_event(event)
        pos = getattr(event, "pos", None)
        if pos is not None and self.back_button.rect.collidepoint(pos):
            return
        self.handle_game_event(event)

    def update(self):
        now = pygame.time.get_ticks()
        # Cap the step so a slow frame (or a pause in another screen) can't
        # make everything jump.
        dt = min(now - self._last_ticks, 250)
        self._last_ticks = now
        if not self.over:
            self.step(dt)

    def draw(self, surface):
        self.draw_game(surface)
        font = self.app.font_small
        surface.blit(render_text(font, f"{self.score_label}: {self.score}"), (12, 30))
        best = scores.best(self.name)
        if best is not None:
            surface.blit(render_text(self.app.font_tiny, f"Best: {best}", config.TITLE_COLOR), (190, 34))
        self.back_button.draw(surface)
        if self.over:
            self._draw_over(surface)

    def _draw_over(self, surface):
        panel = pygame.Rect(100, 110, 440, 320)
        pygame.draw.rect(surface, (10, 60, 35), panel, border_radius=18)
        pygame.draw.rect(surface, config.TITLE_COLOR, panel, width=4, border_radius=18)
        y = draw_text(surface, self.over_title, self.app.font_title, panel.centerx, panel.y + 18,
                      panel.width - 30, config.TITLE_COLOR)
        y = draw_text(surface, f"{self.score_label}: {self.score}", self.app.font_large, panel.centerx, y + 10,
                      panel.width - 30)
        if self.new_best:
            draw_text(surface, "New best!", self.app.font_medium, panel.centerx, y + 6, panel.width - 30,
                      config.TITLE_COLOR)
        for button in self.over_buttons:
            button.draw(surface)

    # For each game to fill in.
    def reset(self):
        pass

    def step(self, dt):
        pass

    def draw_game(self, surface):
        self.draw_background(surface)

    def handle_game_event(self, event):
        pass
