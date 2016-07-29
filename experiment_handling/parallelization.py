from twisted.internet import defer, protocol, task
import os
import subprocess


class Scheduler(object):

    def __init__(self, max_threads=float('inf'), **kwargs):
        self.max_threads = max_threads
        self.active_processes = 0
        self.processes = list()
        self.fired_on_completion_deferreds = list()
        self.stop_reactor_deferred = None

    def add_process(self, process):
        """
        Adds (queues) a process on the scheduler
        :param process: The process to be added
        :return deferred: A Twisted deferred that is fired on the processes completion
        """
        self.processes.append(process)
        return process.defer_until_process_completion()

    def run_processes(self):
        """
        Runs all of the processes queued with add_process.  Blocks until all processes are complete
        :return:
        """
        from twisted.internet import reactor
        while self.processes and self.active_processes < self.max_threads:
            self._open_next_process()

        reactor.run()

    def _open_next_process(self):
        """
        Attempts to open the next process in the process queue.  If the queue is empty, this function creates a
        deferred that is fired when all process are fired.  When fired, this deferred stops the reactor, unblocking
        the run_processes call.
        :return:
        """
        if self.processes and self.active_processes < self.max_threads:
            p = self.processes.pop(0)
            d = p.launch()
            d.addBoth(self._process_complete_callback)
            self.fired_on_completion_deferreds.append(d)
            self.active_processes += 1
        elif self.stop_reactor_deferred is None and not self.processes:
            # If I get here, the processes are exhausted, and the exit deferred hasn't been created yet
            self.stop_reactor_deferred = defer.DeferredList(self.fired_on_completion_deferreds, consumeErrors=True)
            self.stop_reactor_deferred.addBoth(self._stop_reactor_callback)

    def _stop_reactor_callback(self, results):
        """
        Stops the reactor.  Chained to a Deferred that is fired when all processes complete.
        :param results: Argument supplied by the previous callbacks in the deferred.
        :return:
        """
        from twisted.internet import reactor
        reactor.stop()
        return results

    def _process_complete_callback(self, results):
        """
        Callback called when a process is completed.
        Decrements the active_processes counter, and calls open_next_process()
        :param results:
        :return:
        """
        self.active_processes -= 1
        print 'Process Complete'
        print 'Active Processes:', self.active_processes
        print 'Processes Remaining:', len(self.processes)
        self._open_next_process()
        return results


class BatchScheduler(Scheduler):
    
    def __init__(self, max_threads=float('inf'), poll_queue='gpu', polling_interval=5, **kwargs):
        Scheduler.__init__(self, max_threads=max_threads, **kwargs)
        self.poll_queue = poll_queue
        self.poll_call = task.LoopingCall(self._open_next_process)
        self.polling_interval = polling_interval
        
    def get_active_bjobs_count(self):
        output_str = subprocess.check_output('bjobs -q {} | wc -l'.format(self.poll_queue), shell=True)
        n_jobs = int(output_str) - 1 # The first bjobs output line is a header
        return n_jobs

    def run_processes(self):
        self.poll_call.start(self.polling_interval)
        Scheduler.run_processes(self)

    def _open_next_process(self):
        """
        Attempts to open the next process in the process queue.  If the queue is empty, this function creates a
        deferred that is fired when all process are fired.  When fired, this deferred stops the reactor, unblocking
        the run_processes call.
        :return:
        """
        if self.processes and self.get_active_bjobs_count < self.max_threads:
            p = self.processes.pop(0)
            d = p.launch()
            d.addBoth(self._process_complete_callback)
            self.fired_on_completion_deferreds.append(d)
        elif self.stop_reactor_deferred is None and not self.processes:
            # If I get here, the processes are exhausted, and the exit deferred hasn't been created yet
            self.stop_reactor_deferred = defer.DeferredList(self.fired_on_completion_deferreds, consumeErrors=True)
            self.stop_reactor_deferred.addBoth(self._stop_reactor_callback)

    def _process_complete_callback(self, results):
        """
        Callback called when a process is completed.
        Decrements the active_processes counter, and calls open_next_process()
        :param results:
        :return:
        """
        print 'Job Launched'
        print 'Active Bjobs:', self.get_active_bjobs_count()
        print 'Processes Remaining:', len(self.processes)
        print '------------------------------------------'
        return results

class Task(object):

    def __init__(self, action=None, *args, **kwargs):
        self.action = action
        self.fire_on_completion_deferreds = list()

    def launch(self):
        """
        Launches the task.
        :return:
        """
        d = self.defer_until_process_completion()
        try:
            result = self.action()
        except:
            # TODO add failure here
            d.errback()
        finally:
            d.callback(result)
        return d

    def fire_fire_on_completion_deferreds(self, arg=None):
        """
        Fires a list of deferreds once the task ends
        :param arg: An argument to call the deferreds with
        :return: void
        """
        while self.fire_on_completion_deferreds:
            d = self.fire_on_completion_deferreds.pop()
            d.callback(arg)
