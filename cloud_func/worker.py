import importlib.util
import logging
import os
import socket
import sys
from traceback import format_exception

import flask
from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware

import cloud_functions
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
            step = None
            try:
                step = "Pickup"
                load_socket = socket.socket(family=socket.AF_INET6, type=socket.SOCK_STREAM, fileno=s)
                step = "Send"
                load_socket.send(message)
                step = "Close"
                load_socket.close()
            except Exception as ex:
                logger.debug(f'socket {s} errored during {step} with {ex}')


def build_worker_app(flushable_log_handler):
    application = flask.Flask(__name__)

    @application.route('/load', methods=['GET'])
    def load():
        return flask.Response('User function is ready', status=200)

    @application.route('/check', methods=['GET'])
    def check():
        return flask.Response('OK', status=200)

    @application.teardown_request
    def flush_logs(exc):
        flushable_log_handler.flush_all()

    @application.route('/', defaults={"path": ''})
    @application.route('/<path:path>', methods=['GET', 'PUT', 'POST', 'DELETE', 'HEAD', 'PATCH'])
    def catch_all(path):
        data = dict(method=flask.request.method, json=flask.request.json, headers=flask.request.headers)
        res = f"Requested path has no associated handler: {path}\n\n{data!r}"
        logger.error(res)
        return flask.Response('', status=200)  # Just treat it as function success. The errror is logged.

    return application


def main():
    supervisor = Supervisor(
        hostname=SUPERVISOR_HOSTNAME, port=int(SUPERVISOR_INTERNAL_PORT),
        log_timeout_secs=SUPERVISOR_LOG_TIMEOUT_SEC,
        kill_timeout_secs=SUPERVISOR_KILL_TIMEOUT_SEC)
    memory_handler = SupervisorHandler(
        supervisor, MAX_LOG_BATCH_ENTRIES, MAX_LOG_LENGTH, flushLevel=logging.INFO)

    root_logger = logging.getLogger()
    if SUPERVISOR_HOSTNAME is None:
        root_logger.setLevel('ERROR')
    else:
        root_logger.setLevel('DEBUG')
        root_logger.addHandler(memory_handler)

    sockets = sorted(int(s) for s in os.environ['SOCKET_TRANSFERRENCE'].split('_'))
    server_socket = sockets[0]  # The first socket is the listening socket.

    application = build_worker_app(memory_handler)
    dispatcher = DispatcherMiddleware(application)

    try:
        cloud_functions.cloud_app = dispatcher
        with LoadSocketResponder(sockets=sockets[1:]):
            try:
                sys.path.append(f'{CODE_LOCATION_DIR}/user_code')
                spec = importlib.util.spec_from_file_location("cloud", f"{CODE_LOCATION_DIR}/user_code/cloud.py")
                cloud = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cloud)
            except FileNotFoundError:
                logger.error("User code module was not found")
            except Exception as ex:
                logger.error(f"something else? {ex}")

        memory_handler.can_flush = True
        logger.debug(f'Welcome to python {sys.version}! Enjoy your stay.')

        def writable(log_func):
            class X:
                @classmethod
                def write(cls, line):
                    log_func(line)

                @classmethod
                def flush(cls):
                    pass

            return X

        sys.stdout = writable(root_logger.debug)
        sys.stderr = writable(root_logger.error)

        memory_handler.flush_all()
        os.environ['WERKZEUG_SERVER_FD'] = str(server_socket)
        run_simple('0.0.0.0', int(WORKER_PORT), dispatcher, use_debugger=True)
    except Exception as ex:
        logger.error(f"Failure: {ex}")


if __name__ == '__main__':
    main()
