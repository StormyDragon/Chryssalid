from functools import wraps
from typing import Callable, Optional
import logging

import flask
from werkzeug.wsgi import DispatcherMiddleware

cloud_app: DispatcherMiddleware = None
logger = logging.getLogger()


def check(f):
    @wraps(f)
    def g(*args, **kwargs):
        if not cloud_app:
            raise RuntimeError("cloud_app was not set before calling functions in the module")
        return f(*args, **kwargs)

    return g


def fix_firebase_frame(frame: dict):
    """
    Firestore did not wrap the context, I will move things around a bit so it matches the pubsub frame
    :param frame:
    :return:
    """
    if 'resource' in frame:
        data = frame.pop('data')
        return dict(data=data, context=frame)
    return frame


@check
def register_callable_trigger(receiver: Callable[[dict, Optional[dict]], None]):
    """
    A callable trigger is essentially all other non-HTTP endpoints such as notifications from pubsub
    bucket updates, writes to firestore and etc.
    All calls are variants of notifications to topics
    :param receiver: Method which accepts the header, and the posted JSON.
    :return:
    """
    trigger = flask.Flask(__name__)

    @trigger.route('/_ah/push-handlers/pubsub/projects/<project>/topics/<topic>', methods=['POST'])
    def pubsub_handler(project, topic):
        header = {
            "project": project,
            "topic": topic,
            "request": flask.request
        }
        frame = flask.request.json
        frame = fix_firebase_frame(frame)
        receiver(header, frame)

    cloud_app.mounts['/execute'] = trigger
    logger.debug("mounted application pubsub call")


@check
def register_http_trigger(wsgi_application):
    """
    Register blueprint for HTTP trigger
    :type wsgi_application:
    :param wsgi_application:
    :return:
    """
    cloud_app.mounts['/execute'] = wsgi_application
    logger.debug("mounted application http call")
