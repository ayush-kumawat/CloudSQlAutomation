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

from config import MY_PROJECT, MY_INSTANCE, RUN_URL



@app.route("/create", methods=["POST"])
def index():
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
    print("Check {}",msg["incident"]["state"])
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
    if len(ans) <= 5:
        if msg["incident"]["state"] == 'open':
            url = 'https://sqladmin.googleapis.com/sql/v1beta4/projects/{}/instances'.format(MY_PROJECT)
            name = MY_INSTANCE + "-const-" + datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
            myobj = {
            "masterInstanceName": MY_INSTANCE,
            "project": MY_PROJECT,
            "databaseVersion": "MYSQL_5_7",
            "name": name,
            "region": "asia-south1",
            "settings":
                {
                    "tier": "db-custom-48-319488",
                    "userLabels": {"owner": "sql", "env": "prod", "final-read-replica": "true"},
                    "settingsVersion": 0,
                    "ipConfiguration": {"ipv4Enabled": False,
                                        "privateNetwork": 'projects/PROJECT_ID/global/networks/VPC_NAME'},
                    "databaseFlags": [{"name": "sql_mode","value": "ERROR_FOR_DIVISION_BY_ZERO"},{"name": "explicit_defaults_for_timestamp","value": "on"}]
                }
            }

            print('point after create')
            credentials, project_id = google.auth.default()
            credentials.refresh(google.auth.transport.requests.Request())
            headers = {
                "Authorization": "Bearer {}".format(credentials.token), 
                "Content-Type": "application/json"
            }
            print('first token new')
            x = requests.post(url,json = myobj,headers=headers)
            print(x)
            # print(x.text)
            # sys.stdout.flush()
            print('second token')
            sys.stdout.flush()
            auth_req = google.auth.transport.requests.Request()
            id_token = google.oauth2.id_token.fetch_id_token(auth_req, RUN_URL)
            print('after second token')
            sys.stdout.flush()
            headers = {
                "Authorization": "Bearer {}".format(id_token), 
                "Content-Type": "application/json"
            }
            print('before try block')
            sys.stdout.flush()
            try:
                print('try block')
                sys.stdout.flush()
                response = requests.post(RUN_URL + "/poll/" + name, timeout=1, headers=headers)
                print(response)
                sys.stdout.flush()
            except requests.Timeout:
                print('The request timed out')
                sys.stdout.flush() 
            status_code = Response(status=200)
            return status_code
            # print('creation success')
        else:
            print("status not open")
            # return 200
    else:
        print("maximun limit reached")
        sys.stdout.flush()

@app.route("/poll/<instance>", methods=["POST"])
def poll(instance):
    start_time = default_timer()
    sql_admin = CloudSqlAdmin()
    sleep(10)
    print('poll route')
    sys.stdout.flush()
    while True:
        metadata = sql_admin.instances.get(MY_PROJECT, instance)
        if "state" in metadata:
            state = metadata["state"]
        else:
            state = "not found"
            break
        print(
            (
                f"{default_timer() - start_time:9.4} seconds elapsed - "
                f"project: {MY_PROJECT}, instance: {instance}, state: {state}"
            )
        )
        sys.stdout.flush()
        if state == "RUNNABLE" :
            private_ip = metadata["ipAddresses"][0]["ipAddress"]
            payload="{\n    \"name\": \"%s\"\n}" % private_ip
            print(payload)
            sys.stdout.flush()
            headers = {
                'Content-Type': 'application/json'
            }
            # Change the URLs with your webhook server's URLs
            url = ["http://10.14.1.4:9000/hooks/webhook-vm01","http://10.14.1.5:9000/hooks/webhook-vm02","http://10.14.1.6:9000/hooks/webhook-vm03","http://10.14.0.7:9000/hooks/percona-webhook-vm01"]

            try:
                for i in url:         
                    response = requests.request("POST", i, headers=headers, data=payload)
                    print(response)
                    sys.stdout.flush()
            except requests.Timeout:
                print('Webhook request timed out')
                sys.stdout.flush() 
            break
        sleep(10)
    status_code = Response(status=200)
    return status_code

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 8080, debug = True)