#            except defer.AlreadyCalledError:
#                print 'Deferred already fired!'

    def defer_until_process_completion(self):
        """

        :return:
        """
        d = defer.Deferred()
        self.fire_on_completion_deferreds.append(d)
        return d

    @staticmethod
    def _test_callback(result):
        print 'Test Callback'
        return result


class Process(Task, protocol.ProcessProtocol):

    def __init__(self, exe, *args, **kwargs):
        """
        :param exe: Path to the executable to be called
        :param args: Arguments to the Executable being called
        :param output_callback: A function to be called with data from stdout
        :param error_callback: A function to be called with data from stderr
        :param kwargs: Additional keyword arguments, currently output_callback and error_callback

        """
        super(Process, self).__init__(**kwargs)
        self.exe = exe
        self.args = list(args)
        self.output_callback = kwargs.get('output_callback', echo)
        self.error_callback = kwargs.get('error_callback', echo)
        self.env = kwargs.get('env', os.environ)
        self.cwd = kwargs.get('cwd', os.getcwd())
        self.fire_on_completion_deferreds = list()

    def launch(self):
        from twisted.internet import reactor
        reactor.spawnProcess(self, executable=self.exe, args=self.args, env=self.env, path=self.cwd)
        return self.defer_until_process_completion()

    def outReceived(self, data):
        self.output_callback(data)

    def errReceived(self, data):
        self.error_callback(data)

    def processEnded(self, reason):
        # TODO: Figure out what reason (a Failure) contains if process succeeds vs fails
        self.fire_fire_on_completion_deferreds(reason)


class ProcessChain(Task):

    def __init__(self, iterable=None, **kwargs):
        super(ProcessChain, self).__init__(**kwargs)
        if iterable is not None:
            self.processes = [process for process in iterable]
        else:
            self.processes = list()

    def launch(self):
        self._launch_next_process()
        return self.defer_until_process_completion()

    def add_process(self, process):
        self.processes.append(process)
        return process.defer_until_process_completion()

    def get_subprocess_complete_deferreds(self):
        return [process.defer_until_process_completion() for process in self.processes]

    def _launch_next_process(self):
        if self.processes:
            p = self.processes.pop(0)
            d = p.launch()
            d.addBoth(self._launch_next_process_callback)
        else:
            # If I get here, the process chain has been exhausted
            self.fire_fire_on_completion_deferreds()

    def _launch_next_process_callback(self, results):
        self._launch_next_process()


class BatchProcess(Process):
    """
    A process that is submitted to an lsf queue
    """
    # TODO: Add memory and time settings

    def __init__(self, *args, **kwargs):
        bsub_path = 'bsub'
        run_time = kwargs.get('run_time', '12:00')
        queue = kwargs.get('queue', 'short')
        memory = kwargs.get('memory', 32000)
        ngpus = kwargs.get('ngpus', 0)
        self.submission_args = [
            'bsub', 
            '-W', run_time, 
            '-q', queue, 
            '-R', 'rusage[mem={mem},ngpus={ngpus}]'.format(**{'mem': memory, 'ngpus': ngpus})
        ]
        self.log_path = kwargs.get('log_path', None)
        if self.log_path is not None:
            log_string = '-o %s -e %s ' % (self.log_path, self.log_path)
            self.submission_args += log_string.split()
        self.job_args = list(args)
        Process.__init__(self, bsub_path, *(self.submission_args + self.job_args), **kwargs)

    def launch(self):
        self.args = self.submission_args + self.job_args
        d = Process.launch(self)
        return d

    # TODO: Why doesn't this work on orchestra?
    @staticmethod
    def get_bsub_path():
        proc = subprocess.Popen(['which', 'bsub'], stdout = subprocess.PIPE)
        # TODO: raise process failed error if data(1) is not None
        return proc.communicate()[0]


def echo(stuff):
    print stuff


def process_generator():
    exe = '/bin/echo'
    num = 0
    while num < 15:
        num += 1
        args = ['echo', 'This is process number {}!'.format(num)]
        yield Process(exe, *args)


def test_chains():
    scheduler = Scheduler(max_threads=5)

    print 'Running Chain Processes....'
    for chain in (ProcessChain((process for process in process_generator())) for n in xrange(0, 10)):
        scheduler.add_process(chain)
    scheduler.run_processes()


def test_processes():
    scheduler = Scheduler(max_threads=5)

    print 'Running single processes....'
    for process in process_generator():
        scheduler.add_process(process)
    scheduler.run_processes()


def test_bsub():
    scheduler = Scheduler()

    print 'Submitting Bjobs.....'
    args = ['echo', 'bsub_test', '>', '~/testfile.txt']
    process = BatchProcess(*args)

    scheduler.add_process(process)
    scheduler.run_processes()


def main():
    test_bsub()

if __name__ == '__main__':
    main()
