"""
公用
"""
import config
import requests

def get_php_sessions(address:str,
                     cid: str,
                     team_id: str,
                     password: str,
                     route: str = "/cpcsys/contest/contest_auth_ajax") -> str:
    """
    获取sessions
    :param address: OJ web端地址
    :param route: 路由，默认路径为/cpcsys/contest/contest_auth_ajax
    :param cid: 比赛编号
    :param team_id: team_id，staff分配时的用户名
    :param password: 密码
    :return: session字符串
    """
    url = address + route
    data = {
        "cid": cid,
        "team_id": team_id,
        "password": password
    }
    session = requests.Session()
    resp = session.post(url, data=data)
    phpsessid = resp.cookies.get("PHPSESSID")
    if not phpsessid:
        set_cookie = resp.headers.get("Set-Cookie", "")
        for kv in set_cookie.split(";"):
            if kv.strip().startswith("PHPSESSID="):
                phpsessid = kv.strip()[len("PHPSESSID="):]
                break
    if not phpsessid:
        raise RuntimeError("未获取到PHPSESSID")
    print("<UNK>PHPSESSID<UNK>", phpsessid)
    return phpsessid
