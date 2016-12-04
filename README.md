# Libcall
a small wrapper for different types of different types of calls, it can be used to spawn an external process or just python code from a new thread or dedicated process with timeout support. This small lib adds logging and error handling in a way that can be useful for running in agents within a distributed system where you need a uniform yet flexible way to invoke different types of calls and possibly with timeouts. You can retrieve at any point in the the _status_ of the running call or to order it to _stop_ using the same API regardless of the call type. 

__Keep in mind this offers no Security, untrusted data should never reach any of these calls__

Types of calls supported:
* subprocess (spawns external process)
* subprocess with Shell
* Python (threaded)

### Spawn new process
        a = call.Command(['ls','-l','/'],'subprocess', logger=logger)
        b = a.start()

stdout and stderr can be reached using a.stdout or a.stderr

### Spawn a Python Call
        d = call.Command('print 2+2','python-basic', logger=logger)
        d.start()


### Python Call with timeout
        """
        import time
        while True:
            time.sleep(0.1)
        print 'end'
        """
        d = call.Command(code,'python-basic', logger=logger, timeout=2)

> this timeout feature is not 100% reliable for this type of call (it tries to find and kill a thread internally)

### Shell Call with timeout
        d = call.Command('sleep 50','shell-env', logger=logger, timeout=2)
        d.start()
