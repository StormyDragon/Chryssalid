import flask
import structlog

from flask import request

logger = structlog.get_logger()

app = flask.Flask(__name__)
app.use_reloader = False


@app.route('/_ah/log', methods=['POST'])
def log():
    logger.info("received logs from remote", records=request.json)
    return flask.Response('', status=200)


@app.route('/_ah/kill', methods=['POST'])
def kill():
    logger.info("received kill signal from server")
    return flask.Response('', status=200)


def main():
    logger.info("starting flask server on thread")
    app.run(host='0.0.0.0', port=8080)


if __name__ == '__main__':
    main()
