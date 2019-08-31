#! ./venv/bin/python3
# -*- encoding: utf-8 -*-
from app import create_app

app = create_app()

if __name__ == '__main__':
    host = '127.0.0.1'
    port = 8888
    print("start in http://{}:{}/".format(host, port))
    app.run(host=host, port=port)
