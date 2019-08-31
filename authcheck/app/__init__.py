import redis
from apscheduler.schedulers.blocking import BlockingScheduler
from app.common.func import *
from app.model.model import PolicyEnum
from app.conf.secret import *

app_path = os.path.dirname(os.path.realpath(__file__))

redis_pool = redis.ConnectionPool(host=redis_host, port=redis_port, db=redis_db, password=redis_password)

# 简单初始化两个账号，实际使用时可自行接入公司内部sso
users = {
    'admin': {
        'password': 'admin123',
        'role': [PolicyEnum.MANAGE.value, PolicyEnum.ACCESS.value]
    },
    'normal': {
        'password': 'normal123',
        'role': [PolicyEnum.ACCESS.value]
    }
}


def init():
    from threading import Thread
    from app.core.jobs import status_clear

    # 定时任务
    scheduler = BlockingScheduler()
    scheduler.add_job(status_clear, 'cron', hour=0)
    Thread(target=scheduler.start, daemon=True).start()

    # mongo
    from mongoengine import connect
    connect(
        mongo_database,
        username=mongo_user,
        password=mongo_password,
        host=mongo_host,
        port=mongo_port,
        connect=False
    )


def create_app():
    from flask import Flask
    from flask_cors import CORS
    from app.web import bp_api, bp_web, bp_ws
    from app.core.lib import ScanThread
    from app.conf.conf import cors_origin

    init()

    app = Flask(__name__)
    app.secret_key = secret_key

    CORS(bp_api, supports_credentials=True, origins=cors_origin)
    CORS(bp_ws, supports_credentials=True, origins=cors_origin)

    app.register_blueprint(bp_api)
    app.register_blueprint(bp_web)
    app.register_blueprint(bp_ws)

    # jinja2 function
    app.add_template_global(system_types, 'system_types')
    app.add_template_global(workspace_status, 'workspace_status')
    app.add_template_global(func_account, 'func_account')
    app.add_template_global(is_manager, 'is_manager')
    app.add_template_global(time_now, 'time_now')

    app.add_template_filter(time_show, 'time_show')
    app.add_template_filter(ws_roles, 'ws_roles')
    app.add_template_filter(format_json, 'json_show')
    app.add_template_filter(format_request, 'request_show')
    app.add_template_filter(format_response, 'response_show')
    app.add_template_filter(str_show, 'str_show')
    app.add_template_filter(request_num, 'request_num')

    # 开启扫描任务
    ScanThread().start()

    return app
