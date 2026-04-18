import json
from urllib.parse import unquote_plus
import boto3
import os
import logging
print('Loading function')
logger = logging.getLogger()
logger.setLevel("INFO")
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
reckognition = boto3.client('rekognition')

table = dynamodb.Table(os.getenv("DYNAMO_TABLE"))


def lambda_handler(event, context):
    logger.info(json.dumps(event, indent=2))

    # Récupération du bucket et de la clé de l'objet uploadé
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = unquote_plus(event["Records"][0]["s3"]["object"]["key"])

    logger.info(f"Bucket : {bucket}")
    logger.info(f"Key : {key}")

    # Récupération de l'utilisateur et de l'UUID de la tâche
    # Le chemin est de la forme : user/id_publication/image_name
    user, task_id = key.split('/')[:2]
    logger.info(f"User : {user}")
    logger.info(f"Task id : {task_id}")

    # Reconstruction des clés DynamoDB (mêmes préfixes que dans app.py)
    user_key = f"USER#{user}"
    post_id = task_id


    # Appel à Rekognition pour détecter les labels de l'image
    label_data = reckognition.detect_labels(
        Image={
            "S3Object": {
                "Bucket": bucket,
                "Name": key
            }
        },
        MaxLabels=5,
        MinConfidence=0.75
    )
    logger.info(f"Labels data : {label_data}")

    # Récupération des résultats des labels
    labels = [label["Name"] for label in label_data["Labels"]]
    logger.info(f"Labels detected : {labels}")

    # Mise à jour de la table DynamoDB : ajout de l'image (path S3) et des labels
    response = table.update_item(
        Key={
            "user": user_key,
            "id": post_id,
        },
        UpdateExpression="SET #img = :image_val, #lbl = :labels_val",
        ExpressionAttributeNames={
            "#img": "image",
            "#lbl": "label",
        },
        ExpressionAttributeValues={
            ":image_val": key,
            ":labels_val": labels,
        },
    )
    logger.info(f"Update response : {response}")

    return {"statusCode": 200, "labels": labels}