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
    upload_location = upload_package_zip(location)
    project_location = f"projects/{project}/locations/{location}"

    response = functions.projects().locations().functions().list(location=location).execute()
    names = [item['name'] for item in response['functions']]

    def create_or_update(location, name, *, body):
        if name in names:
            return functions.projects().locations().functions().update(name=name, body=body)
        else:
            return functions.projects().locations().functions().create(location=location, body=body)

    name = f"{project_location}/functions/trigger-firestore"
    body = {
        "name": name,
        "sourceUploadUrl": upload_location,
        "eventTrigger": {
            "eventType": "providers/cloud.firestore/eventTypes/document.create",
            "resource": f"projects/{project}/databases/" + "(default)/documents/trigger-firestore/{unique}",
            # "failurePolicy": {"retry": {}}
        }
    }
    with error_handler():
        response = create_or_update(project_location, name, body=body).execute()
        pprint(response)

    name = f"{project_location}/functions/{prefix}-http"
    body = {
        "name": name,
        "sourceUploadUrl": upload_location,
        "httpsTrigger": {}
    }

    with error_handler():
        response = create_or_update(project_location, name, body=body).execute()
        pprint(response)

    name = f"{project_location }/functions/{prefix}-bucket"
    body = {
        "name": name,
        "sourceUploadUrl": upload_location,
        "eventTrigger": {
            "eventType": "google.storage.object.finalize",
            "resource": "projects/stormweyr/buckets/stormweyr-trigger-bucket",
            # "failurePolicy": {"retry": {}}
        }
    }

    with error_handler():
        response = create_or_update(project_location, name, body=body).execute()
        pprint(response)

    name = f"{project_location }/functions/{prefix}-topic"
    body = {
        "name": name,
        "sourceUploadUrl": upload_location,
        "eventTrigger": {
            "eventType": "google.pubsub.topic.publish",
            "resource": "projects/stormweyr/topics/trigger-topic",
            # "failurePolicy": {"retry": {}}
        }
    }

    with error_handler():
        response = create_or_update(project_location, name, body=body).execute()
        pprint(response)


if __name__ == '__main__':
    main()
