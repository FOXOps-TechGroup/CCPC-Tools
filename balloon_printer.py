import threading
import time
import queue
import traceback

import requests
import logging
import config
import utils

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(threadName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# 全局 session id 缓存及锁
_phpsessid = None
_phpsessid_lock = threading.Lock()

def get_cookie():
    global _phpsessid
    with _phpsessid_lock:
        if _phpsessid is not None:
            return _phpsessid
        _phpsessid = utils.get_php_sessions(
            config.Address,
            config.ContentID,
            config.TeamID,
            config.Password,
        )
        logger.info("获取新的 PHPSESSID：%s", _phpsessid)
        return _phpsessid

def reset_cookie():
    """失效时重置全局 session id"""
    global _phpsessid
    with _phpsessid_lock:
        logger.warning("PHPSESSID 失效，重置 session id")
        _phpsessid = None

# 队列与判重集合
print_queue = queue.Queue()
task_set = set()

# 题号映射
id2abc = {}
abc2id = {}

#状态映射
status = {
    2:"普通",
    3:"一血",
    5:"已发"
}

def get_balloon_task_list():
    route = "/cpcsys/contest/balloon_task_ajax"
    url = config.Address + route
    cookies = {"PHPSESSID": get_cookie()}
    params = {
        "cid": config.ContentID,
        "room": config.ROOM,
        "team_start": "",
        "team_end": ""
    }
    try:
        response = requests.get(url, params=params, cookies=cookies, headers={
            "X-Requested-With": "XMLHttpRequest",
        })
        response.raise_for_status()
        json_data = response.json()
    except Exception as e:
        logger.error("获取 task list 异常: %s", e)
        return []

    global id2abc, abc2id
    if 'data' in json_data:
        pid_map = json_data['data'].get('problem_id_map', {})
        id2abc = pid_map.get('id2abc', {})
        abc2id = pid_map.get('abc2id', {})
    tasks = json_data.get('data', {}).get('balloon_task_list', [])
    logger.info("拉取任务数: %d", len(tasks))
    return tasks

def balloon_change_status(cid, team_id, apid, bst):
    """
    修改气球状态接口，自动处理session失效。
    """
    route = "/cpcsys/contest/balloon_change_status_ajax"
    url = config.Address + route
    params = {"cid": cid}
    data = {"team_id": team_id, "apid": apid, "bst": bst}

    for attempt in range(2):
        cookies = {"PHPSESSID": get_cookie()}
        try:
            response = requests.post(
                url, params=params, data=data, cookies=cookies, headers={
                    "X-Requested-With": "XMLHttpRequest",
                }
            )
            response.raise_for_status()
            try:
                resp_json = response.json()
                logger.info("设置气球状态返回: %s", resp_json)
                return resp_json.get('msg') == 'ok'
            except Exception:
                logger.error("设置气球状态返回非 json: %s", response.text)
                if attempt == 0:
                    reset_cookie()
                    continue
                else:
                    return False
        except Exception as e:
            logger.error("设置气球状态异常: %s", e)
            return False
    return False

def print_task(task):
    pid = str(task['problem_id'])
    problem_letter = id2abc.get(pid, pid)
    logger.info(
        "打印小票 | 队伍ID: %s | 题号: %s | 房间: %s | 时间: %s |状态: %s",
        task['team_id'], problem_letter, task['room'], task['ac_time'], status[task['pst']],
    )
    #TODO:打印机接口

def getter():
    logger.info("Getter启动")
    while True:
        try:
            tasks = get_balloon_task_list()
            for task in tasks:
                if task.get('bst') != 5:
                    key = (task['team_id'], task['problem_id'], task['room'])
                    if key not in task_set:
                        print_queue.put(task)
                        task_set.add(key)
                        logger.info("新任务入队: %s", key)
            time.sleep(3)
        except Exception as e:
            logger.error("Getter异常: %s", e)
            time.sleep(3)

def setter():
    logger.info("Setter启动")
    while True:
        try:
            task = print_queue.get()
            print_task(task)
            cid = str(task['contest_id'])
            team_id = task['team_id']
            problem_id = str(task['problem_id'])
            apid = id2abc[problem_id]  # balloon_change_status要求数字
            success = balloon_change_status(cid, team_id, apid, "5")
            if not success:
                logger.warning("设置bst=5失败: %s", task)
            key = (team_id, problem_id, task['room'])
            task_set.discard(key)
            print_queue.task_done()
            logger.info("任务完成并移除: %s", key)
        except Exception as e:
            logger.error("Setter异常: %s", e)
            time.sleep(1)

def main():
    t_prod = threading.Thread(target=getter, name="Getter", daemon=True)
    t_cons = threading.Thread(target=setter, name="Setter", daemon=True)
    t_prod.start()
    t_cons.start()
    logger.info("队列打印已启动。按 Ctrl+C 退出。")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("退出。")

if __name__ == "__main__":
    main()
