import re
import requests
from app.conf.conf import logger
from app.model.po import Workspace


def watch_hosts(portal_site):
    """
    获取url下的所有hosts，以及sso认证时所需要的一些信息
    可根据自己实际情况获取，可能会有前后端分离的情况，可以自己去解析
    本示例比较简单，只简单获取当前url中的host
    :param portal_site: 首页url
    :return: (redirect_url, system_type, hosts, portal_site)
    """
    logger.info("watch hosts: {} begin...".format(portal_site))

    hs = re.findall(r'http[s]?://([\w.:-]+).*$', portal_site)
    rest = requests.get(portal_site)
    system_type = Workspace.TYPE_SSO

    logger.info("watch hosts: {} -> {}".format(portal_site, hs))
    return rest.url, system_type, hs, portal_site
