import re
import logging
from app.conf.secret import *

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(filename)s %(funcName)s - %(message)s")
logger = logging.getLogger(__name__)

# 代理
proxies = {
    "http": None,
    "https": None
}
# proxies = {
#   "http": "http://127.0.0.1:8080",
#   "https": "https://127.0.0.1:8080",
# }

# cors
cors_origin = '*'

# requests超时时间
timeout = 5

# auth_session有效时间（分钟）
session_timeout = 5
# 页面监听有效时间（分钟）
listening_timeout = 1
# 数据统计间隔时间（分钟）
statistics_timeout = 3

# 全局编码
encoding = 'utf-8'

# 扫码任务线程数量
max_workers = 20

# pattern
space_pattern = re.compile(r"\s+")

# 过滤
scope_exclude = r'\.gif$|\.jpg$|\.png$|\.css$|\.js$|\.ico$|\.ttf$|\.woff2$|\.woff$'
scope_exclude += r'|\.gif\?|\.jpg\?|\.png\?|\.css\?|\.js\?|\.ico\?|\.ttf\?|\.woff2\?|\.woff\?'
scope_exclude = re.compile(scope_exclude)
