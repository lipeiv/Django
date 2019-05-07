from itsdangerous import TimedJSONWebSignatureSerializer
from django.conf import settings
from itsdangerous import BadData


def generate_access_token(openid):

    serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, expires_in=300)

    data = {
        'openid': openid
    }

    # dumps()函数的返回值是一个bytes类型: 需要解码:decode()
    token = serializer.dumps(data)

    return token.decode()


def check_access_token(access_token):

    # 解密:
    serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, expires_in=300)

    try:
        # loads(): 把token扔进来, 得到解密之后的内容:
        data = serializer.loads(access_token)

    except BadData:

        return None

    else:

        return data.get('openid')
