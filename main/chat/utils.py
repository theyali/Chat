import uuid
import json
from decimal import Decimal
import hashlib
import time

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def generate_ref_code():
    code = str(uuid.uuid4()).replace('-','')[:12]
    return code



def generateAgoraToken(channelName, uid, appID, appCertificate, role, privilegeExpiredTs):
    token = '006' + appID + hashlib.md5((channelName + str(uid) + appCertificate + str(role) + str(privilegeExpiredTs)).encode()).hexdigest() + str(role) + str(privilegeExpiredTs)
    return token
