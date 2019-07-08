#(C) Copyright 2018 Hewlett Packard Enterprise Development LP

import bottle
import requests
import json
import os
import subprocess
import time
import logging
import boto3
import os
from botocore.exceptions import ClientError

X_BROKER_API_MAJOR_VERSION = 2
X_BROKER_API_MINOR_VERSION = 3
X_BROKER_API_VERSION_NAME = 'X-Broker-API-Version'
ec2_instance_id =''
ec2_ip_addr = ''

# UPDATE THIS FOR YOUR ECHO SERVICE DEPLOYMENT
# service endpoint templates
service_binding = "http://localhost:8090/echo/{{instance_id}}/{{binding_id}}"

#GUID (or UUID) is an acronym for 'Globally Unique Identifier' (or 'Universally Unique Identifier'). It is a 128-bit integer number used to identify resources.
#sudo pip install gunicorn
# services
service = {
    "name": "grommet",
    "id": "97ca7e25-8f63-44a7-99d1-a75729ebfb5e",
    "description": "grommet service",
    "tags": ["ui", "grommet"],
    "requires": ["route_forwarding"],
    "bindable": True,
    "metadata": {
      "provider": {
        "name": "The grommet"
      },
      "listing": {
        "imageUrl": "http://example.com/cat.gif",
        "blurb": "Add a blurb here",
        "longDescription": "UI component library, in a galaxy far far away..."
      },
      "displayName": "The Grommet Broker"
    },
    "dashboard_client": {
      "id": "7cc087aa-e978-4e66-9e3f-820024d05868",
      "secret": "277cabb0-XXXX-XXXX-XXXX-7822c0a90e5d",
      "redirect_uri": "http://localhost:1234"
    },
    "plan_updateable": True,
    "plans": [{
      "name": "grommet-plan-1",
      "id": "2a44ed0e-2c09-4be6-8a81-761ddba2f733",
      "description": "Grommet-plan-1",
      "free": False,
      "metadata": {
        "max_storage_tb": 5,
        "costs":[
            {
               "amount":{
                  "usd":99.0
               },
               "unit":"MONTHLY"
            },
            {
               "amount":{
                  "usd":0.99
               },
               "unit":"1GB of messages over 20GB"
            }
         ],
        "bullets": [
          "Shared fake server",
          "5 TB storage",
          "40 concurrent connections"
        ]
      },
      "schemas": {
        "service_instance": {
          "create": {
            "parameters": {
              "$schema": "http://json-schema.org/draft-04/schema#",
              "type": "object",
              "properties": {
			  "region": {
			      "index": 0,
                  "description": "specify the aws region.",
                  "type": "string"
                },
			    "Access_Key_ID": {
			      "index": 1,
                  "description": "specify the aws account Access Key ID.",
                  "type": "string"
                },
				"Secret_Access_Key": {
				  "index": 2,
                  "description": "specify the aws account Secret Access Key.",
                  "type": "string"
                },
				"Image_ID": {
				  "index": 3,
                  "description": "ID of AMI to launch, such as 'ami-XXXX'",
                  "type": "string"
                },
				"Flavor": {
				  "index": 4,
                  "description": "Select the instance type",
				  "type": "object",
				  "allowedValues": ["t2.micro","t2.small"]
                },
                "NodeJS_version": {
                  "index": 5,
                  "description": "select the nodejs version.",
                  "type": "object",
                  "allowedValues": ["10.15.3","12.1.0"] 
                }
              }
            }
          },
          "update": {
            "parameters": {
              "$schema": "http://json-schema.org/draft-04/schema#",
              "type": "object",
              "properties": {
                "Ubuntu_URL": {
                  "description": "specify the ubuntu url.",
                  "type": "string"
                }
              }
            }
          }
        },
        "service_binding": {
          "create": {
            "parameters": {
              "$schema": "http://json-schema.org/draft-04/schema#",
              "type": "object",
              "properties": {
                "Ubuntu_URL": {
                  "description": "specify the ubuntu url.",
                  "type": "string"
                }
              }
            }
          }
        }
      }
    }, {
      "name": "grommet-plan-2",
      "id": "e3c4f66b-b7ae-4f64-b5a3-51c910b19ac0",
      "description": "grommet-plan-2",
      "free": False,
      "metadata": {
        "max_storage_tb": 5,
        "costs":[
            {
               "amount":{
                  "usd":199.0
               },
               "unit":"MONTHLY"
            },
            {
               "amount":{
                  "usd":0.99
               },
               "unit":"1GB of messages over 20GB"
            }
         ],
        "bullets": [
          "40 concurrent connections"
        ]
      }
    }]
}

