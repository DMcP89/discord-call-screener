import boto3
import os
import json


dir_path = os.path.dirname(os.path.realpath(__file__))
with open(dir_path+'/config.json', 'r') as f:
    config = json.load(f)

ACCESS_KEY = config["S3"]["ACCESS_KEY_ID"]
SECRET_KEY = config["S3"]["SECRET_KEY_ID"]

s3 = boto3.resource(
    's3',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)


def save_recording_to_bucket(bucket, filename):
    s3.Object(bucket, filename).put(Body=open(filename, 'rb'))