import uuid
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def generate_ref_code():
    code = str(uuid.uuid4()).replace('-','')[:12]
    return code
