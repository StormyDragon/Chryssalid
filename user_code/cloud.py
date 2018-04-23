import logging

import flask

blueprint = flask.Blueprint('user_function', __name__)
logger = logging.getLogger(__name__)


@blueprint.route('/')
def hello():
    logger.info("Hoy!")
    return "Hello from Python!"
