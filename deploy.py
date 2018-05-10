import json
from contextlib import contextmanager
from pprint import pprint

import click
import requests
from googleapiclient import discovery
from googleapiclient.errors import HttpError

functions = discovery.build('cloudfunctions', 'v1beta2')


@contextmanager
def error_handler():
    try:
        yield
    except HttpError as ex:
        pprint(ex.resp)
        pprint(json.loads(ex.content))


def upload_package_zip(location):
    upload_response = functions.projects().locations().functions().generateUploadUrl(parent=location).execute()
    upload_location = upload_response['uploadUrl']
    with open('package.zip', 'rb') as file:
        response = requests.put(
            upload_location, data=file, headers={
                'content-type': 'application/zip',
                'x-goog-content-length-range': '0,104857600'
            }
        )
        response.raise_for_status()
    return upload_location


@click.command()
@click.option('--project')
@click.option('--location', default='us-central1')
@click.option('--prefix', default='test-trigger')
def main(project, location, prefix):
    project_location = f"projects/{project}/locations/{location}"
    upload_location = upload_package_zip(project_location)

    response = functions.projects().locations().functions().list(location=project_location).execute()
    names = [item['name'] for item in response['functions']]

    def create_or_update(location, name, *, body):
        if name in names:
            return functions.projects().locations().functions().update(name=name, body=body)
        else:
            return functions.projects().locations().functions().create(location=location, body=body)

    def name_f(name):
        return f"{project_location}/functions/{prefix}-{name}"

    func_name = name_f("firestore")
    body = {
        "name": func_name,
        "sourceUploadUrl": upload_location,
        "eventTrigger": {
            "eventType": "providers/cloud.firestore/eventTypes/document.create",
            "resource": f"projects/{project}/databases/" "(default)/documents/trigger-firestore/{unique}",
            # "failurePolicy": {"retry": {}}
        }
    }
    with error_handler():
        response = create_or_update(project_location, func_name, body=body).execute()
        pprint(response)

    func_name = name_f("http")
    body = {
        "name": func_name,
        "sourceUploadUrl": upload_location,
        "httpsTrigger": {}
    }

    with error_handler():
        response = create_or_update(project_location, func_name, body=body).execute()
        pprint(response)

    func_name = name_f("bucket")
    body = {
        "name": func_name,
        "sourceUploadUrl": upload_location,
        "eventTrigger": {
            "eventType": "google.storage.object.finalize",
            "resource": f"projects/{project}/buckets/{project}-trigger-bucket",
            # "failurePolicy": {"retry": {}}
        }
    }

    with error_handler():
        response = create_or_update(project_location, func_name, body=body).execute()
        pprint(response)

    func_name = name_f("topic")
    body = {
        "name": func_name,
        "sourceUploadUrl": upload_location,
        "eventTrigger": {
            "eventType": "google.pubsub.topic.publish",
            "resource": f"projects/{project}" "/topics/trigger-topic",
            # "failurePolicy": {"retry": {}}
        }
    }

    with error_handler():
        response = create_or_update(project_location, func_name, body=body).execute()
        pprint(response)

    func_name = name_f("realtime")
    body = {
        "name": func_name,
        "sourceUploadUrl": upload_location,
        "eventTrigger": {
            "eventType": "providers/google.firebase.database/eventTypes/ref.create",
            "resource": f"projects/_/instances/{project}" "/refs/trigger/{entry}",
            # "failurePolicy": {"retry": {}}
        }
    }

    with error_handler():
        response = create_or_update(project_location, func_name, body=body).execute()
        pprint(response)

    func_name = name_f("auth")
    body = {
        "name": func_name,
        "sourceUploadUrl": upload_location,
        "eventTrigger": {
            "eventType": "providers/firebase.auth/eventTypes/user.create",
            "resource": f"projects/{project}",
            # "failurePolicy": {"retry": {}}
        }
    }

    with error_handler():
        response = create_or_update(project_location, func_name, body=body).execute()
        pprint(response)


if __name__ == '__main__':
    main()
