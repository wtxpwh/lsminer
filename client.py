#!/usr/bin/python3
from tools import *
import time
import socket
import uuid
import json
import os
import logging
import queue
import threading
import sys
import subprocess
import shlex
from datetime import timedelta
from datetime import datetime
import tarfile
import signal
import copy

from gpumon import *
from minerinfo import *

logging.basicConfig(level = logging.INFO, format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt = '%Y-%m-%d  %H:%M:%S %a')

#commond queue
q = queue.Queue(0)

class lsminerClient(object):
    def __init__(self):
        self.cfg = {}
        self.sock = None
        self.minerargs = {}
        self.minerpath = ''
        self.subprocess = None
        self.mthread = None
        self.rthread = None
        self.startime = datetime.now()
        self.gpuType = self.checkGpuType()    #nvidia==1, amd==2
        self.minertime = datetime.now()
        self.consoleurl = ''
        self.accesskey = getAccessKey()
        self.ttyserver = self.getTTYServerString()
        self.ttyservicestarting = 0

    def __del__(self):
        pass

    def getClientUptimeMinutes(self):
        delta = datetime.now() - self.startime
        return delta.seconds // 60

    def getMinerUptimeMinutes(self):
        delta = datetime.now() - self.minertime
        return delta.seconds // 60

    def getGpuInfo(self):
        if self.gpuType == 1:
            return nvmlGetGpuInfo()
        else:
            return fsGetGpuInfo()

    def checkGpuType(self):
        n = nvmlGetGpuCount()
        a = fsGetGpuCount()
        return  1 if n > a else 2

    def checkServerConnection(self):
        try:
            cs = self.cfg['ip'].strip() + ':' + self.cfg['port'].strip()
            netlines = os.popen('netstat -ent').read().splitlines(False)
            for line in netlines:
                if cs in line and 'ESTABLISHED' in line:
                    return True
        except Exception as e:
            logging.error("function checkServerConnection exception. msg: " + str(e))
            logging.exception(e)
        return False

    def checkTTYServerConnection(self):
        try:
            if self.ttyserver:
                netlines = os.popen('netstat -ent').read().splitlines(False)
                for line in netlines:
                    if self.ttyserver in line and 'ESTABLISHED' in line:
                        return True
        except Exception as e:
            logging.error("function checkTTYServerConnection exception. msg: " + str(e))
            logging.exception(e)
        return False

    def getTTYServerString(self):
        try:
            with open('./boot/ttyshare', 'r', encoding="utf-8") as text:
                for line in text.readlines():
                    if '--server ' in line:
                        ttyserver = line.split('--server ')[1].strip()
                        logging.info('find tty server string: ' + ttyserver)
                        return ttyserver
            logging.warning('do not find tty server string.')
        except Exception as e:
            logging.error("function getTTYServerString exception. msg: " + str(e))
            logging.exception(e)
        return ''

    def connectSrv(self):
        try:
            logging.info('lsminerClient start connecting server: '+ str(self.cfg['ip'])+':'+ str(self.cfg['port']))
            self.sock = socket.create_connection((self.cfg['ip'], self.cfg['port']), 3)
            self.sock.setblocking(True)
            self.sock.settimeout(None)
        except Exception as e:
            logging.error('connectSrv exception. msg: ' + str(e))
            logging.exception(e)
            time.sleep(3)
            q.put(1)
    
    def sendLoginReq(self):
        try:
            if self.gpuType == 1:
                cnt = nvmlGetGpuCount()
                name = nvmlGetGpuName()
            else:
                cnt = fsGetGpuCount()
                name = fsGetGpuName()
            
            reqData = {}
            reqData['method'] = 1
            reqData['accesskey'] = self.accesskey

            if self.cfg['wkname']:
                reqData['wkname'] = self.cfg['wkname']
            else:
                reqData['wkname'] = getLanIp().replace('.', 'X')

            if self.cfg['wkid']:
                reqData['wkid'] = self.cfg['wkid']
            else:
                reqData['wkid'] = getWkid()

            reqData['devicename'] = name
            reqData['devicecnt'] = cnt
            reqData['appver'] = getClientVersion()
            reqData['platform'] = self.gpuType
            reqData['driverver'] = self.cfg['driverver']
            reqData['os'] = self.cfg['os']
            reqjson = json.dumps(reqData)
            reqjson += '\r\n'
            logging.info('lsminerClient send login request.')
            logging.info(reqjson)
            self.sock.sendall(reqjson.encode("utf-8"))
        except Exception as e:
            logging.error('sendLoginReq exception. msg: ' + str(e))
            logging.exception(e)
            time.sleep(1)
            if not self.checkServerConnection():
                self.sock = None
            return None     

    def sendGetMinerArgsReq(self):
        try:
            reqData = {}
            reqData['method'] = 2
            reqData['os'] = self.cfg['os']
            reqjson = json.dumps(reqData)
            reqjson += '\r\n'
            logging.info('lsminerClient send get miner args.')
            logging.info(reqjson)
            self.sock.sendall(reqjson.encode("utf-8"))
        except Exception as e:
            logging.error('sendGetMinerArgsReq exception. msg: ' + str(e))
            logging.exception(e)
            time.sleep(1)
            if not self.checkServerConnection():
                self.sock = None
            return None

    def sendLogoutReq(self):
        try:
            reqData = {}
            reqData['method'] = 6
            reqData['os'] = self.cfg['os']
            reqjson = json.dumps(reqData)
            reqjson += '\r\n'
            logging.info('lsminerClient send logout request.')
            logging.info(reqjson)
            self.sock.sendall(reqjson.encode("utf-8"))
        except Exception as e:
            logging.error('sendLogoutReq exception. msg: ' + str(e))
            logging.exception(e)
            return None

    def sendConsoleIdReq(self):
        try:
            reqData = {}
            reqData['method'] = 16
            reqData['params'] = self.consoleurl
            reqData['os'] = self.cfg['os']
            reqjson = json.dumps(reqData)
            reqjson += '\r\n'
            logging.info('lsminerClient send console request.')
            logging.info(reqjson)
            self.sock.sendall(reqjson.encode("utf-8"))
        except Exception as e:
            logging.error('sendConsoleIdReq exception. msg: ' + str(e))
            logging.exception(e)
            time.sleep(1)
            if not self.checkServerConnection():
                self.sock = None
            return None

    def onWelcome(self, msg):
        logging.info('recv server connecting msg: ' + str(msg))
        logging.info('connect server ok.')
        thread = threading.Thread(target=lsminerClient.ttyshareProc, args=(self,))
        thread.start()
        q.put(2)

    def onLoginResp(self, msg):
        logging.info('recv server login msg: ' + str(msg))
        if 'result' in msg and msg['result']:
            logging.info('login ok.')
            q.put(3)
        else:
            logging.info('login error. msg: ' + msg['error'])
            q.put(6)
            time.sleep(1)
            q.put(1)
    
    def getReportData(self, mcfg):
        try:
            reqData = {}
            reqData['method'] = 3
            reqData['minerver'] = mcfg['minerver']
            reqData['uptime'] = self.getMinerUptimeMinutes()
            reqData['minerstatus'] = 1
            gpuinfo = self.getGpuInfo()
            if gpuinfo:
                minerinfo = getMinerStatus(mcfg)
                if not minerinfo:
                    reqData['hashrate'] = 0
                    for i in range(len(gpuinfo)):
                        gpustatus = str(i) + '|'+ gpuinfo[i]['name'] + '|' + str(gpuinfo[i]['tempC']) + '|0|' + str(gpuinfo[i]['fanpcnt']) + '|' + str(gpuinfo[i]['power_usage'])
                        if i+1 == len(gpuinfo):
                            gpustatus += '$'
                        else:
                            gpustatus += '|'
                else:
                    reqData['hashrate'] = minerinfo['totalhashrate']
                    mc = len(minerinfo['hashrate'])
                    for i in range(len(gpuinfo)):
                        if i < mc:
                            gpustatus = str(i) + '|'+ gpuinfo[i]['name'] + '|' + str(gpuinfo[i]['tempC']) + '|' + str(minerinfo['hashrate'][i]) + '|' + str(gpuinfo[i]['fanpcnt']) + '|' + str(gpuinfo[i]['power_usage'])
                        else:
                            gpustatus = str(i) + '|'+ gpuinfo[i]['name'] + '|' + str(gpuinfo[i]['tempC']) + '|0|' + str(gpuinfo[i]['fanpcnt']) + '|' + str(gpuinfo[i]['power_usage'])
                        
                        if i+1 == len(gpuinfo):
                            gpustatus += '$'
                        else:
                            gpustatus += '|'
                gpustatus += str(self.getClientUptimeMinutes())
                reqData['gpustatus'] = gpustatus
                reqData = json.dumps(reqData) + '\r\n'
                return reqData
        except Exception as e:
            logging.error("function getReportData exception. msg: " + str(e))
            logging.exception(e)
        return None

    def reportThread(self):
        while True:
            try:
                time.sleep(float(self.cfg['reportime']))

                #check ttyshare connection
                if not self.checkTTYServerConnection():
                    thread = threading.Thread(target=lsminerClient.ttyshareProc, args=(self,))
                    thread.start()

                mcfg = self.minerargs
                reqData = self.getReportData(mcfg)
                while not reqData:
                    logging.warning('getReportData failed. sleep 3 seconds and try again.')
                    time.sleep(3)
                    reqData = self.getReportData(mcfg)

                logging.info('lsminerClient send miner report data.')
                logging.info(reqData)
                if self.sock:
                    self.sock.sendall(reqData.encode('utf-8'))
                else:
                    logging.warning('socket unusable.')
                    time.sleep(1)
                    if not self.checkServerConnection():
                        q.put(1)
            except Exception as e:
                logging.error("function reportThread exception. msg: " + str(e))
                logging.exception(e)
                time.sleep(1)
                if not self.checkServerConnection():
                    q.put(1)

    def getNewMinerFile(self, mcfg):
        try:
            path = './miners/temp.tar.xz'
            while not downloadFile(mcfg['minerurl'], path):
                logging.error("download miner kernel file failed. sleep 3 seconds and try later.")
                time.sleep(3)

            with tarfile.open(path) as tar:
                tar.extractall('./miners')
                #os.remove(path)
                self.minerpath = './miners/' + mcfg['minerver'] + '/' + mcfg['minername']
                return self.minerpath
        except Exception as e:
            logging.error("function getNewMinerFile exception. msg: " + str(e))
            logging.exception(e)

    def checkMinerVer(self, mcfg):
        try:
            mf = './miners/' + mcfg['minerver']
            if os.path.exists(mf):
                self.minerpath = mf + '/' + mcfg['minername']
                return self.minerpath
            else:
                delcmd = 'rm -rf ./miners/' + mcfg['minerver'].split('_')[0] + '_*'
                os.system(delcmd)
        except Exception as e:
            logging.error("function checkMinerVer exception. msg: " + str(e))
            logging.exception(e)
        return None

    def killAllMiners(self, path):
        try:
            cmd = 'ps -x | grep ' + path
            o = os.popen(cmd).read()
            lines = o.splitlines(False)
            for l in lines:
                p = l.lstrip().split(' ')
                if 'grep' in p:
                    continue
                logging.info('kill task pid: ' + p[0])
                os.kill(int(p[0]), signal.SIGKILL)
        except Exception as e:
            logging.error("function killAllMiners exception. msg: " + str(e))
            logging.exception(e)

    def minerThreadProc(self):
        try:
            mcfg = self.minerargs
            if not self.checkMinerVer(mcfg):
                self.getNewMinerFile(mcfg)
            cmd = self.minerpath + ' ' + mcfg['customize']
            process = subprocess.Popen(cmd, shell=True)
            time.sleep(3)
            process.terminate()
            #update miner time
            self.minertime = datetime.now()
        except Exception as e:
            logging.error("function minerThread exception. msg: " + str(e))
            logging.exception(e)

    
    def onGetMinerArgs(self, msg):
        try:
            logging.info('recv server get miner args msg: ' + str(msg))
            if 'result' in msg and msg['result']:
                logging.info('get miner args ok.')
                
                self.minerargs = copy.deepcopy(msg)
                logging.info('mmmmmmmmmmmmmmmmmmmmmmmmmmmmm')
                logging.info(msg)
                logging.info('ssssssssssssssssssssssssssss')
                logging.info(self.minerargs)
                #kill miner process, the miner thread will exit
                if self.minerpath:
                    self.killAllMiners(self.minerpath[1:])

                #start new miner thread
                self.mthread = threading.Thread(target=lsminerClient.minerThreadProc, args=(self,))
                self.mthread.start()
                
                #start new report Thread
                if self.rthread == None:
                    self.rthread = threading.Thread(target=lsminerClient.reportThread, args=(self,))
                    self.rthread.start()
            else:
                logging.info('get miner args error. msg: ' + msg['error'])
                q.put(3)
        except Exception as e:
            logging.error("function onGetMinerArgs exception. msg: " + str(e))
            logging.exception(e)

    #unused function minerThread
    def minerThread(self):
        try:
            mcfg = self.minerargs
            if not self.checkMinerVer(mcfg):
                self.getNewMinerFile(mcfg)

            args = []
            args.append(self.minerpath)
            margs = shlex.split(mcfg['customize'])
            args.extend(margs)
            self.subprocess = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for line in iter(self.subprocess.stdout.readline, ''):
                print(line.decode('gbk'))
            if self.subprocess.returncode < 0:
                logging.info('miner terminated.')
            else:
                q.put(3)
        except Exception as e:
            logging.error("function minerThread exception. msg: " + str(e))
            logging.exception(e)

    #unused function onGetMinerArgsbak
    def onGetMinerArgsbak(self, msg):
        try:
            if 'result' in msg and msg['result']:
                logging.info('get miner args ok.')

                self.minerargs = msg
                
                #kill miner process, the miner thread will exit
                if self.mthread:
                    while self.mthread.is_alive():
                        if self.subprocess and self.subprocess.poll() == None:
                            #self.subprocess.terminate()
                            self.killAllMiners(self.minerpath[1:])
                        time.sleep(1)

                #start new miner thread
                self.mthread = threading.Thread(target=lsminerClient.minerThread, args=(self,))
                self.mthread.start()
                
                #start new report Thread
                
                if self.rthread == None:
                    self.rthread = threading.Thread(target=lsminerClient.reportThread, args=(self,))
                    self.rthread.start()
            else:
                logging.info('get miner args error. msg: ' + msg['error'])
                q.put(3)
        except Exception as e:
            logging.error("function onGetMinerArgs exception. msg: " + str(e))
            logging.exception(e)

    def onReportResp(self, msg):
        logging.info('recv server report msg: ' + str(msg))

    def onUpdateMinerArgs(self, msg):
        logging.info('recv server update miner args msg: ' + str(msg))
        q.put(3)

    def onClientUpdate(self, msg):
        logging.info('recv server client update msg: ' + str(msg))
        #kill miner process, exit client.py
        if self.minerpath:
            self.killAllMiners(self.minerpath[1:])
        self.sock.close()
        time.sleep(0.5)
        sys.exit(123)

    def onGetTTYShareId(self, msg):
        logging.info('recv server get ttyshare msg: ' + str(msg))
        thread = threading.Thread(target=lsminerClient.ttyshareProc, args=(self,))
        thread.start()

    def processMsg(self, msg):
        if 'method' in msg:
            if msg['method'] == 1:
                self.onLoginResp(msg)
            elif msg['method'] == 2:
                self.onGetMinerArgs(msg)
            elif msg['method'] == 3:
                self.onReportResp(msg)
            elif msg['method'] == 4:
                self.onUpdateMinerArgs(msg)
            elif msg['method'] == 5:
                pass
            elif msg['method'] == 6:
                pass
            elif msg['method'] == 7:
                pass
            elif msg['method'] == 8:
                pass
            elif msg['method'] == 9:
                self.onWelcome(msg)
            elif msg['method'] == 10:
                pass
            elif msg['method'] ==11:
                pass
            elif msg['method'] == 12:
                pass
            elif msg['method'] == 13:
                pass
            elif msg['method'] == 14:
                pass
            elif msg['method'] == 15:
                pass
            elif msg['method'] == 16:
                self.onGetTTYShareId(msg)
            else:
                logging.info('unknown server msg method! msg: ' + str(msg))
        else:
            logging.info('unknown server msg! msg: ' + str(msg))

    def recvThread(self):
        while True:
            try:
                buffer = ''
                if self.sock == None:
                    logging.info('client socket == None. sleep 1 second.')
                    time.sleep(1)
                    continue

                data = self.sock.recv(4096)
                if not data:
                    logging.warning('server close socket. try to reconnect.')
                    self.sock = None
                    q.put(1)
                    continue

                buffer += data.decode()
                if '\n' in buffer:
                    if '{' == buffer[0] and '}' == buffer[len(buffer)-2]:
                        msg = json.loads(buffer)
                        self.processMsg(msg)
                    else:
                        logging.warning('lsminerClient recv unknown format data.')
                        logging.warning(buffer)
                    buffer = ''
            except Exception as e:
                logging.info('recvThread exception. msg: ' + str(e))
                logging.exception(e)
                time.sleep(1)
                if not self.checkServerConnection():
                    self.sock = None

    '''cmd list: 1 == connect server, 2 == login server, 3 == get miner config'''
    def processCmd(self, cmd):
        if cmd == 1:
            self.connectSrv()
        elif cmd == 2:
            self.sendLoginReq()
        elif cmd == 3:
            self.sendGetMinerArgsReq()
        elif cmd == 6:
            self.sendLogoutReq()
        elif cmd == 16:
            self.sendConsoleIdReq()
        else:
            logging.error('unknown cmd. cmd: ' + str(cmd))

    def ttyshareProc(self):
        filepath = "/home/lsminer/ttyshare.id"

        #check ttyshare server connection ok? ok = True,
        if not self.checkTTYServerConnection():
            subprocess.run('sudo systemctl stop ttyshare', shell=True)
            time.sleep(1)
            subprocess.run('sudo systemctl start ttyshare', shell=True)

        if not self.ttyservicestarting:
            self.ttyservicestarting = 1
            while True:
                try:
                    if not os.path.exists(filepath):
                        logging.warning('can not find ttyshare.id file. sleep 10 seconds and try again.')
                        time.sleep(10)
                        continue
                    time.sleep(2)
                    with open(filepath, "r", encoding="utf-8") as fs:
                        self.consoleurl = fs.readline().replace("\n","")
                        logging.info("ttyshareurl: " + str(self.consoleurl))
                    q.put(16)
                    break
                except Exception as e:
                    logging.info('ttyshareProc exception. msg: ' + str(e))
                    logging.exception(e)
                    time.sleep(10)
            self.ttyservicestarting = 0

    def init(self):
        self.cfg = loadCfg()
        thread = threading.Thread(target=lsminerClient.recvThread, args=(self,))
        thread.start()

    def run(self):
        q.put(1)
        while True:
            try:
                cmd = q.get()
                self.processCmd(cmd)
            except Exception as e:
                logging.info("main loop run exception. msg: " + str(e))
                logging.exception(e)
                logging.info("sleep 3 seconds and retry...")
                time.sleep(3)


if __name__ == '__main__':
    client = lsminerClient()
    client.init()
    client.run()
