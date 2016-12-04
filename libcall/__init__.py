"""Libcall

a small wrapper for different types of calls, it can be used to spawn an external process
or to just run python code from string onto a new thread with timeout support. This small
lib adds logging and error handling in a way that can be useful for running in agents within
a distributed system where you need a uniform yet flexible way to invoke different types of
calls and possibly with timeouts. You will get a handle that you can use to retrieve at any
point in time the status of the running call or to order it to stop always using the same API
 regardless of the call type.
"""

__all__ = ["start", "timer_callback", "stop"]
