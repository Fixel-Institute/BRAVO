import datetime 
import os 
from cryptography.fernet import Fernet
from neomodel import Q

key = os.environ.get('ENCRYPTION_KEY')
secureEncoder = Fernet(key)

def current_time():
    return datetime.datetime.utcnow().timestamp()

def encryptMessage(message):
    return secureEncoder.encrypt(message.encode("utf-8")).decode("utf-8")

def decryptMessage(message):
    try:
        return secureEncoder.decrypt(message.encode("utf-8")).decode("utf-8")
    except:
        return message

def filterNodesByType(nodeset, nodeType, *args):
    return [item for item in nodeset.filter(*args).all() if type(item) == nodeType]

class AttrDict(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value
