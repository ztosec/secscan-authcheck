from flask import blueprints

bp_web = blueprints.Blueprint('web', __name__)
bp_api = blueprints.Blueprint('api', __name__, url_prefix="/api")
bp_ws = blueprints.Blueprint('ws', __name__, url_prefix='/ws')

from app.web import api
from app.web import error
from app.web import web
from app.web import ws
