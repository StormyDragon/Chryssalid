from time import sleep

import click
import requests
from googleapiclient import discovery

functions = discovery.build('cloudfunctions', 'v1')


def create_or_update(body):
    project_location, _ = body['name'].split('/functions/', 1)
    response = functions.projects().locations().functions().list(parent=project_location).execute()
    names = [item['name'] for item in response.get('functions', [])]
    if body['name'] in names:
        return functions.projects().locations().functions().patch(name=body['name'], body=body)
    else:
        return functions.projects().locations().functions().create(location=project_location, body=body)


def upload_package_zip(package, project, location):
    project_location = f"projects/{project}/locations/{location}"
    upload_response = functions.projects().locations().functions().generateUploadUrl(parent=project_location).execute()
    upload_location = upload_response['uploadUrl']
    with open(package, 'rb') as file:
        response = requests.put(
            upload_location, data=file, headers={
                'content-type': 'application/zip',
                'x-goog-content-length-range': '0,104857600'
            }
        )
        response.raise_for_status()
    return upload_location


def deploy(package, project, location, name, *, body):
    upload_location = upload_package_zip(package, project, location)
    function_name = f'projects/{project}/locations/{location}/functions/{name}'
    response = create_or_update(body={
        "name": function_name,
        "sourceUploadUrl": upload_location,
        **body
    }).execute()
    version_id = response['metadata']['versionId']
    new_version = '0'
    while new_version != version_id:
        sleep(5)
        response = functions.projects().locations().functions().get(name=function_name).execute()
        new_version = response['versionId']
    print(f"Version {response['versionId']} deployed - status: {response['status']}")


def deploy_http(package, project, location, name):
    deploy(package, project, location, name, body={
        "httpsTrigger": {}
    })


def deploy_event(package, project, location, name, resource, event):
    deploy(package, project, location, name, body={
        "eventTrigger": {
            "eventType": event,
            "resource": resource
        }
    })


def check_event(ctx, param, value):
    trigger = ctx.params['trigger_type']
    if trigger == 'http' and value is not None:
        raise click.BadParameter(f'cannot use with http triggers')
    if value is None and trigger == 'event':
        raise click.BadParameter('value must be supplied')


@click.command()
@click.option('--name')
@click.option('--project')
@click.option('--package')
@click.option('--location', default='us-central1')
@click.option('--http', 'trigger_type', flag_value='http', is_eager=True)
@click.option('--event', 'trigger_type', flag_value='event', is_eager=True)
@click.option('--resource', callback=check_event)
@click.option('--event', callback=check_event)
def deploy_cloud_function(name, project, package, location, trigger_type, resource, event):
    print(f"Deploying {trigger_type} to {project}/{location}/{name}")
    if trigger_type == 'http':
        deploy_http(package, project, location, name)
    elif trigger_type == 'event':
        print(f"Event Type: {event}\nResource: {resource}")
        deploy_event(package, project, location, name, resource, event)
    else:
        raise ValueError("Must specify either of --http or --event")


if __name__ == '__main__':
    deploy_cloud_function()
