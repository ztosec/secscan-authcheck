import time
from flask import Flask, redirect, url_for, session, request, jsonify, abort, render_template
from flask_oauthlib.client import OAuth

accounts = [
    {'id': '1', 'username': 'admin', 'password': '123456'},
    {'id': '2', 'username': 'normal', 'password': '123456'},
    {'id': '3', 'username': 'test', 'password': '123456'},
    {'id': '4', 'username': 'test2', 'password': '123456'},
    {'id': '5', 'username': 'test3', 'password': '123456'}
]

orders = [
    {'id': 1, 'order_no': '2017009171822298053', 'recv': '老王:18925139194', 'total_amount': '8444.44',
     'order_status': '待确认', 'order_time': '2017-08-17 18:22'},
    {'id': 2, 'order_no': '2017009171822298054', 'recv': '老王:18925139194', 'total_amount': '8444.44',
     'order_status': '待确认', 'order_time': '2016-08-17 18:22'},
    {'id': 3, 'order_no': '2017009171822298055', 'recv': '老王:18925139194', 'total_amount': '8444.44',
     'order_status': '待确认', 'order_time': '2017-08-17 18:22'},
    {'id': 4, 'order_no': '2017009171822298056', 'recv': '老王:18925139194', 'total_amount': '8444.44',
     'order_status': '待确认', 'order_time': '2018-08-17 18:22'},
    {'id': 5, 'order_no': '2017009171822298057', 'recv': '老王:18925139194', 'total_amount': '8444.44',
     'order_status': '待确认', 'order_time': '2017-08-17 18:22'},
    {'id': 6, 'order_no': '2017009171822298058', 'recv': '老王:18925139194', 'total_amount': '8444.44',
     'order_status': '待确认', 'order_time': '2019-08-17 18:22'}
]

own_orders = {
    'admin': [{
        'id': 1,
        'order_no': '2017009171822298053',
        'recv_phone': '13333333333',
        'send_phone': '14444444444',
        'amount': 998,
        'order_status': '已完成',
        'order_time': time.ctime()
    }, {
        'id': 2,
        'order_no': '2018009171822298053',
        'recv_phone': '13333333333',
        'send_phone': '14444444444',
        'amount': 1998,
        'order_status': '待确认',
        'order_time': time.ctime()
    }, {
        'id': 3,
        'order_no': '2019009171822298053',
        'recv_phone': '13333333333',
        'send_phone': '14444444444',
        'amount': 9998,
        'order_status': '已完成',
        'order_time': time.ctime()
    }],
    'normal': [{
        'id': 4,
        'order_no': '20180091738838333332',
        'recv_phone': '10000000001',
        'send_phone': '10000000002',
        'amount': 9,
        'order_status': '已完成',
        'order_time': time.ctime()
    }, {
        'id': 5,
        'order_no': '2018048484848484',
        'recv_phone': '10000000001',
        'send_phone': '10000000002',
        'amount': 19,
        'order_status': '待确认',
        'order_time': time.ctime()
    }]
}


def create_client(app):
    oauth = OAuth(app)

    api_error = lambda msg: jsonify({'flag': 'error', 'msg': msg})
    api_success = lambda msg: jsonify({'flag': 'success', 'msg': msg})

    remote = oauth.remote_app(
        'site2',
        consumer_key='site2',
        consumer_secret='site2-secret',
        request_token_params={'scope': 'userinfo'},
        base_url=os.environ['base_url'],
        request_token_url=None,
        access_token_method='GET',
        access_token_url=os.environ['access_token_url'],
        authorize_url=os.environ['authorize_url']
    )

    @app.route('/')
    def index():
        if 'dev_token' in session:
            return render_template("home.html")
        return redirect(url_for('login'))

    @app.route('/welcome')
    def welcome():
        return render_template('welcome.html')

    @app.route('/account')
    def account():
        if session.get('role') != 'admin':
            return api_error("无权限！")
        return render_template("account.html", count=len(accounts), accounts=accounts)

    @app.route('/account/<_id>', methods=['DELETE'])
    def account_op(_id):
        global accounts
        accounts = [i for i in accounts if i.get('id') != _id]
        return api_success("删除成功！")

    @app.route('/order')
    def order():
        if session.get('role') != 'admin':
            return api_error('无权限！')
        return render_template("order.html", count=len(orders), orders=orders)

    @app.route('/<username>/order')
    def own_order(username):
        return render_template("own-orders.html", orders=own_orders.get(username, []),
                               count=len(own_orders.get(username, [])))

    @app.route('/order/<_id>')
    def order_op(_id):
        for i in orders:
            if str(i.get('id')) == _id:
                return api_success(i)
        return api_error('未找到订单：{}'.format(_id))

    @app.route('/login')
    def login():
        return remote.authorize(callback=url_for('authorized', _external=True))

    @app.route('/logout')
    def logout():
        session.pop('dev_token', None)
        return redirect(url_for('index'))

    @app.route('/authorized')
    def authorized():
        resp = remote.authorized_response()
        if resp is None:
            return 'Access denied: error=%s' % (
                request.args['error']
            )
        if isinstance(resp, dict) and 'access_token' in resp:
            session['dev_token'] = (resp['access_token'], '')
            userinfo = remote.get("userinfo").data
            session['username'] = userinfo['username']
            session['role'] = userinfo['role']
            return redirect(url_for('index'))
        return str(resp)

    @app.route('/client')
    def client_method():
        ret = remote.get("client")
        if ret.status not in (200, 201):
            return abort(ret.status)
        return ret.raw_data

    @app.route('/userinfo')
    def userinfo_method():
        ret = remote.get("userinfo")
        if ret.status not in (200, 201):
            return abort(ret.status)
        return ret.raw_data

    @app.route('/address')
    def address():
        ret = remote.get('address/hangzhou')
        if ret.status not in (200, 201):
            return ret.raw_data, ret.status
        return ret.raw_data

    @app.route('/method/<name>')
    def method(name):
        func = getattr(remote, name)
        ret = func('method')
        return ret.raw_data

    @remote.tokengetter
    def get_oauth_token():
        return session.get('dev_token')

    return remote


if __name__ == '__main__':
    import os

    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'
    # DEBUG=1 python oauth2_client.py
    app = Flask(__name__)
    app.debug = True
    app.config['JSON_AS_ASCII'] = False
    app.secret_key = 'site2'
    create_client(app)
    app.run(host=os.environ.get('host', '0.0.0.0'), port=int(os.environ.get('post', 8001)))
