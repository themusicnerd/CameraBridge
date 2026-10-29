"""Reentrant camera access with FIFO ordering within each priority."""
from contextlib import contextmanager
import threading
import time

class CameraAccess:
    def __init__(self):
        self.condition=threading.Condition()
        self.owner=None
        self.depth=0
        self.waiters=[]
        self.sequence=0

    @contextmanager
    def priority(self,priority=0,ready_at=None):
        ident=threading.get_ident()
        with self.condition:
            if self.owner==ident:
                self.depth+=1
            else:
                self.sequence+=1
                ticket=(priority,self.sequence)
                self.waiters.append(ticket)
                try:
                    while True:
                        eligible=self.owner is None and ticket==min(self.waiters)
                        delay=max(0,ready_at()-time.monotonic()) if eligible and ready_at is not None else 0
                        if eligible and delay<=0:break
                        self.condition.wait(delay if eligible and delay>0 else None)
                    self.owner=ident
                    self.depth=1
                finally:
                    self.waiters.remove(ticket)
                    self.condition.notify_all()
        try:
            yield self
        finally:
            with self.condition:
                self.depth-=1
                if not self.depth:
                    self.owner=None
                    self.condition.notify_all()

    def __enter__(self):
        # Each invocation needs its own context, including nested acquisitions.
        context=self.priority()
        context.__enter__()
        with self.condition:
            if not hasattr(self,'contexts'):self.contexts={}
            self.contexts.setdefault(threading.get_ident(),[]).append(context)
        return self

    def __exit__(self,*args):
        with self.condition:
            contexts=self.contexts[threading.get_ident()]
            context=contexts.pop()
            if not contexts:del self.contexts[threading.get_ident()]
        return context.__exit__(*args)
