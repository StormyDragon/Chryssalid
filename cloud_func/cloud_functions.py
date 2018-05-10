from functools import wraps
from typing import Callable, Optional

import flask

cloud_app: flask.Flask = None


def check(f):
    @wraps(f)
    def g(*args, **kwargs):
        if not cloud_app:
            raise RuntimeError("cloud_app was not set before calling functions in the module")
        return f(*args, **kwargs)

    return g


def fix_firestore_frame(frame: dict):
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
    trigger = flask.Blueprint('bucket_trigger', __name__)

    @trigger.route('_ah/push-handlers/pubsub/projects/<str:project>/topics/<str:topic>', methods=['POST'])
    def pubsub_handler(project, topic):
        header = {
            "project": project,
            "topic": topic,
            "request": flask.request
        }
        frame = flask.request.json
        frame = fix_firestore_frame(frame)
        receiver(header, frame)

    cloud_app.register_blueprint(trigger, url_prefix='/execute')


@check
def register_http_trigger(blueprint: flask.Blueprint):
    """
    Register blueprint for HTTP trigger
    :type blueprint: flask.Blueprint
    :param blueprint:
    :return:
    """
    cloud_app.register_blueprint(blueprint, url_prefix='/execute')
