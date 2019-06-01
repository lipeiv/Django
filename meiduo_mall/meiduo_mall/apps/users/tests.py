from django.test import TestCase

# Create your tests here.
import pickle
import base64

if __name__ == '__main__':
    # 定义一个字典:
    cart_dict = {
        1: {
            'count': 2,
            'selected': True
        },
        3: {
            'count': 3,
            'selected': False
        }
    }

    # result_bytes = pickle.dumps(cart_dict)
    # print(result_bytes)
    #
    # result2_bytes = base64.b64encode(result_bytes)
    # print(result2_bytes)

    str = base64.b64encode(pickle.dumps(cart_dict)).decode()
    print(str)
    print(type(str))

    dict = pickle.loads(base64.b64decode(str))
    print(dict)
    print(type(dict))

