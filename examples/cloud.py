import logging

import flask
import cloud_functions

flask_application = flask.Flask(__name__)
logger = logging.getLogger(__name__)


@flask_application.route('/', strict_slashes=False)
def hello():
    logger.info("Hoy!")
    return "Hello from Python!"


@flask_application.route('/_ah/push-handlers/pubsub/projects/<project>/topics/<topic>', methods=['POST'])
def call(project, topic):
    frame = cloud_functions.fix_firebase_frame(flask.request.json)
    logger.info(f"PUBSUB call :>   {frame}")
    return ""


cloud_functions.register_http_trigger(flask_application)
