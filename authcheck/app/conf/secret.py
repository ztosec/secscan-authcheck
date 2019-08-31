import os

# flask app
secret_key = b'\x00\x01\x02\x03\x04\x05'

# mongodb
mongo_database = os.environ['mongo_database']
mongo_host = os.environ['mongo_host']
mongo_port = int(os.environ['mongo_port'])
mongo_user = os.environ.get('mongo_user')
mongo_password = os.environ.get('mongo_password')


# redis
redis_host = os.environ['redis_host']
redis_port = int(os.environ['redis_port'])
redis_db = int(os.environ['redis_db'])
redis_password = os.environ.get('redis_password')
