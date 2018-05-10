import importlib.util
import logging
import os
import socket
from traceback import format_exception

import flask

from supervisor_logger import Supervisor, SupervisorHandler

CODE_LOCATION_DIR = os.environ.get("X_GOOGLE_CODE_LOCATION")
PACKAGE_JSON_FILE = CODE_LOCATION_DIR + '/package.json'
ENTRY_POINT = os.environ.get("X_GOOGLE_ENTRY_POINT", 'function')
SUPERVISOR_HOSTNAME = os.environ.get("X_GOOGLE_SUPERVISOR_HOSTNAME", None)
SUPERVISOR_INTERNAL_PORT = os.environ.get("X_GOOGLE_SUPERVISOR_INTERNAL_PORT", None)
FUNCTION_TRIGGER_TYPE = os.environ.get("X_GOOGLE_FUNCTION_TRIGGER_TYPE")
FUNCTION_NAME = os.environ.get("X_GOOGLE_FUNCTION_NAME")
FUNCTION_TIMEOUT_SEC = os.environ.get("X_GOOGLE_FUNCTION_TIMEOUT_SEC", 0)
WORKER_PORT = os.environ.get("X_GOOGLE_WORKER_PORT")

FUNCTION_STATUS_HEADER_FIELD = 'X-Google-Status'
EXECUTE_PREFIX = '/execute'

MAX_LOG_LENGTH = 5000
MAX_LOG_BATCH_ENTRIES = 1500
MAX_LOG_BATCH_LENGTH = 150000
SUPERVISOR_LOG_TIMEOUT_SEC = max(60, int(FUNCTION_TIMEOUT_SEC))
SUPERVISOR_KILL_TIMEOUT_SEC = 5

logging.getLogger('flask').setLevel('DEBUG')

logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

worker = flask.Blueprint('worker', __name__)


def pong(fileno):
    if fileno == 0:
        return
    s = socket.socket(fileno=fileno)
    headers = "HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"
    s.send(headers.encode('utf8'))
    s.close()


class LoadSocketResponder:
    def __init__(self, *, sockets):
        self.sockets = sockets

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_tb is exc_type is exc_val is None:
            message = b'HTTP/1.1 200 OK\r\nContent-Length: 22\r\n\r\nUser function is ready'
        else:
            exception_message = ''.join(format_exception(exc_type, exc_val, exc_tb)).encode('utf8')
            headers = ("HTTP/1.1 200 OK\r\n"
                       "X-Google-Status: load_error\r\n"
                       f"Content-Length: {len(exception_message)}\r\n\r\n")
            message = headers.encode('utf8') + exception_message

        for s in self.sockets:
            load_socket = socket.socket(fileno=s)
            load_socket.send(message)
            load_socket.close()


def main():
    supervisor = Supervisor(
        hostname=SUPERVISOR_HOSTNAME, port=int(SUPERVISOR_INTERNAL_PORT),
        log_timeout_secs=SUPERVISOR_LOG_TIMEOUT_SEC,
        kill_timeout_secs=SUPERVISOR_KILL_TIMEOUT_SEC)
    memory_handler = SupervisorHandler(
        supervisor, MAX_LOG_BATCH_ENTRIES, MAX_LOG_LENGTH, flushLevel=logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel('DEBUG')
    root_logger.addHandler(memory_handler)

    sockets = sorted(int(s) for s in os.environ['SOCKET_TRANSFERRENCE'].split('_'))
    server_socket = sockets[0]  # The first socket is the listening socket.

    application = flask.Flask(__name__)

    @application.route('/load', methods=['GET'])
    def load():
        return flask.Response('User function is ready', status=200)

    @application.route('/check', methods=['GET'])
    def check():
        return flask.Response('', status=200)

    @application.teardown_request
    def flush_logs(exc):
        memory_handler.flush_all()

    @application.route('/', defaults={"path": ''})
    @application.route('/<path:path>', methods=['GET', 'PUT', 'POST', 'DELETE', 'HEAD', 'PATCH'])
    def catch_all(path):
        data = dict(method=flask.request.method, json=flask.request.json, headers=flask.request.headers)
        res = f"Requested path has no associated handler: {path}\n\n{data!r}"
        logger.error(res)
        return flask.Response('', status=200)  # Just treat it as function success. The errror is logged.

    try:
        with LoadSocketResponder(sockets=sockets[1:]):
            spec = importlib.util.spec_from_file_location("cloud", f"{CODE_LOCATION_DIR}/user_code/cloud.py")
            cloud = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cloud)
            application.register_blueprint(cloud.blueprint, url_prefix='/execute')


        logger.debug(f'Welcome to python! Enjoy your stay.')
        memory_handler.flush_all()
        os.environ['WERKZEUG_SERVER_FD'] = str(server_socket)
        application.run(host='0.0.0.0', port=int(WORKER_PORT))
    except Exception as ex:
        logger.error(f"Failure: {ex}")
    finally:
        memory_handler.flush_all()
        supervisor.kill_instance()


if __name__ == '__main__':
    main()