@bottle.error(401)
@bottle.error(409)
def error(error):
    bottle.response.content_type = 'application/json'
    return '{"error": "%s"}' % error.body

def authenticate(username, password):
    return True

"""
def authenticate(username, password):
    print(username, password, "<--Username/Password")
    if username != config.osb_connector_username:
        print("Wrong username")
        return False
    if password != config.osb_connector_password:
        print("Wrong password")
        return False
    return True
"""
	
@bottle.route('/v2/service_instances/<instance_id>/last_operation', method='GET')
@bottle.auth_basic(authenticate)
def last_operation(instance_id):
    """
    Return the catalog of services handled
    by this broker

    GET /v2/service_instances/<instance_id>/last_operation

    HEADER:
        X-Broker-API-Version: <version>

    return:
        JSON document with details about the
        services offered through this broker
    """
    api_version = bottle.request.headers.get('X-Broker-API-Version')
    if (not api_version or not (api_version_is_valid(api_version))):
        bottle.abort(
            409,
            "Missing or incompatible %s. Expecting version %.0f.%.0f or later" % (
                X_BROKER_API_VERSION_NAME,
                X_BROKER_API_MAJOR_VERSION,
                X_BROKER_API_MINOR_VERSION))
    print("inside last operation")
    print("instance_id",instance_id)
    print("ec2_instance_id inside last operation",ec2_instance_id)
    global ec2_ip_addr
    ec2_ip_addr,state = get_public_ip_address(ec2_instance_id)
    print("inside last operation ec2_ip_addr,state ",ec2_ip_addr,state)
    if (state == u'pending'):
        print("inside lat operation pending")
        return {"state": "in progress"}
    else:
        print("inside lat operation succeeded")
        return {"state": "succeeded"}
		
	
def get_public_ip_address(instanceId):
    # When passed a tag key, tag value this will return a list of InstanceIds that were found.
    ec2client = boto3.client('ec2')
    print("instance id insed get public ip addr",instanceId)
    boto3.set_stream_logger('boto3.resources', logging.INFO)
    response = ec2client.describe_instances(InstanceIds=[instanceId,])
    for reservation in (response["Reservations"]):
        for instance in reservation["Instances"]:
            public_ip_address = (instance["PublicIpAddress"])
            state_status = instance['State']['Name']
            print("inside get public ip address :::: public_ip_address,state_status",public_ip_address,state_status)
    return public_ip_address,state_status

@bottle.route('/v2/catalog', method='GET')
@bottle.auth_basic(authenticate)
def catalog():
    """
    Return the catalog of services handled
    by this broker

    GET /v2/catalog:

    HEADER:
        X-Broker-API-Version: <version>

    return:
      JSON document with details about the
      services offered through this broker

      Using OSB Spec of Get Catalog:
      https://github.com/openservicebrokerapi/servicebroker/blob/v2.13/spec.md
    """
    api_version = bottle.request.headers.get('X-Broker-API-Version')
    if (not api_version or not (api_version_is_valid(api_version))):
        bottle.abort(
            409,
            "Missing or incompatible %s. Expecting version %.0f.%.0f or later" % (
                X_BROKER_API_VERSION_NAME,
                X_BROKER_API_MAJOR_VERSION,
                X_BROKER_API_MINOR_VERSION))
    return {"services": [service]}

