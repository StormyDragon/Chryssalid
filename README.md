# Chryssalid
Grow within your enemy, then burst out.

## I just want to get going
Ok.

### Prerequisites
* Docker
* Service Account json with `Google Cloud Functions Developer` role
* Pipenv
* Project with a `flask` blueprint and an entry point called `cloud.py`

#### `cloud.py`
```python
import flask
import cloud_functions

blueprint = flask.Blueprint('hello', __name__)


@blueprint.route('/')
def hello():
    return "Hello cloud functions."


cloud_functions.register_http_trigger(blueprint)
```

#### `Dockerfile`
```dockerfile
FROM stormydragon/gcf-python
CMD ['--http', '--project=<my project name>', '--name=<trigger name>']
```

#### Run these commands
```shell
pipenv install flask
docker build --tag my_cloud_function .
docker run --rm -it -v /path/to/service-account.json:/service-account.json:ro my_cloud_function
```

The container will package your project during build and by running it with the specified arguments
will deploy the package to Google Cloud Functions

## Objective
Replace google cloud function node interpreter with arbitrary code
Instead of using node as a shim, simply replace node.js and be master control program of the container.

### How does it work?
The node worker script `google_cloud_worker/worker.js` was built into the container by the cloud function deployment
machinery and is untouchable by our code until the `/load` endpoint is called, this is triggered by a "cold start"
before the first connection is made. Our code usurps the node process and executes our own, in the process handing the
connected `/load` and listening file descriptor to it, it is then that we send the answer to load, and
accept new connections on the listener.

## Worker needs
Google cloud functions consists of a webserver that accepts
three 'paths' as well as communication via http with a supervisor
service.

### Environment
* `X_GOOGLE_CODE_LOCATION`
* `X_GOOGLE_ENTRY_POINT`
* `X_GOOGLE_FUNCTION_TRIGGER_TYPE` - `HTTP_TRIGGER`, ``, ``
* `X_GOOGLE_FUNCTION_NAME`
* `X_GOOGLE_FUNCTION_TIMEOUT_SEC`
* `X_GOOGLE_WORKER_PORT` - Web server port
* `X_GOOGLE_SUPERVISOR_HOSTNAME`
* `X_GOOGLE_SUPERVISOR_INTERNAL_PORT`

### Variables
* `MAX_LOG_LENGTH = 5000`
* `MAX_LOG_BATCH_ENTRIES = 1500`
* `MAX_LOG_BATCH_LENGTH = 150000`
* `SUPERVISOR_KILL_TIMEOUT_MS = 500`
* `SUPERVISOR_LOG_TIMEOUT_MS`


### Paths
* `/load` - Not used after node.
* `/check` - Heartbeat, must return 200 OK
* `/execute` - POST - For execution of all non-http functions
* `/execute/*` - For HTTP will accept arbitrary paths.

### Response headers
* `X-Google-Status`: one of `crash`, `load_error`, `error` to indicate why the function died.

### Supervisor
Accept logs and kill command from worker

* `_ah/kill` - Notify of our need to die.
* `_ah/log`
```json
  {
    "Entries": [
      {
        "TextPayLoad": "...",
        "Severity": "INFO",
        "Time": "2018-01-01T00:00:00.000Z"
      }
    ]
  }
```

## Google Pub/Sub Events and Types

Events from firebase don't wrap the context in a sepate field.

### Firebase Auth
#### Event Resource Definition
`projects/<project name>`
#### Event Types
* `providers/firebase.auth/eventTypes/user.create`
* `providers/firebase.auth/eventTypes/user.delete`

### Firebase Firestore
#### Event Resource Definition
`projects/<project name>/databases/(default)/documents/<collection path>/{collectionId}`
#### Event Types
* `providers/cloud.firestore/eventTypes/document.create`
* `providers/cloud.firestore/eventTypes/document.update`
* `providers/cloud.firestore/eventTypes/document.delete`
* `providers/cloud.firestore/eventTypes/document.write`

### Firebase Realtime Database
#### Event Resource Definition
`projects/_/instances/<instance|project name>/refs/<path>/{key}`
#### Event Types
* `providers/google.firebase.database/eventTypes/ref.create`
* `providers/google.firebase.database/eventTypes/ref.write`
* `providers/google.firebase.database/eventTypes/ref.update`
* `providers/google.firebase.database/eventTypes/ref.delete`

### Pub Sub Topics
#### Event Resource Definition
`projects/<project name>/topics/<topic name>`
#### Event Types
* `google.pubsub.topic.publish`

### Cloud Storage
#### Event Resource Definition
`projects/<project name>/buckets/<bucket name>`
#### Event Types
* `google.storage.object.finalize`
* `google.storage.object.metadata_update`
* `google.storage.object.delete`
* `google.storage.object.archive`
