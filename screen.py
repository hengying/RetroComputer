
import pygame

from config import Config
from utils import *
from basic_interpreter import BasicInterpreter
from queue import Queue
import os
from listcmd.listcmd import line2argv

"""
物理屏幕：
35每行
8行

虚拟屏幕：
每行字符个数不限制
历史信息最多保留500行

单个字符大小：
36x48
"""

class Screen():
    def __init__(self, container):
        self._container = container
        self._surface = container.surface

        self._config = Config()

        # counted by pixel
        self._BIAS_X_PX = 10
        self._BIAS_Y_PX = 5
        self._CHAR_WIDTH_PX = 36
        self._CHAR_HEIGHT_PX = 48
        self._CURSOR_BIAS_Y_PX = 6

        # counted by character
        self._SCREEN_WIDTH = 35
        self._SCREEN_HEIGHT = 8
        self._MAX_HISTORY_MSG_COUNT = 500
        self._HIS_DISPLAY_COUNT = 7
        self._MAX_INPUT_HIS_RECORDS_COUNT = 20
        self._his_camera_x = 0
        self._his_camera_y = 0
        self._cur_camera_x = 0
        self._cursor_x = 0

        # cursor blink about one third second
        self._cursor_blink_switch_count = self._config.fps / 3
        self._cursor_bright = True
        self._cursor_blink_count = 0

        self._history_msgs = []
        self._history_input_lines = []
        self._current_displayed_history_record_index = None

        self._current_line = ''
        self._in_history_mode = False

        self._esc_pressed_count = 0

        self._set_prompt('>')

        self._command_queue = Queue()
        self._request_queue = Queue()
        self._in_request_user_input = False
        self._basic_interpreter = BasicInterpreter(self)

        self.print_messages('Welcome to PyBasic')
        self.print_messages('HELP for help')

    def key_down(self, event):
        if event.key == pygame.K_ESCAPE:
            if not self._in_history_mode:
                self._esc_pressed_count += 1
                if self._esc_pressed_count >= 2:
                    self._basic_interpreter.break_execution()
                    self._set_input_line('')
                    self._esc_pressed_count = 0
        else:
            self._esc_pressed_count = 0

        if event.key == pygame.K_F4:
            self.quit()

        if event.key == pygame.K_TAB:
            self._change_to_history_mode(not self._in_history_mode)

        if not self._in_history_mode:
            if event.key == pygame.K_RETURN:
                self._return_pressed()
            elif event.key == pygame.K_BACKSPACE:
                self._del_pre_char()
                self._validate_cursor()
            elif event.key == pygame.K_DELETE:
                self._del_char()
                self._validate_cursor()
            elif event.key == pygame.K_INSERT:
                pass
            # 对于以上按键，Mac OS 上 len(event.unicode) > 0 不成立
            # 但是在树莓派上，len(event.unicode) > 0 成立，所以放到上面
            elif len(event.unicode) > 0:
                k = ord(event.unicode)
                if k >= pygame.K_SPACE and k < pygame.K_a:
                    self._add_char(chr(ord('[') + k - pygame.K_LEFTBRACKET))
                elif k >= pygame.K_a and k <= pygame.K_z:
                    self._add_char(chr(ord('A') + k - pygame.K_a))
                elif k >= 123 and k <= 126:
                    self._add_char(event.unicode)

        if event.key == pygame.K_UP:
            if self._in_history_mode:
                self._his_camera_y -= 1
                self._validate_history_camera()
            else:
                self._show_previous_history_input()
        elif event.key == pygame.K_DOWN:
            if self._in_history_mode:
                self._his_camera_y += 1
                self._validate_history_camera()
            else:
                self._show_next_history_input()
        elif event.key == pygame.K_RIGHT:
            if self._in_history_mode:
                self._his_camera_x += 1
                self._validate_history_camera()
            else:
                self._cursor_x += 1
                self._validate_cursor()
        elif event.key == pygame.K_LEFT:
            if self._in_history_mode:
                self._his_camera_x -= 1
                self._validate_history_camera()
            else:
                self._cursor_x -= 1
                self._validate_cursor()
        elif event.key == pygame.K_HOME:
            if self._in_history_mode:
                self._his_camera_x = 0
                self._validate_history_camera()
            else:
                self._cursor_x = 0
                self._validate_cursor()
        elif event.key == pygame.K_END:
            if self._in_history_mode:
                self._his_camera_x = max([len(msg) for msg in self._displayed_history_msgs()])
                self._validate_history_camera()
            else:
                self._cursor_x = len(self._current_line)
                self._validate_cursor()
        elif event.key == pygame.K_PAGEUP:
            if self._in_history_mode:
                self._his_camera_y -= self._HIS_DISPLAY_COUNT
                self._validate_history_camera()
            else:
                pass
        elif event.key == pygame.K_PAGEDOWN:
            if self._in_history_mode:
                self._his_camera_y += self._HIS_DISPLAY_COUNT
                self._validate_history_camera()
            else:
                pass

        return True

    def quit(self):
        self._container.quit()

    def end(self):
        self._basic_interpreter.break_execution()
        if self._in_request_user_input:
            self._send_user_input('')
        self._command_queue.put('EXIT')
        self._basic_interpreter.wait_thread()

    def _del_pre_char(self):
        self._current_line = self._current_line[:self._cursor_x - 1] + self._current_line[self._cursor_x:]
        self._cursor_x -= 1
        self._validate_cursor()

    def _del_char(self):
        self._current_line = self._current_line[:self._cursor_x] + self._current_line[self._cursor_x + 1:]
        self._validate_cursor()

    def _add_char(self, char):
        self._current_line = self._current_line[:self._cursor_x] + char + self._current_line[self._cursor_x:]
        self._cursor_x += 1
        self._validate_cursor()

    def _set_input_line(self, input_line):
        if len(self._current_line) > 0:
            if self._current_displayed_history_record_index is None:
                self._add_input_history(self._current_line)
        self._current_line = input_line
        self._cursor_x = len(self._current_line)
        self._validate_cursor()

    def _validate_cursor(self):
        if self._cursor_x < 0:
            self._cursor_x = 0
        if self._cursor_x > len(self._current_line):
            self._cursor_x = len(self._current_line)
        if self._cur_camera_x > self._cursor_x:
            self._cur_camera_x = self._cursor_x - self._input_line_display_width
            if self._cur_camera_x < 0:
                self._cur_camera_x = 0
            if self._cur_camera_x >= len(self._current_line):
                self._cur_camera_x = len(self._current_line)
        if self._cursor_x > self._cur_camera_x + self._input_line_display_width:
            self._cur_camera_x = self._cursor_x - self._input_line_display_width

    def _validate_history_camera(self):
        if len(self._history_msgs) < self._HIS_DISPLAY_COUNT:
            self._his_camera_y = len(self._history_msgs) - self._HIS_DISPLAY_COUNT
        else:
            if self._his_camera_y < 0:
                self._his_camera_y = 0

        if self._his_camera_y + self._HIS_DISPLAY_COUNT > len(self._history_msgs):
            self._his_camera_y = len(self._history_msgs) - self._HIS_DISPLAY_COUNT


        max_length = max([len(msg) for msg in self._displayed_history_msgs()])
        if self._his_camera_x + self._SCREEN_WIDTH > max_length:
            self._his_camera_x = max_length - self._SCREEN_WIDTH

        if self._his_camera_x < 0:
            self._his_camera_x = 0

    def _set_prompt(self, prompt):
        self._cur_line_prompt = prompt
        self._input_line_display_width = self._SCREEN_WIDTH - len(self._cur_line_prompt) - 1
        self._validate_cursor()

    def _show_previous_history_input(self):
        if self._current_displayed_history_record_index is None:
            if len(self._history_input_lines) > 0:
                if len(self._current_line) > 0:
                    self._add_input_history(self._current_line)
                    self._current_displayed_history_record_index = len(self._history_input_lines) - 2
                else:
                    self._current_displayed_history_record_index = len(self._history_input_lines) - 1
                self._current_line = self._history_input_lines[self._current_displayed_history_record_index]
        else:
            if self._current_displayed_history_record_index > 0:
                self._current_displayed_history_record_index -= 1
                self._current_line = self._history_input_lines[self._current_displayed_history_record_index]
            else:
                if len(self._current_line) == 0:
                    self._current_line = self._history_input_lines[self._current_displayed_history_record_index]
        self._validate_cursor()

    def _show_next_history_input(self):
        if self._current_displayed_history_record_index is None:
            pass
        else:
            if self._current_displayed_history_record_index < len(self._history_input_lines) - 1:
                self._current_displayed_history_record_index += 1
                self._current_line = self._history_input_lines[self._current_displayed_history_record_index]
            else:
                if len(self._current_line) == 0:
                    self._current_line = self._history_input_lines[self._current_displayed_history_record_index]

        self._validate_cursor()

    def _add_input_history(self, input_line):
        self._history_input_lines.append(input_line)
        if len(self._history_input_lines) > self._MAX_INPUT_HIS_RECORDS_COUNT:
            self._history_input_lines.pop(0)
        self._current_displayed_history_record_index = None

    def _return_pressed(self):
        command = self._current_line
        argv = line2argv(command)

        if not self._in_request_user_input:
            self._add_input_history(self._current_line)
            self.print_messages(self._cur_line_prompt + self._current_line)
        self._current_line = ''
        self._cursor_x = 0
        self._cur_camera_x = 0

        if len(argv) > 0:
            c = argv[0]
            if c == 'QUIT' or c == 'EXIT':
                self.quit()
            elif c == 'HELP':
                self._print_help_message()
            elif c == 'DIR':
                self._list_basic_programs()
            elif c == 'DEL':
                if len(argv) < 2:
                    print('No filename')
                else:
                    filename = argv[1]
                    if not file_name_is_valid(filename):
                        print("Filename can't have: '\\','/','..'")
                    else:

                        full_file_name = BASIC_PROGRAM_FOLDER_NAME + '/' + filename
                        if not os.path.exists(full_file_name):
                            print("File not found")
                        else:
                            os.remove(full_file_name)
            elif c == 'STOP' or c == 'BREAK' or c == 'END':
                # if BASIC is in infinite loop,
                # user could use BREAK command to stop the execution
                self._basic_interpreter.break_execution()
            else:
                try:
                    if self._in_request_user_input:
                        self._send_user_input(command)
                    else:
                        self._command_queue.put(command)
                except Exception as e:
                    self.print_messages(str(e))

    def _print_help_message(self):
        self.print_messages('---------- Document -----------\n')
        self.print_messages('https://github.com/richpl/PyBasic')
        self.print_messages('---------- Function -----------\n'
            'EXP(n) LOG(n) SQR(n) POW(b, e)\n'
            'PI SIN(n) COS(n) TAN(n) ATN(n)\n'
            'ABS(n) ROUND(n) MAX(exp) MIN(exp)\n'
            'RANDOMIZE[n] RND RNDINT(l, h)\n'
            'ASC(s) CHR$(n) STR$(n) VAL(s)\n'
            'LEN(s) LOWER$(s) UPPER$(s)\n'
            'IFF(e,n,n) IF$(exp,s,s)\n'
            'INSTR(...) MID$(...)')
        self.print_messages('---------- Language -----------\n'
            'REM LET DIM DATA\n'
            'IF THEN ELSE\n'
            'FOR TO STEP NEXT\n'
            'INPUT PRINT\n'
            'GOTO ON GOSUB GOSUB RETURN STOP')
        self.print_messages('----------- Command -----------\n'
            'NEW LIST RUN STOP EXIT\n'
            'SAVE LOAD DEL DIR')
        self.print_messages('----------- Console -----------\n'
            'TAB to switch to history\n'
            'ESC twice to clear\n'
            'HELP for help')

    def _list_basic_programs(self):
        for filename in os.listdir(BASIC_PROGRAM_FOLDER_NAME):
            self.print_messages(filename)

    @property
    def command_queue(self):
        return self._command_queue

    @property
    def request_queue(self):
        return self._request_queue

    def print_messages(self, msgs):
        lines = msgs.split('\n')
        for line in lines:
            if len(line) > 0:
                self._history_msgs.append(line)
                if len(self._history_msgs) > self._MAX_HISTORY_MSG_COUNT:
                    self._history_msgs.pop(0)
        self._his_camera_x = 0
        self._his_camera_y = len(self._history_msgs)
        self._validate_history_camera()

    def _change_to_history_mode(self, history_mode):
        self._in_history_mode = history_mode

    def paint(self):
        split_line_y = self._BIAS_Y_PX + self._CHAR_HEIGHT_PX * self._HIS_DISPLAY_COUNT
        if self._in_history_mode:
            pygame.draw.rect(self._surface, self._config.active_background_color,
                         (0, 0, self._config.win_width, split_line_y))
            pygame.draw.rect(self._surface, self._config.background_color,
                         (0, split_line_y, self._config.win_width, self._config.win_height - split_line_y))
        else:
            pygame.draw.rect(self._surface, self._config.background_color,
                         (0, 0, self._config.win_width, split_line_y))
            pygame.draw.rect(self._surface, self._config.active_background_color,
                         (0, split_line_y, self._config.win_width, self._config.win_height - split_line_y))

        self._blit_text_lines(self._surface, self._displayed_history_msgs(),
                        (self._BIAS_X_PX - self._CHAR_WIDTH_PX * self._his_camera_x,
                         self._BIAS_Y_PX - self._CHAR_HEIGHT_PX * self._his_camera_y if self._his_camera_y < 0 else self._BIAS_Y_PX),
                        self._container.font,
                        self._config.highlight_text_color if self._in_history_mode else self._config.text_color)

        self._blit_text_lines(self._surface, [self._cur_line_prompt + self._current_line[self._cur_camera_x:]],
                        (self._BIAS_X_PX,
                         self._BIAS_Y_PX + self._CHAR_HEIGHT_PX * self._HIS_DISPLAY_COUNT),
                        self._container.font,
                        self._config.text_color if self._in_history_mode else self._config.highlight_text_color)

        if not self._in_history_mode:
            if self.cursor_bright:
                self._blit_text_lines(self._surface, ['_'],
                                ((len(self._cur_line_prompt) + self.cursor_x - self._cur_camera_x) * self._CHAR_WIDTH_PX + self._BIAS_X_PX,
                                 self._BIAS_Y_PX + self._CHAR_HEIGHT_PX * self._HIS_DISPLAY_COUNT + self._CURSOR_BIAS_Y_PX),
                                self._container.font, self._config.highlight_text_color)

    def _displayed_history_msgs(self):
        if self._his_camera_y < 0:
            return self._history_msgs[:self._his_camera_y + self._HIS_DISPLAY_COUNT + 1]
        else:
            return self._history_msgs[self._his_camera_y:self._his_camera_y + self._HIS_DISPLAY_COUNT]

    @property
    def cursor_x(self):
        return self._cursor_x

    @property
    def cursor_bright(self):
        return self._cursor_bright

    def _request_user_input(self, prompt):
        self._set_prompt(prompt)
        self._in_request_user_input = True

    def _send_user_input(self, input_line):
        self._set_prompt('>')
        self._in_request_user_input = False
        self._command_queue.put(input_line)

    def update(self):
        self._cursor_blink_count += 1
        if self._cursor_blink_count > self._cursor_blink_switch_count:
            self._cursor_blink_count = 0
            self._cursor_bright = not self._cursor_bright

        if not self._request_queue.empty():
            msg = self._request_queue.get()
            self._request_user_input(msg)

    def _blit_text_lines(self, surface, text_lines, pos, font, color):
        x, y = pos
        for line in text_lines:
            line_surface = font.render(line, True, color)
            line_width, line_height = line_surface.get_size()
            surface.blit(line_surface, (x, y))
            y += line_height

    """
    # 超宽按单词折行版本
    def _blit_text(self, surface, text, pos, font, color):
        words = [word.split(' ') for word in text.splitlines()]  # 2D array where each row is a list of words.
        space = font.size(' ')[0]  # The width of a space.
        max_width, max_height = surface.get_size()
        x, y = pos
        for line in words:
            for word in line:
                word_surface = font.render(word, True, color)
                word_width, word_height = word_surface.get_size()
                if x + word_width >= max_width:
                    x = pos[0]  # Reset the x.
                    y += word_height  # Start on new row.
                surface.blit(word_surface, (x, y))
                x += word_width + space
            x = pos[0]  # Reset the x.
            y += word_height  # Start on new row.
    """