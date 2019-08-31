# coding: utf-8
from enum import Enum
from datetime import datetime, timedelta
from flask import g, render_template, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_oauthlib.provider import OAuth2Provider
from flask_oauthlib.contrib.oauth2 import bind_sqlalchemy
from flask_oauthlib.contrib.oauth2 import bind_cache_grant

db = SQLAlchemy()


class Role(Enum):
    ADMIN = "admin"
    NORMAL = "normal"


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, index=True,
                         nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(40), nullable=False, default=Role.NORMAL.value)

    def check_password(self, password):
        return self.password == password


class Client(db.Model):
    # id = db.Column(db.Integer, primary_key=True)
    # human readable name
    name = db.Column(db.String(40))
    client_id = db.Column(db.String(40), primary_key=True)
    client_secret = db.Column(db.String(55), unique=True, index=True,
                              nullable=False)
    client_type = db.Column(db.String(20), default='public')
    _redirect_uris = db.Column(db.Text)
    default_scope = db.Column(db.Text, default='email address userinfo')

    @property
    def user(self):
        return g.user

    @property
    def redirect_uris(self):
        if self._redirect_uris:
            return self._redirect_uris.split()
        return []

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]

    @property
    def default_scopes(self):
        if self.default_scope:
            return self.default_scope.split()
        return []

    @property
    def allowed_grant_types(self):
        return ['authorization_code', 'password', 'client_credentials',
                'refresh_token']

    def validate_redirect_uri(self, redirect_uri):
        # dev
        return True


class Grant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE')
    )
    user = relationship('User')

    client_id = db.Column(
        db.String(40), db.ForeignKey('client.client_id', ondelete='CASCADE'),
        nullable=False,
    )
    client = relationship('Client')
    code = db.Column(db.String(255), index=True, nullable=False)

    redirect_uri = db.Column(db.String(255))
    scope = db.Column(db.Text)
    expires = db.Column(db.DateTime)

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self

    @property
    def scopes(self):
        if self.scope:
            return self.scope.split()
        return None


class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.String(40), db.ForeignKey('client.client_id', ondelete='CASCADE'),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE')
    )
    user = relationship('User')
    client = relationship('Client')
    token_type = db.Column(db.String(40))
    access_token = db.Column(db.String(255))
    refresh_token = db.Column(db.String(255))
    expires = db.Column(db.DateTime)
    scope = db.Column(db.Text)

    def __init__(self, **kwargs):
        expires_in = kwargs.pop('expires_in', None)
        if expires_in is not None:
            self.expires = datetime.utcnow() + timedelta(seconds=expires_in)

        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def scopes(self):
        if self.scope:
            return self.scope.split()
        return []

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self


def current_user():
    return g.user


def cache_provider(app):
    oauth = OAuth2Provider(app)

    bind_sqlalchemy(oauth, db.session, user=User,
                    token=Token, client=Client)

    app.config.update({'OAUTH2_CACHE_TYPE': 'simple'})
    bind_cache_grant(app, oauth, current_user)
    return oauth


def sqlalchemy_provider(app):
    oauth = OAuth2Provider(app)

    bind_sqlalchemy(oauth, db.session, user=User, token=Token,
                    client=Client, grant=Grant, current_user=current_user)

    return oauth


def default_provider(app):
    oauth = OAuth2Provider(app)

    @oauth.clientgetter
    def get_client(client_id):
        z = Client.query.filter_by(client_id=client_id).first()
        return z

    @oauth.grantgetter
    def get_grant(client_id, code):
        return Grant.query.filter_by(client_id=client_id, code=code).first()

    @oauth.tokengetter
    def get_token(access_token=None, refresh_token=None):
        if access_token:
            return Token.query.filter_by(access_token=access_token).first()
        if refresh_token:
            return Token.query.filter_by(refresh_token=refresh_token).first()
        return None

    @oauth.grantsetter
    def set_grant(client_id, code, request, *args, **kwargs):
        expires = datetime.utcnow() + timedelta(seconds=100)
        grant = Grant(
            client_id=client_id,
            code=code['code'],
            redirect_uri=request.redirect_uri,
            scope=' '.join(request.scopes),
            user_id=g.user.id,
            expires=expires,
        )
        db.session.add(grant)
        db.session.commit()

    @oauth.tokensetter
    def set_token(token, request, *args, **kwargs):
        # In real project, a token is unique bound to user and client.
        # Which means, you don't need to create a token every time.
        tok = Token(**token)
        tok.user_id = request.user.id
        tok.client_id = request.client.client_id
        db.session.add(tok)
        db.session.commit()

    @oauth.usergetter
    def get_user(username, password, *args, **kwargs):
        # This is optional, if you don't need password credential
        # there is no need to implement this method
        return User.query.filter_by(username=username, password=password).first()

    return oauth


