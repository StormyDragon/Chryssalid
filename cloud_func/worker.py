import logging
import os
import socket
import sys
from datetime import datetime, timezone
from logging.handlers import MemoryHandler

import flask
import requests

CODE_LOCATION_DIR = os.environ.get("X_GOOGLE_CODE_LOCATION")
PACKAGE_JSON_FILE = CODE_LOCATION_DIR + '/package.json'
ENTRY_POINT = os.environ.get("X_GOOGLE_ENTRY_POINT", 'function')
SUPERVISOR_HOSTNAME = os.environ.get("X_GOOGLE_SUPERVISOR_HOSTNAME", None)
SUPERVISOR_INTERNAL_PORT = os.environ.get("X_GOOGLE_SUPERVISOR_INTERNAL_PORT", None)
FUNCTION_TRIGGER_TYPE = os.environ.get("X_GOOGLE_FUNCTION_TRIGGER_TYPE")
FUNCTION_NAME = os.environ.get("X_GOOGLE_FUNCTION_NAME")
FUNCTION_TIMEOUT_SEC = os.environ.get("X_GOOGLE_FUNCTION_TIMEOUT_SEC")
WORKER_PORT = os.environ.get("X_GOOGLE_WORKER_PORT")

FUNCTION_STATUS_HEADER_FIELD = 'X-Google-Status'
EXECUTE_PREFIX = '/execute'

MAX_LOG_LENGTH = 5000
MAX_LOG_BATCH_ENTRIES = 1500
MAX_LOG_BATCH_LENGTH = 150000
SUPERVISOR_LOG_TIMEOUT_MS = max(60, int(FUNCTION_TIMEOUT_SEC) if FUNCTION_TIMEOUT_SEC else 0) * 1000
SUPERVISOR_KILL_TIMEOUT_MS = 5000


class SupervisorTasks:
    KILL = "_ah/kill"
    LOG = "_ah/log"


def kill_instance():
    post_to_supervisor(SupervisorTasks.KILL, '', SUPERVISOR_KILL_TIMEOUT_MS, lambda: sys.exit(16))


def post_to_supervisor(path, post_data, timeout, callback=lambda x: None):
    try:
        url = f"http://{SUPERVISOR_HOSTNAME}:{SUPERVISOR_INTERNAL_PORT}/{path}"
        response = requests.post(url, json=post_data, timeout=timeout)
        response.raise_for_status()
    except requests.Timeout as ex:
        callback("Supervisor request timed out")
    except requests.HTTPError as ex:
        callback("Supervisor responded inappropriately.")
    except requests.exceptions.InvalidURL:
        print(post_data)


class SupervisorHandler(MemoryHandler):
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

    def flush(self):
        records, self.buffer = self.buffer[:MAX_LOG_BATCH_ENTRIES], self.buffer[MAX_LOG_BATCH_ENTRIES:]
        if records:
            output = {'Entries': [self.log_entry(record) for record in records]}
            post_to_supervisor(SupervisorTasks.LOG, output, SUPERVISOR_LOG_TIMEOUT_MS)
        return bool(records)

    def flush_all(self):
        while self.flush():
            pass


memory_handler = SupervisorHandler(MAX_LOG_BATCH_ENTRIES, flushLevel=logging.ERROR)
root_logger = logging.getLogger('')
root_logger.addHandler(memory_handler)

logging.getLogger('flask').setLevel('DEBUG')

logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

worker = flask.Blueprint('worker', __name__)


@worker.route('/load', methods=['GET'])
def load():
    return flask.Response('User function is ready', status=200)


@worker.route('/check', methods=['GET'])
def check():
    return flask.Response('', status=200)


def cloud_endpoints(*blueprints):
    app = flask.Flask(__name__)
    app.register_blueprint(worker)

    @app.route('/execute')
    def execute_redir():
        return flask.redirect('/execute/')

    for blue in blueprints:
        app.register_blueprint(blue, url_prefix='/execute')

    return app


if __name__ == '__main__':
    user_functions = flask.Blueprint('user_function', __name__)


    @user_functions.route('/')
    def hello():
        logger.info("Hoy!")
        return "Hello from Python!"


    app = cloud_endpoints(user_functions)


    @app.after_request
    def flush_logs(response):
        memory_handler.flush_all()
        return response


    @app.route('/', defaults={"path": ''})
    @app.route('/<path:path>')
    def catch_all(path):
        res = f"Requested path has no handler associated: {path}"
        logger.warning(res)
        return flask.Response(res, 404)


    memory_handler.flush()

    try:
        socket = socket.socket(fileno=int(os.environ['LOAD_DESCRIPTOR']))
        socket.send(b'HTTP/1.1 200 OK\r\nContent-Length: 22\r\n\r\nUser function is ready')
        socket.close()

        os.environ['WERKZEUG_SERVER_FD'] = os.environ['SERVER_DESCRIPTOR']
        logger.debug(f"{os.environ}")
        logger.info("Python ready to serve")
        app.run(host='0.0.0.0', port=int(WORKER_PORT))
    except Exception as ex:
        logger.error(f"Failure: {ex}")
    finally:
        kill_instance()