def api_version_is_valid(api_version):
    version_data = api_version.split('.')
    result = True
    if (float(version_data[0]) < X_BROKER_API_MAJOR_VERSION
        or (float(version_data[0]) == X_BROKER_API_MAJOR_VERSION
            and float(version_data[1]) < X_BROKER_API_MINOR_VERSION)):
                result = False
    return result


@bottle.route('/v2/service_instances/<instance_id>', method='PUT')
@bottle.auth_basic(authenticate)
def provision(instance_id):
    """
    Provision an instance of this service
    for the given org and space

    PUT /v2/service_instances/<instance_id>:
        <instance_id> is provided by the Cloud
          Controller and will be used for future
          requests to bind, unbind and deprovision

    BODY:
        {
          "service_id":        "<service-guid>",
          "plan_id":           "<plan-guid>",
          "organization_guid": "<org-guid>",
          "space_guid":        "<space-guid>"
        }

    return:
        JSON document with details about the
        services offered through this broker
    """
    if bottle.request.content_type != 'application/json':
        bottle.abort(415, 'Unsupported Content-Type: expecting application/json')
    # get the JSON document in the BODY
    provision_details = bottle.request.json
    print("Inside provision function")
    print("provision_details",provision_details)

    planId = bottle.request.json['plan_id']
    serviceId = bottle.request.json['service_id']
    parameters = bottle.request.json['parameters']
    print("parameters",parameters)
    print("planId",planId)
# Assign these values before running the program
    access_key_id = parameters.get('Access_Key_ID')
    access_key_id = 'AKIAUWDMTYRVJOHOCP4V'
    print("access_key_id",access_key_id)
    secret_access_key = parameters.get('Secret_Access_Key')
    secret_access_key = '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'
    print("secret_access_key",secret_access_key)
    image_id = parameters.get('Image_ID')
    image_id = 'ami-05f07ee3c7aaadaaa'
    print("image_id",image_id)
    instance_type = parameters.get('Flavor')
    print("instance_type",instance_type)
    region = parameters.get('region')
    region ='us-east-1'
    print("region",region)
	
    #image_id = 'ami-05f07ee3c7aaadaaa'
    keypair_name = 'ec2-keypair'
    user_data = open(os.getcwd() + '/cloudinit.txt', 'r').read()
    #user_data = open(os.getcwd() + '/userdata.txt', 'r').read()
    print("user data", user_data)
    hd = os.path.expanduser('~')
    directory = hd + '/.aws'
    print("hd",hd)
    print("directory",directory)
    if not os.path.exists(directory):
        print("not exist")
        os.mkdir(os.path.join(hd, '.aws'))
    with open (hd+"/.aws/credentials", 'w+') as credentials:
        credentials.write('[default]' + '\n' + 'aws_access_key_id = ' + access_key_id + '\n' + 'aws_secret_access_key = ' + secret_access_key)
    with open (hd+"/.aws/config", 'w+') as config:
        config.write('[default]' + '\n' + 'region =' + region + '\n' + 'output =json')
	
    # Provision and launch the EC2 instance
    instance_info = create_ec2_instance(image_id, instance_type, keypair_name, user_data)
    print("instance infoooooooo",instance_info)
    global ec2_instance_id
    ec2_instance_id = instance_info["InstanceId"]
    print("ec2_instance_id inside provision",ec2_instance_id)
    bottle.response.status = 202
    #ec2_ip_addr = instance_info['Instances'][0]['PublicIpAddress']
    print("public address inside provision", ec2_ip_addr)
    dashboard_url = "http://"+ec2_ip_addr+":3000"
    return {"dashboard_url": dashboard_url} 
    #return {"public ipaddress": ec2_ip_addr}

