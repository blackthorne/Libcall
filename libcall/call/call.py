#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Libcall

a small wrapper for different types of calls, it can be used to spawn an external process
or to just run python code from string onto a new thread with timeout support. This small
lib adds logging and error handling in a way that can be useful for running in agents within
a distributed system where you need a uniform yet flexible way to invoke different types of
calls and possibly with timeouts. You will get a handle that you can use to retrieve at any
point in time the status of the running call or to order it to stop always using the same API
 regardless of the call type.

"""

__author__ = 'Francisco Ribeiro <blackthorne@ironik.org>'
__license__ = 'Apache License 2.0'
__vcs_id__ = '$Id$'
__version__ = '0.1'

# defaults
DEFAULT_TIMEOUT = 5

# error
CALL_TYPE_NOT_SUPPORTED = -1
CALL_ERROR = -2
TIMEOUT_REACHED = -3
UNKNOWN = -4
CALL_SYNTAX_ERROR = -5
THREAD_ERROR = -6

# status codes
INIT = 0
RUNNING = 1
ERROR = -1
COMPLETED = 2

# commands - not in use
STOP = 0
START = 1
RESUME = 2
ABORT = 3

# imports
import subprocess, shlex
import threading
import time
import ctypes
import inspect
import signal
import sys

# Python3.3 subprocess32
# http://stackoverflow.com/questions/18372395/python-importing-subprocess-modules-from-v3-3-to-v2-7-4
import subprocess32

subprocess = subprocess32

# for handling stdout in python basic calls
import StringIO
import contextlib

## call types
# subprocess - subprocess_call(*popenargs, **kwargs):
# shell-env -
# python-basic

def isset(var): return var in vars() or var in globals()

@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = StringIO.StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old


class StoppableThread(threading.Thread):

    def __init__(self, code=None, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name,
                                  verbose=verbose)
        self.args = args
        self.kwargs = kwargs
        self.code = code
        return

    def kill(self):
        self.handle.terminate()
        self.handle.raise_exc(SystemExit)

    @staticmethod
    def _async_raise(tid, exctype):
        """raises the exception, performs cleanup if needed"""
        if not inspect.isclass(exctype):
            raise TypeError("Only types can be raised (not instances)")
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid),
                                                         ctypes.py_object(exctype))
        if res == 0:
            raise ValueError("invalid thread id")
        elif res != 1:
            # """if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    @staticmethod
    def worker(code):
        exec code

    def _get_my_tid(self):
        """determines this (self's) thread id"""
        if not self.isAlive():
            raise threading.ThreadError("the thread is not active")

        # do we have it cached?
        if hasattr(self, "_thread_id"):
            return self._thread_id

        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid

        raise AssertionError("could not determine the thread's id")

    def raise_exc(self, exctype):
        """raises the given exception type in the context of this thread"""
        self._async_raise(self._get_my_tid(), exctype)

    def terminate(self):
        """raises SystemExit in the context of the given thread, which should
        cause the thread to exit silently (unless caught)"""
        self.raise_exc(SystemExit)

    def run(self):
        self.worker(self.code)
        return


# command line handling
def str_to_cmd_args(cmd_line):
    return shlex.split(cmd_line)


def cmd_args_to_str(args):
    # or ' '.join(shlex.quote(x) for x in args)
    return subprocess.list2cmdline(args)


class TimeoutError(Exception):
    pass


class timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)


#############
# Main Class