def prepare_app(app):
    db.init_app(app)
    db.app = app
    db.create_all()

    import os

    client1 = Client(
        name='site1', client_id='site1', client_secret='site1-secret',
        _redirect_uris=os.environ['site1_redirect_url']
    )

    client2 = Client(
        name='site2', client_id='site2',
        client_secret='site2-secret',
        _redirect_uris=os.environ['site2_redirect_url']
    )

    user = User(username='admin', password='admin123', role=Role.ADMIN.value)
    user2 = User(username='normal', password='normal123', role=Role.NORMAL.value)

    temp_grant = Grant(
        user_id=1, client_id='site1',
        code='12345', scope='userinfo email',
        expires=datetime.utcnow() + timedelta(seconds=100)
    )

    temp_grant2 = Grant(
        user_id=2, client_id='site2',
        code='12345', scope='userinfo email',
        expires=datetime.utcnow() + timedelta(seconds=100)
    )

    temp_grant3 = Grant(
        user_id=1, client_id='site1',
        code='12345', scope='userinfo email',
        expires=datetime.utcnow() + timedelta(seconds=100)
    )

    temp_grant4 = Grant(
        user_id=2, client_id='site2',
        code='12345', scope='userinfo email',
        expires=datetime.utcnow() + timedelta(seconds=100)
    )

    access_token = Token(
        user_id=1, client_id='site1', access_token='nerver_expire'
    )

    access_token2 = Token(
        user_id=1, client_id='site2', access_token='nerver_expire'
    )

    access_token3 = Token(
        user_id=2, client_id='site1', access_token='never_expire'
    )
    access_token4 = Token(
        user_id=2, client_id='site2', access_token='never_expire'
    )

    try:
        db.session.add(client1)
        db.session.add(client2)
        db.session.commit()

        db.session.add(user)
        db.session.add(user2)
        db.session.commit()

        db.session.add(temp_grant)
        db.session.add(temp_grant2)
        db.session.add(temp_grant3)
        db.session.add(temp_grant4)
        db.session.commit()

        db.session.add(access_token)
        db.session.add(access_token2)
        db.session.add(access_token3)
        db.session.add(access_token4)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # raise e
    return app


def create_server(app, oauth=None):
    if not oauth:
        oauth = default_provider(app)

    app = prepare_app(app)

    @app.before_request
    def load_current_user():
        # user = User.query.get(1)
        # g.user = user
        pass

    @app.route('/home')
    def home():
        return render_template('home.html')

    @app.route('/oauth/authorize', methods=['GET', 'POST'])
    @oauth.authorize_handler
    def authorize(*args, **kwargs):
        # NOTICE: for real project, you need to require login
        if request.method == 'GET':
            # render a page for user to confirm the authorization
            return render_template('confirm.html')

        if request.method == 'HEAD':
            # if HEAD is supported properly, request parameters like
            # client_id should be validated the same way as for 'GET'
            response = make_response('', 200)
            response.headers['X-Client-ID'] = kwargs.get('client_id')
            return response

        username = request.form.get('username', 'no')
        password = request.form.get('password', 'no')
        confirm = request.form.get('confirm', 'no')
        if confirm == 'yes':
            user = User.query.filter_by(username=username, password=password).first()
            g.user = user
            return user is not None
        return False

    @app.route('/oauth/token', methods=['POST', 'GET'])
    @oauth.token_handler
    def access_token():
        return {}

    @app.route('/oauth/revoke', methods=['POST'])
    @oauth.revoke_handler
    def revoke_token():
        pass

    @app.route('/api/email')
    @oauth.require_oauth('email')
    def email_api():
        oauth = request.oauth
        return jsonify(email='me@oauth.net', username=oauth.user.username)

    @app.route('/api/client')
    @oauth.require_oauth()
    def client_api():
        oauth = request.oauth
        return jsonify(client=oauth.client.name)

    @app.route('/api/userinfo')
    @oauth.require_oauth()
    def user_info():
        oauth = request.oauth

        return jsonify({
            'username': oauth.user.username,
            'role': oauth.user.role
        })

    @app.route('/api/address/<city>')
    @oauth.require_oauth('address')
    def address_api(city):
        oauth = request.oauth
        return jsonify(address=city, username=oauth.user.username)

    @app.route('/api/method', methods=['GET', 'POST', 'PUT', 'DELETE'])
    @oauth.require_oauth()
    def method_api():
        return jsonify(method=request.method)

    @oauth.invalid_response
    def require_oauth_invalid(req):
        return jsonify(message=req.error_message), 401

    return app


if __name__ == '__main__':
    import os
    from flask import Flask

    app = Flask(__name__)
    app.debug = True
    app.secret_key = 'development'
    app.config.update({
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///test.sqlite'
    })
    app = create_server(app)
    app.run(host=os.environ.get('host', '0.0.0.0'), port=int(os.environ.get('post', 7373)))
