# mongoDBと連携するための処理を書く
from decouple import config
from fastapi import HTTPException
from typing import Union
from bson import ObjectId
import motor.motor_asyncio
from auth_utils import AuthJwtCsrf
import asyncio

MONGO_API_KEY = config('MONGO_API_KEY')

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_API_KEY)
client.get_io_loop = asyncio.get_event_loop

database = client.API_DB

# mongoDBで設定したcollectionsと一致している必要がある
collection_todo = database.todo
collection_user = database.user
auth = AuthJwtCsrf()


def todo_serializer(todo) -> dict :
    return {
        "id" : str(todo["_id"]) ,
        "title" : todo["title"] ,
        "description" : todo["description"]
    }


def user_serializer(user) -> dict :
    return {
        "id" : str(user["_id"]) ,
        "email" : user["email"] ,
    }


async def db_create_todo(data: dict) -> Union[dict , bool] :
    todo = await collection_todo.insert_one(data)
    new_todo = await collection_todo.find_one({"_id" : todo.inserted_id})
    if new_todo :
        return todo_serializer(new_todo)
    return False


async def db_get_todos() -> list :
    todos = []
    # findで実際に通信は行われておらず、to_listで通信を行っている
    for todo in await collection_todo.find().to_list(length=100) :
        todos.append(todo_serializer(todo))
    return todos


async def db_get_single_todo(id: str) -> Union[dict , bool] :
    todo = await collection_todo.find_one({"_id" : ObjectId(id)})
    if todo :
        return todo_serializer(todo)
    return False


async def db_update_todo(id: str , data: dict) -> Union[dict , bool] :
    # idが存在するかのチェック
    todo = await collection_todo.find_one({"_id" : ObjectId(id)})
    if todo :
        updated_todo = await collection_todo.update_one(
            {"_id" : ObjectId(id)} ,
            # 更新するデータ
            {"$set" : data}
        )
        # データが更新されている場合は、modified_count(修正されたデータの数？)が0より大きい値で返ってくる
        if (updated_todo.modified_count > 0) :
            new_todo = await collection_todo.find_one({"_id" : ObjectId(id)})
            return todo_serializer(new_todo)
    return False


async def db_delete_todo(id: str) -> bool :
    todo = await collection_todo.find_one({"_id" : ObjectId(id)})
    if todo :
        delete_todo = await collection_todo.delete_one({"_id" : ObjectId(id)})
        # データが削除されている場合は、delete_count(削除されたデータの数？)が0より大きい値で返ってくる
        if (delete_todo.deleted_count > 0) :
            return True
        return False


async def db_signup(data: dict) -> dict :
    email = data.get("email")
    password = data.get("password")

    # dbにmailアドレスが登録されているかを確認
    overlap_user = await collection_user.find_one({"email" : email})
    if overlap_user :
        raise HTTPException(status_code=400, detail="Email is already taken")
    if not password or len(password) < 6 :
        raise HTTPException(status_code=400, detail="Password too short")

    # user情報を登録
    user = await collection_user.insert_one(
        {
            "email" : email ,
            # ハッシュ化されたパスワードで登録
            "password" : auth.generate_hashed_pw(password)
        }
    )

    new_user = await collection_user.find_one({"_id": user.inserted_id})

    return user_serializer(new_user)


async def db_login(data: dict) -> str:
    email = data.get("email")
    password = data.get("password")
    user = await collection_user.find_one({"email": email})

    # ハッシュ化されたパスワードと入力されたパスワードが一致するかを確認
    if not user or not auth.verify_pw(password, user["password"]):
        raise HTTPException(
            status_code=401, detail="Invalid email or password"
        )
    token = auth.encode_jwt(user["email"])

    return token

