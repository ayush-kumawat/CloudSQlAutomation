# from flask import Flask
from flask import Flask, request
from flask import Response
from werkzeug.datastructures import ImmutableDict
import requests
import datetime
import base64
import os
from pprint import pprint
from time import sleep
from timeit import default_timer
from gcsql_admin import CloudSqlAdmin
import sys
import google.auth.transport.requests
import google.oauth2.id_token
import google.auth
import json
from googleapiclient import discovery

app = Flask('post method')

from config import MY_PROJECT, RUN_URL

@app.route("/proxysql", methods=["POST"])
def proxy():
    envelope = request.get_json()
    if not envelope:
        msg = "no Pub/Sub message received"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    if not isinstance(envelope, dict) or "message" not in envelope:
        msg = "invalid Pub/Sub message format"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    pubsub_message = envelope["message"]

    name = "World"
    if isinstance(pubsub_message, dict) and "data" in pubsub_message:
        name = base64.b64decode(pubsub_message["data"]).decode("utf-8").strip()
        # return ("", 204)

    print(f"Hello {name}!")
    sys.stdout.flush()
    msg = json.loads(name)
    print(type(msg))
    sys.stdout.flush()
    credentials, project_id = google.auth.default()
    credentials.refresh(google.auth.transport.requests.Request())
    service = discovery.build('sqladmin', 'v1beta4', credentials=credentials)
    ans = []
    print(type(ans))
    sys.stdout.flush()
    requestA = service.instances().list(project=MY_PROJECT)
    while requestA is not None:
        responseA = requestA.execute()
    #    print(type(response))
        for database_instance in responseA['items']:
            # TODO: Change code below to process each `database_instance` resource:
    #        pprint(database_instance['name'])
            if 'autorep' in database_instance['name']:
                ans.append(database_instance['name'])

        requestA = service.instances().list_next(previous_request=requestA, previous_response=responseA)
    if len(ans) >= 1:
        print(ans[0])
        sys.stdout.flush()
        MY_INSTANCE = ans[0]

        print("Check {}",msg["incident"]["state"])
        sys.stdout.flush()
        if msg["incident"]["state"] == 'open':
            start_time = default_timer()
            sql_admin = CloudSqlAdmin()
            sleep(10)
            print('start')
            sys.stdout.flush()
            metadata = sql_admin.instances.get(MY_PROJECT, MY_INSTANCE)
            state = metadata["state"]
            if state == "RUNNABLE" :
                private_ip = metadata["ipAddresses"][0]["ipAddress"]
                payload="{\n    \"name\": \"%s\"\n}" % private_ip
                print(payload)
                sys.stdout.flush() 
                headers = {
                    'Content-Type': 'application/json'
                }
                # Change URLs with your webhook server URLs for deletion
                url = ["http://10.14.1.5:9001/hooks/webhook2-vm02","http://10.14.1.4:9001/hooks/webhook2-vm01","http://10.14.1.6:9001/hooks/webhook2-vm03","http://10.14.0.7:9001/hooks/webhook-del-vm01"]
                try:
                    for i in url:         
                        response = requests.request("POST", i, headers=headers, data=payload)
                        print(response)
                        sys.stdout.flush()
                    print('after webhook')
                    sys.stdout.flush()
                    sleep(10)
                    # credentials, project_id = google.auth.default()
                    # credentials.refresh(google.auth.transport.requests.Request())
                    auth_req = google.auth.transport.requests.Request()
                    id_token = google.oauth2.id_token.fetch_id_token(auth_req, RUN_URL)
                    print('id_token')
                    sys.stdout.flush()
                    print('after second token')
                    sys.stdout.flush()
                    headers = {
                        "Authorization": "Bearer {}".format(id_token), 
                        "Content-Type": "application/json"
                    }
                    # print('after webhook')
                    # sys.stdout.flush()
                    print('trigger delete')
                    sys.stdout.flush()
                    response = requests.post(RUN_URL + "/delete/" + MY_INSTANCE, timeout=1, headers=headers)
                    print(response)
                    sys.stdout.flush()
                except requests.Timeout:
                    print('timed out')
                    sys.stdout.flush()
                status_code = Response(status=200)
                return status_code
        else:
            print("status not open")
            sys.stdout.flush()
    else:
        print("minimum count reached")
        sys.stdout.flush()
        status_code = Response(status=200)
        return status_code
        # exit()

@app.route("/delete/<instance>", methods=["POST"])
def index(instance):

    url = 'https://sqladmin.googleapis.com/sql/v1beta4/projects/{}/instances/{}'.format(MY_PROJECT,instance)
    # name = "my instance"
    print('point after create')
    credentials, project_id = google.auth.default()
    credentials.refresh(google.auth.transport.requests.Request())
    headers = {
        "Authorization": "Bearer {}".format(credentials.token), 
        "Content-Type": "application/json"
    }
    print('deleting')
    x = requests.delete(url,headers=headers)
    print(x)
    sleep(600)
    # print(x.text)
    # sys.stdout.flush()
    print('second token')
    sys.stdout.flush()
    status_code = Response(status=200)
    return status_code

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 8080, debug = True)