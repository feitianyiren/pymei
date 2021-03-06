import pygame
import time
import logging

import plugin, theme, config, keybinds

class Application(object):
    def __init__(self, entrypoint):
        pygame.display.init()
        pygame.font.init()
        pygame.mouse.set_visible(False)
        pygame.event.set_blocked([pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP, pygame.MOUSEBUTTONDOWN])

        self._config = config.get('application')
        theme.load(self._config['theme'])

        self._fullscreen = bool(self._config['fullscreen'])
        self._initScreen()

        self._plugins = self._config['plugins'].keys()
        plugin.globals.init(self._plugins, self)

        self.continue_running = True
        self._window_stack = []
        self._loaded_keys = {}

        self._current_window = None
        self._current_window = entrypoint(self)

        # Sets a recurring event that'll "wake" the loop at least every X ms, so
        # we'll have at least that many FPS. :)
        pygame.time.set_timer(pygame.USEREVENT, int(1.0/self._config['min_fps']*1000))

        self.clock = pygame.time.Clock()

    def _initScreen(self):
        flags = pygame.DOUBLEBUF
        if self._fullscreen:
            flags |= pygame.HWSURFACE | pygame.FULLSCREEN
        self.screen = pygame.display.set_mode(self._config['resolution'], flags)

        pygame.display.set_caption('PyMei')
        return self.screen

    def setFullscreen(self, value):
        if value != self._fullscreen:
            logging.debug("New fullscreen state is %s" % value)
            self._fullscreen = value
            self._initScreen()

    def getFullscreen(self):
        return self._fullscreen

    fullscreen = property(getFullscreen, setFullscreen)

    def _handleEvent(self, event):
        if event.type == pygame.QUIT:
            self._current_window = None
        elif hasattr(event, 'key') and event.type == pygame.KEYDOWN:
            # We load keys on-demand, since it's quite clumsy to traverse the
            # menu tree to find what plugins will be referenced.
            window_name = self.current_window.__class__.__name__
            # A window's keys are loaded only once.
            if not window_name in self._loaded_keys:
                self._load_keys(window_name)
                self._loaded_keys[window_name] = True

            keybinds.handle_key(event.key, self.current_window)

    def _load_keys(self, window):
        keys = config.get('keybinds/%s' % window, {})

        # First we load the config, here.
        keybinds.load_bindings(window, keys)

        # Then, if there are defaults, we "fill in the blanks" using them.
        if not hasattr(self.current_window, 'DEFAULT_KEYS'):
            return 

        details = self.current_window.DEFAULT_KEYS
        keybinds.load_bindings(window, details, ignore_dupes=True)

    @property
    def current_window(self):
        return self._current_window

    def close_window(self):
        if not self.continue_running:
            return
        
        if not self._window_stack:
            self._current_window = None
            self.continue_running = False
        else:
            self._current_window = self._window_stack.pop()

    def open_window(self, window):
        if self._current_window:
            self._window_stack.append(self._current_window)
        self._current_window = window

    def run(self):
        self.screen.fill((0, 0, 0))

        if not self._current_window:
            return False

        plugin.globals.call(self._plugins, 'before_draw', self.screen)
        self._current_window.draw(self.screen)
        plugin.globals.call(self._plugins, 'after_draw', self.screen)
    
        pygame.display.flip()

        plugin.globals.call(self._plugins, 'generate_events')

        self._handleEvent(pygame.event.wait())
        for event in pygame.event.get():
            self._handleEvent(event)

        self.clock.tick(self._config['max_fps'])
        return self.continue_running

    def quit(self):
        pygame.quit()
        plugin.globals.call(self._plugins, 'quit')
