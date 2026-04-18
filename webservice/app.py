#################################################################################################
##                                                                                             ##
##                                 NE PAS TOUCHER CETTE PARTIE                                 ##
##                                                                                             ##
## 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 ##
import boto3
from botocore.config import Config
import os
import uuid
from dotenv import load_dotenv
from typing import Union
import logging
from fastapi import FastAPI, Request, status, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

load_dotenv()
from getSignedUrl import getSignedUrl



app = FastAPI()
logger = logging.getLogger("uvicorn")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
	logger.error(f"{request}: {exc_str}")
	content = {'status_code': 10422, 'message': exc_str, 'data': None}
	return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class Post(BaseModel):
    title: str
    body: str

my_config = Config(
    region_name='us-east-1',
    signature_version='v4',
)

dynamodb = boto3.resource('dynamodb', config=my_config)
table = dynamodb.Table(os.getenv("DYNAMO_TABLE"))
s3_client = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4'))
bucket = os.getenv("BUCKET")

## ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ##
##                                                                                                ##
####################################################################################################

def generate_image_url(object_key):
    return s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": object_key},
        ExpiresIn=3600
    )

def format_post(item):
    image_key = item.get("image")
    return {
        "user":item.get("user"),
        "id" : item.get("id"),
        "title": item.get("title"),
        "body": item.get("body"),
        "image": generate_image_url(image_key) if image_key else None,
        "labels": item.get("label") or None
    }

def get_posts_by_user(username):
    user_key = f"USER#{username}"
    response = table.scan(
        FilterExpression="#u = :user_val",
        ExpressionAttributeNames={"#u": "user"},
        ExpressionAttributeValues={":user_val": user_key},
    )
    return response.get("Items", [])


def get_all_posts_from_db():
    response = table.scan()
    return response.get("Items", [])


@app.post("/posts")
async def post_a_post(post: Post, authorization: str | None = Header(default=None)):
    """
    Poste un post ! Les informations du poste sont dans post.title, post.body et le user dans authorization
    """
    logger.info(f"title : {post.title}")
    logger.info(f"body : {post.body}")
    logger.info(f"user : {authorization}")

    post_id = f"POST#{uuid.uuid4()}"
    user_key = f"USER#{authorization}" 

    res = table.put_item(
        Item={
            "user": user_key,
            "id": post_id,
            "title": post.title,
            "body": post.body,
        }
    )


    # Doit retourner le résultat de la requête la table dynamodb
    return {"user": user_key, "id": post_id, "title": post.title, "body": post.body}


@app.get("/posts")
async def get_all_posts(user: Union[str, None] = None):
    """
    Récupère tout les postes. 
    - Si un user est présent dans le requête, récupère uniquement les siens
    - Si aucun user n'est présent, récupère TOUS les postes de la table !!
    """
    if user :
        logger.info(f"Récupération des postes de : {user}")
        items = get_posts_by_user(user)
    else :
        logger.info("Récupération de tous les postes")
        items = get_all_posts_from_db()
     # Doit retourner une liste de posts
    res = [format_post(item) for item in items]

    return res

    
@app.delete("/posts/{post_id}")
async def delete_post(post_id: str, authorization: str | None = Header(default=None)):
    # Doit retourner le résultat de la requête la table dynamodb
    logger.info(f"post id : {post_id}")
    logger.info(f"user: {authorization}")

    user_key = f"USER#{authorization}"
    # Récupération des infos du poste
    post_infos = table.get_item(Key={"user": user_key, "id": f"POST#{post_id}"})
    post = post_infos.get("Item")
    
    # S'il y a une image on la supprime de S3
    if post and post.get("image"):
        s3_client.delete_object(Bucket=bucket, Key=post["image"])
    # Suppression de la ligne dans la base dynamodb
    res = table.delete_item(Key={"user": user_key, "id": f"POST#{post_id}"})
    # Retourne le résultat de la requête de suppression
    return res



#################################################################################################
##                                                                                             ##
##                                 NE PAS TOUCHER CETTE PARTIE                                 ##
##                                                                                             ##
## 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 ##
@app.get("/signedUrlPut")
async def get_signed_url_put(filename: str,filetype: str, postId: str,authorization: str | None = Header(default=None)):
    return getSignedUrl(filename, filetype, postId, authorization)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")

## ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ##
##                                                                                                ##
####################################################################################################