# Chryssalid
Grow within your enemy, then burst out.

## Objective
Replace google cloud function node interpreter with arbitrary code
Instead of using node as a shim, simply replace node.js and be master control program of the container.

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
