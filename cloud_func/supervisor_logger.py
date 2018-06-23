import logging
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from logging.handlers import MemoryHandler

import requests


@contextmanager
def supress_logging():
    root = logging.getLogger()
    level = root.getEffectiveLevel()
    root.setLevel('ERROR')
    yield
    root.setLevel(level)


class Supervisor:
    KILL = "_ah/kill"
    LOG = "_ah/log"

    def __init__(self, *,
                 hostname: str, port: int,
                 log_timeout_secs: int, kill_timeout_secs: int):
        self.supervisor_hostname = hostname
        self.supervisor_port = port
        self.log_timeout_secs = log_timeout_secs
        self.kill_timeout_secs = kill_timeout_secs

    def kill_instance(self):
        """
        Notify supervisor of our imminent death.
        :return:
        """
        self.post_to_supervisor(self.KILL, '', self.kill_timeout_secs, lambda: sys.exit(16))

    def log_entry(self, record):
        payload = record.getMessage()
        severity = record.levelname
        time = datetime.fromtimestamp(record.created)
        time = time.replace(tzinfo=timezone.utc)
        return {
            "TextPayload": payload,
            "Severity": severity,
            "Time": time.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        }

    def log(self, records):
        entries = {'Entries': [self.log_entry(record) for record in records]}
        self.post_to_supervisor(self.LOG, entries, self.log_timeout_secs)

    def post_to_supervisor(self, path, post_data, timeout, callback=lambda x: None):
        try:
            url = f"http://{self.supervisor_hostname}:{self.supervisor_port}/{path}"
            with supress_logging():
                response = requests.post(url, json=post_data, timeout=timeout)
            if response.status_code != 200:
                logging.getLogger().debug('Could not communicate with Supervisor')
        except requests.Timeout as ex:
            callback("Supervisor request timed out")
        except requests.HTTPError as ex:
            callback("Supervisor responded inappropriately.")
        except requests.exceptions.InvalidURL:
            print(post_data)


class SupervisorHandler(MemoryHandler):
    def __init__(self, supervisor: Supervisor, max_batch_entries: int, max_log_length: int, **config):
        super().__init__(max_batch_entries, **config)
        self.supervisor = supervisor
        self.max_log_length = max_log_length
        self.can_flush = False

    def shouldFlush(self, record):
        return super().shouldFlush(record) or len(record.getMessage()) > self.max_log_length

    def flush(self):
        if self.can_flush:
            records, self.buffer = self.buffer[:self.capacity], self.buffer[self.capacity:]
            if records:
                self.supervisor.log(records)
            return bool(records)
        else:
            return False

    def flush_all(self):
        while self.flush():
            pass
