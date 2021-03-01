from PyBasic.basictoken import BASICToken as Token
from PyBasic.lexer import Lexer
from PyBasic.program import Program
import sys
import builtins
import threading
import time
from queue import Queue
from utils import *

# https://stackoverflow.com/questions/21341096/redirect-print-to-string-list
class PrintStream:
    def __init__(self, console):
        self._console = console
        self._buffer = ''

    def write(self, msg):
        self._buffer = self._buffer + msg
        if self._buffer.find('\n') != -1:
            self._console.print_messages(self._buffer)
            self._buffer = ''

    def flush(self):
        pass

    def __enter__(self):
        sys.stdout = self
        return self

    def __exit__(self, ext_type, exc_value, traceback):
        sys.stdout = sys.__stdout__


# A BASIC Interpreter - Program like it's 1979!
# https://github.com/richpl/PyBasic

class BasicInterpreter():
    def __init__(self, console):
        self._console = console
        self._should_break  = False
        self._command_queue = self._console.command_queue
        self._request_queue = self._console.request_queue
        self._lexer = Lexer()
        self._program = Program(self)
        self._print_stream = PrintStream(console)
        sys.stdout = self._print_stream

        def request_user_input(prompt):
            return self._request_user_input(prompt)
        builtins.input = request_user_input

        def thread_run():
            return self.run()
        self._thread = threading.Thread(target = thread_run)
        self._thread.start()

    def _request_user_input(self, prompt):
        self._request_queue.put(prompt)
        msg = self._command_queue.get()
        print('INPUT:' + msg)
        return msg

    def break_execution(self):
        self._should_break = True

    def should_break(self):
        return self._should_break

    def wait_thread(self):
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def run(self):
        while True:
            try:
                command = self._command_queue.get()

                tokenlist = self._lexer.tokenize(command)

                # Execute commands directly, otherwise
                # add program statements to the stored
                # BASIC program

                if len(tokenlist) > 0:

                    # Exit the interpreter
                    if tokenlist[0].category == Token.EXIT:
                        break

                    # Add a new program statement, beginning
                    # a line number
                    elif tokenlist[0].category == Token.UNSIGNEDINT \
                            and len(tokenlist) > 1:
                        self._program.add_stmt(tokenlist)

                    # Delete a statement from the program
                    elif tokenlist[0].category == Token.UNSIGNEDINT \
                            and len(tokenlist) == 1:
                        self._program.delete_statement(int(tokenlist[0].lexeme))

                    # Execute the program
                    elif tokenlist[0].category == Token.RUN:
                        try:
                            self._should_break = False
                            self._program.execute()

                        except KeyboardInterrupt:
                            print("Program terminated")

                    # List the program
                    elif tokenlist[0].category == Token.LIST:
                        self._program.list()

                    # Save the program to disk
                    elif tokenlist[0].category == Token.SAVE:
                        file_name = self._get_filename(tokenlist)
                        if file_name is not None:
                            self._program.save(BASIC_PROGRAM_FOLDER_NAME + '/' + file_name)
                            print("Program written to file {}".format(file_name))

                    # Load the program from disk
                    elif tokenlist[0].category == Token.LOAD:
                        file_name = self._get_filename(tokenlist)
                        if file_name is not None:
                            self._program.load(BASIC_PROGRAM_FOLDER_NAME + '/' + file_name)
                            print("Program read from file {}".format(file_name))

                    # Delete the program from memory
                    elif tokenlist[0].category == Token.NEW:
                        self._program.delete()

                    # Unrecognised input
                    else:
                        print("Unrecognised input")
                        for token in tokenlist:
                            token.print_lexeme()
                        #print(flush=True)

            except Exception as e:
                print(str(e))

    def _get_filename(self, tokenlist):
        if len(tokenlist) <= 1:
            print('No filename')
            return None
        else:
            filename = ''
            for t in tokenlist[1:]:
                filename += t.lexeme

            if not file_name_is_valid(filename):
                print("Filename can't have: '\\','/','..'")
                return None
            else:
                return filename
