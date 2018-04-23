# Chryssalid
Grow within your enemy, then burst out.

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
