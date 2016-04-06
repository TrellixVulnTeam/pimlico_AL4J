from Queue import Queue, Empty
from threading import Thread


def _enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()


class OutputQueue(object):
    """
    Direct a readable output (e.g. pipe from a subprocess) to a queue. Returns the queue.
    Output is added to the queue one line at a time.
    To perform a non-blocking read call get_nowait() or get(timeout=T)
    """
    def __init__(self, out):
        self.out = out
        self.q = Queue()
        t = Thread(target=_enqueue_output, args=(out, self.q))
        t.daemon = True # thread dies with the program
        t.start()

    def get_nowait(self):
        try:
            return self.q.get_nowait()
        except Empty:
            # No more in queue
            return None

    def get(self, timeout=None):
        try:
            return self.q.get(timeout=timeout)
        except Empty:
            return None

    def get_available(self):
        """
        Don't block. Just return everything that's available in the queue.
        """
        lines = []
        try:
            while True:
                lines.append(self.q.get_nowait())
        except Empty:
            pass
        return "\n".join(reversed(lines))