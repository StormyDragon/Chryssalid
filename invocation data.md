# Invocations

## Google Storage
```python
{
    'data': {
        'bucket': 'stormweyr-trigger-bucket',
        'contentType': 'image/png',
        'crc32c': 'KuhXQQ==',
        'etag': 'CIDHl7/A+doCEAE=',
        'generation': '1525898933560192',
        'id': 'stormweyr-trigger-bucket/scintilating.png/1525898933560192',
        'kind': 'storage#object',
        'md5Hash': 'hlFmwimNla4lQTPpCHMSnw==',
        'mediaLink': 'https://www.googleapis.com/download/storage/v1/b/stormweyr-trigger-bucket/o/scintilating.png?generation=1525898933560192&alt=media',
        'metageneration': '1',
        'name': 'scintilating.png',
        'selfLink': 'https://www.googleapis.com/storage/v1/b/stormweyr-trigger-bucket/o/scintilating.png',
        'size': '1044156',
        'storageClass': 'REGIONAL',
        'timeCreated': '2018-05-09T20:48:53.558Z',
        'timeStorageClassUpdated': '2018-05-09T20:48:53.558Z',
        'updated': '2018-05-09T20:48:53.558Z'
    },
    'context': {
        'eventId': '95463401944740', 'timestamp': '2018-05-09T20:48:53.777Z',
        'eventType': 'google.storage.object.finalize',
        'resource': {
            'service': 'storage.googleapis.com',
            'name': 'projects/_/buckets/stormweyr-trigger-bucket/objects/scintilating.png',
            'type': 'storage#object'
        }
    }
}
```

## Firebase Auth
```python
{
    'data': {
        'email': '______@stormweyr.dk',
        'metadata': {'createdAt': '2018-05-10T13:59:09Z'},
        'uid': 'X5svJfCay8hCol8wp4j34y29EIw2'
    },
    'context': {
        'eventId': '74c8bbbc-fc8f-450f-8543-28a03a5db6de',
        'eventType': 'providers/firebase.auth/eventTypes/user.create',
        'notSupported': {},
        'resource': 'projects/stormweyr',
        'timestamp': '2018-05-10T13:59:09.919Z'
    }
}
```

## Firebase Firestore
```python
{
    'data': {
        'oldValue': {},
        'updateMask': {},
        'value': {
            'createTime': '2018-05-09T20:43:07.288911Z',
            'fields': {'what': {'stringValue': 'really?'}},
            'name': 'projects/stormweyr/databases/(default)/documents/trigger-firestore/qW0tKNNcURsuae83i8t1',
            'updateTime': '2018-05-09T20:43:07.288911Z'
        }
    },
    'context': {
        'eventId': '1178a95f-fb05-4761-8023-c3d74bfa3c77-0',
        'eventType': 'providers/cloud.firestore/eventTypes/document.create',
        'notSupported': {},
        'params': {'unique': 'qW0tKNNcURsuae83i8t1'},
        'resource': 'projects/stormweyr/databases/(default)/documents/trigger-firestore/qW0tKNNcURsuae83i8t1',
        'timestamp': '2018-05-09T20:43:07.288911Z'
    }
}
```

## Firebase Realtime Database
``` python
{
    'data': {
        'data': None, 'delta': {'depth': {'please': True}}
    },
    'context': {
        'eventType': 'providers/google.firebase.database/eventTypes/ref.create',
        'params': {'entry': 'more'},
        'auth': {'admin': True},
        'resource': 'projects/_/instances/stormweyr/refs/trigger/more',
        'timestamp': '2018-05-10T16:34:06.184Z',
        'eventId': 'gssPQAHOPr0vtzA647CyG+bqF5U='
    }
}
```
