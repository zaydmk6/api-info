from import FreeFire_pb2, main_pb2, AccountPersonalShow_pb2
import httpx
import asyncio
import json
from google.protobuf import json_format, message
from google.protobuf.message import Message
from Crypto.Cipher import AES
import base64
from typing import Tuple


MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')
RELEASEVERSION = "OB48"
USERAGENT = "Dalvik/2.1.0 (Linux; U; Android 13; CPH2095 Build/RKQ1.211119.001)"
SUPPORTED_REGIONS = ["IND", "BR", "SG", "RU", "ID", "TW", "US", "VN", "TH", "ME", "PK", "CIS"]
ACCOUNTS = {'ME': "uid=4245081395&password=9FB4D5398792BF93F26620E01618B469379606F25FADA0A00E291F2276F30342"}


async def json_to_proto(json_data: str, proto_message: Message) -> bytes:
    json_format.ParseDict(json.loads(json_data), proto_message)
    serialized_data = proto_message.SerializeToString()
    return serialized_data
def pad(text: bytes) -> bytes:
    padding_length = AES.block_size - (len(text) % AES.block_size)
    padding = bytes([padding_length] * padding_length)
    return text + padding
def aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    aes = AES.new(key, AES.MODE_CBC, iv)
    padded_plaintext = pad(plaintext)
    ciphertext = aes.encrypt(padded_plaintext)
    return ciphertext
def decode_protobuf(encoded_data: bytes, message_type: message.Message) -> message.Message:
    message_instance = message_type()
    message_instance.ParseFromString(encoded_data)
    return message_instance



async def getAccess_Token(account):
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    payload = account + "&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"
    headers = {
        'User-Agent': USERAGENT,
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/x-www-form-urlencoded"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=payload, headers=headers)
        data = response.json()
        return data.get("access_token", "0"), data.get("open_id", "0")




async def create_jwt(region: str) -> Tuple[str, str, str]:
    account = ACCOUNTS.get(region)
    access_token, open_id = await getAccess_Token(account)
    json_data = json.dumps({
      "open_id": open_id,
      "open_id_type": "4",
      "login_token": access_token,
      "orign_platform_type": "4"
    })
    encoded_result = await json_to_proto(json_data, FreeFire_pb2.LoginReq())
    payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, encoded_result)
    url = "https://loginbp.ggblueshark.com/MajorLogin"
    headers = {
        'User-Agent': USERAGENT,
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/octet-stream",
        'Expect': "100-continue",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': RELEASEVERSION
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=payload, headers=headers)
        response_content = response.content
        message = json.loads(json_format.MessageToJson(decode_protobuf(response_content, FreeFire_pb2.LoginRes)))
        token = message.get("token", "0")
        region = message.get("lockRegion", "0")
        serverUrl = message.get("serverUrl", "0")
        return f"Bearer {token}", region, serverUrl



async def GetAccountInformation(ID, UNKNOWN_ID, regionMain, endpoint):
    json_data = json.dumps({
        "a": ID,
        "b": UNKNOWN_ID
    })
    encoded_result = await json_to_proto(json_data, main_pb2.GetPlayerPersonalShow())
    payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, encoded_result)
    regionMain = regionMain.upper()
    if regionMain in SUPPORTED_REGIONS:
        token, region, serverUrl = await create_jwt(regionMain)
    else:
        return {
            "error": "Invalid request",
            "message": f"Unsupported 'region' parameter. Supported regions are: {', '.join(SUPPORTED_REGIONS)}."
        }
    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 13; A063 Build/TKQ1.221220.001)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/octet-stream",
        'Expect': "100-continue",
        'Authorization': token,
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': RELEASEVERSION
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(serverUrl + endpoint, data=payload, headers=headers)
        response_content = response.content
        message = json.loads(json_format.MessageToJson(decode_protobuf(response_content, AccountPersonalShow_pb2.AccountPersonalShowInfo)))
        return message