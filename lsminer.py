from urllib import request
import time
import socket
import uuid
import json
import os
import hashlib

def getMac():
    '''获取系统网卡MAC地址'''
    macnum = hex(uuid.getnode())[2:]
    mac = "-".join(macnum[i: i+2] for i in range(0, len(macnum), 2))
    return mac

def getName():
    '''获取电脑名称'''
    return socket.gethostname()

def getIp():
    '''获取系统内网IP地址'''
    return socket.gethostbyname(getName())

def loadCfg():
    '''加载当前目录下的配置文件config.json'''
    return json.load(open("config.json", "r", encoding="utf-8"))

def md5(data):
    '''MD5哈希函数'''
    return str(hashlib.md5(data.encode('utf-8')).hexdigest())

def getReboot(url):
    '''检测是否需要重启系统'''
    try:
        req = request.Request(url)
        with request.urlopen(req) as f:
            return int(f.read().decode('utf-8'))
    except Exception as e:
        print("function getReboot exception. msg: " + str(e))
        return 0