def create_ec2_instance(image_id, instance_type, keypair_name, user_data):
    """Provision and launch an EC2 instance

    The method returns without waiting for the instance to reach
    a running state.

    :param image_id: ID of AMI to launch, such as 'ami-XXXX'
    :param instance_type: string, such as 't2.micro'
    :param keypair_name: string, name of the key pair
    :return Dictionary containing information about the instance. If error,
    returns None.
    """

    # Provision and launch the EC2 instance
    ec2_client = boto3.client('ec2')
    try:
        response = ec2_client.run_instances(ImageId=image_id,
                                            InstanceType=instance_type,
                                            KeyName=keypair_name,
                                            MinCount=1,
                                            MaxCount=1,
											UserData=user_data,
											SecurityGroups=[
                                                'AllowSSHandOSB',
                                            ]
		                                    )
        instance = response['Instances'][0]
        print "Instance  %s" % instance
        print "Instance State name []: %s" % instance['State']['Name']
        #while instance['State']['Name'] == u'pending':
        #    print "Instance State: %s" % instance['State']['Name']
        #    time.sleep(5)
        #    instance.update()
    except ClientError as e:
        logging.error(e)
        return None
 
    
    return response['Instances'][0]

@bottle.route('/v2/service_instances/<instance_id>', method='DELETE')
@bottle.auth_basic(authenticate)
def deprovision(instance_id):
    """
    Deprovision an existing instance of this service

    DELETE /v2/service_instances/<instance_id>:
        <instance_id> is the Cloud Controller provided
          value used to provision the instance

   return:
        As of API 2.3, an empty JSON document
        is expected
    """
    # send response
    #ec2_client = boto3.client('ec2')
	#ec2.Instance('i-00434b87058703892').terminate()
    #ec2.instances.filter(InstanceIds=ids).terminate()
    return {}

@bottle.route('/v2/service_instances/<instance_id>/service_bindings/<binding_id>', method='PUT')
@bottle.auth_basic(authenticate)
def bind(instance_id, binding_id):
    """
    Bind an existing instance with the
    for the given org and space

    PUT /v2/service_instances/<instance_id>/service_bindings/<binding_id>:
        <instance_id> is the Cloud Controller provided
          value used to provision the instance
        <binding_id> is provided by the Cloud Controller
          and will be used for future unbind requests

    BODY:
        {
          "plan_id":           "<plan-guid>",
          "service_id":        "<service-guid>",
          "app_guid":          "<app-guid>"
        }

    return:
        JSON document with credentails and access details
        for the service based on this binding
        http://docs.cloudfoundry.org/services/binding-credentials.html
    """
    if bottle.request.content_type != 'application/json':
        bottle.abort(415, 'Unsupported Content-Type: expecting application/json')
    # get the JSON document in the BODY
    binding_details = bottle.request.json
    print(binding_details)
    bottle.response.status = 201
    uri ="http://"+ec2_ip_addr+":3000"
    return {"credentials": {"uri": uri, "username": "ubuntu"}}

@bottle.route('/v2/service_instances/<instance_id>/service_bindings/<binding_id>', method='DELETE')
@bottle.auth_basic(authenticate)
def unbind(instance_id, binding_id):
    """
    Unbind an existing instance associated
    with the binding_id provided

    DELETE /v2/service_instances/<instance_id>/service_bindings/<binding_id>:
        <instance_id> is the Cloud Controller provided
          value used to provision the instance
        <binding_id> is the Cloud Controller provided
          value used to bind the instance

    return:
        As of API 2.3, an empty JSON document
        is expected
    """
    return {}

if __name__ == '__main__':
    port = int(os.getenv('PORT', '7099'))
    bottle.run(host='0.0.0.0', port=port, debug=True, reloader=False, server='gunicorn')
    #bottle.run(host='172.18.203.43', port=port, debug=True, reloader=False, certfile='/home/ubuntu/.minikube/ca.crt', keyfile='/home/ubuntu/.minikube/ca.key', server='gunicorn')
