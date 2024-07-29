from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app


def generate_confirmation_token(key, expiration=3600):
    s = Serializer(current_app.config.get('SECRET_KEY'), expiration)
    token = s.dumps({'confirm': key}).decode('utf-8')
    return token


def verify_confirmation_token(token):
    s = Serializer(current_app.config.get('SECRET_KEY'))
    try:
        data = s.loads(token.encode('utf-8'))
    except:
        return False
    return data