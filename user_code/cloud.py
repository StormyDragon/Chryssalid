import logging

import flask
import cloud_functions

blueprint = flask.Blueprint('user_function', __name__)
logger = logging.getLogger(__name__)


@blueprint.route('/')
def hello():
    logger.info("Hoy!")
    return "Hello from Python!"


@blueprint.route('_ah/push-handlers/pubsub/projects/<str:project>/topics/<str:topic>', methods=['POST'])
def call(project, topic):
    frame = cloud_functions.fix_firestore_frame(flask.request.json)
    logger.info(f"PUBSUB call :>   {frame}")
    return ""


cloud_functions.register_http_trigger(blueprint)
