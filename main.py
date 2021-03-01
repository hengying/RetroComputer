import os
import sys
import time
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

from config import Config
from screen import Screen
from utils import *

class RetroComputer():
    def __init__(self):
        make_sure_basic_folder_exist()
        pygame.init()
        self._config = Config()
        if self._config.win_pos_x is not None and self._config.win_pos_y is not None:
            os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (self._config.win_pos_x, self._config.win_pos_y)
        self._surface = pygame.display.set_mode((self._config.win_width, self._config.win_height), pygame.NOFRAME)
        self._clock = pygame.time.Clock()
        if not self._config.show_cursor:
            pygame.mouse.set_visible(False)

        self.__font = pygame.font.Font('fonts/graph-35-pix-clone.ttf', 48)

        self._screen = Screen(self)

    def run(self):
        try:
            while True:
                self._update()

                for e in pygame.event.get():
                    if e.type == pygame.QUIT:
                        raise StopIteration
                    if e.type == pygame.KEYDOWN:
                        self._key_down(e)

                self._paint()

                pygame.display.flip()
                self._clock.tick(self._config.fps)
        except StopIteration:
            self.quit()

    def quit(self):
        self._do_quit()

    def _do_quit(self):
        self._screen.end()
        #self._config.save_config_file()
        pygame.quit()
        sys.exit()

    def _update(self):
        self._screen.update()

    def _paint(self):
        self._screen.paint()

    def _key_down(self, event):
        self._screen.key_down(event)

    @property
    def font(self):
        return self.__font

    @property
    def surface(self):
        return self._surface

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    c = RetroComputer()
    c.run()