class Command(object):
    # implements 'subprocess' call:   sys [str...] -> popen
    # uses subprocess32 backport
    def subprocess_call(self, **popenvars):
        """Run command with arguments.  Wait for command to complete or
        timeout, then return the returncode attribute.

        The arguments are the same as for the Popen constructor.  Example:

        retcode = execute_call(["ls", "-l"])
        """

        try:
            self.handle = subprocess.Popen(self.task, **popenvars)
            self.logger.debug(
                "subprocess32 call: {0} with PID: {1} and timeout: {2}".format(self.task, self.handle.pid, self.timeout))
            stdout, stderr = self.handle.communicate(timeout=self.timeout)  # return ,p.poll() ?
            return self.handle.returncode, stdout, stderr
            # return p.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            self.logger.debug("timeout expired, killing the process...")
            if isset('self.handle'):
                self.handle.send_signal(signal.SIGTERM)
                self.handle.kill()
                self.handle.wait()
                self.error_code = TIMEOUT_REACHED
                return None
        except:
            self.logger.debug("unknown error")
            self.status = ERROR
            if isset('self.handle'):
                self.handle.kill()
                self.handle.wait()
                self.error_code = CALL_ERROR
                return None

        return UNKNOWN

    #@TODO: stderr, stdin, return_code and add args?
    def python_basic_call2(self):
        self.logger.debug("python_basic_call with args {0}".format(vars))
        if self.timeout is None or self.timeout == 0:
            try:
                with stdoutIO() as s:
                    exec (self.task)
                    self.stdout = s.getvalue()
            except SyntaxError:
                self.status = CALL_SYNTAX_ERROR
                return CALL_SYNTAX_ERROR
        else:
            try:
                with timeout(seconds=self.timeout):
                    with stdoutIO() as s:
                        exec (self.task)
                        self.stdout = s.getvalue()
            except TimeoutError:
                pass

    # implements 'python-basic' call:  python code str -> exec
    #
    def python_basic_call(self):
        self.logger.debug("python_basic_call with args {0}".format(vars))
        if self.timeout is None or self.timeout == 0:
            try:
                with stdoutIO() as s:
                    exec (self.task)
                    self.stdout = s.getvalue()
            except SyntaxError:
                self.status = CALL_SYNTAX_ERROR
                return CALL_SYNTAX_ERROR
        else:
            self.handle = StoppableThread(code=self.task)
            self.logger.debug("thread created")
            self.handle.start()
            self.logger.debug("thread started")
            self.status = RUNNING if self.handle.isAlive() else COMPLETED
            try:
                start_time = time.time()
                while self.handle.isAlive():
                    time.sleep(1)
                    if (time.time() - start_time) > self.timeout:
                        self.logger.debug('timeout triggered')
                        self.handle.terminate()
                        self.handle.raise_exc(SystemExit)  # @TODO: self.status error handling needs review
                        self.status = ERROR
            except threading.ThreadError:
                self.status = ERROR
                pass
            finally:
                self.logger.debug("thread stopped")
                self.status = ERROR if self.status == ERROR else COMPLETED
                self.handle.join()

                # unix_timeout_call.unix_timeout_call(python_code, timeout)

    def __init__(self, task, call_type, timeout=None, pre_callback=None, post_callback=None, logger=None,
                 timer_callback=None, executable=None):
        """

        :param task:
        :param call_type:
        :param timeout:
        :param pre_callback:
        :param post_callback:
        :param logger:
        :param timer_callback:
        :return:
        """
        self.task = task
        self.timeout = timeout
        self.call_type = call_type
        self.pre_callback = pre_callback
        self.post_callback = post_callback
        self.timer_callback = timer_callback
        self.requested_status = None
        self.process = None
        self.start_time = None
        self.stop_time = None
        self.return_msg = None
        self.stdin = subprocess.PIPE
        self.stdout = subprocess.PIPE
        self.stderr = subprocess.PIPE
        self.status = INIT
        self.executable = executable
        self.error_code = None
        self.handle = None

        if logger is not None:
            self.logger = logger
            self.logger.debug('Command created')

    def start(self):
        self.status = RUNNING
        return_code = None

        if self.call_type == 'subprocess':
            result = self.subprocess_call(stdin=self.stdin, stdout=self.stdout, stderr=self.stderr)

        elif self.call_type == 'shell-env':
            result = self.subprocess_call(stdin=self.stdin, stdout=self.stdout, stderr=self.stderr, shell=True)

        elif self.call_type == 'python-basic':
            self.logger.debug("code loaded with {0} line(s)".format(len(self.task.split('\n'))))
            return self.python_basic_call()

        else:
            self.logger.debug("failed to execute call")
            return CALL_TYPE_NOT_SUPPORTED

        if type(result) == tuple:
            return_code, self.stdout, self.stderr = result

        return return_code

    #@TODO: to be done
    #     thread = threading.Thread(target=target)
    # self.timer = threading.Timer(self.timeout, self.timer_callback)

    def timer_callback(self):
        self.logger.debug('Terminating process (timed out)')
        self.process.terminate()

    def stop(self):

        if self.call_type == 'subprocess' or self.call_type == 'shell-env':
            self.handle.send_signal(signal.SIGTERM)
            self.handle.kill()
            self.handle.wait()

        elif self.call_type == 'python-basic':
            self.handle.terminate()
            self.handle.raise_exc(SystemExit) # only works with basic call 1

        else:
            self.logger.debug("failed to execute call")
            return CALL_TYPE_NOT_SUPPORTED

        self.requested_status = STOP

        # @TODO: call pre_callback
        # @TODO: call post_callback
