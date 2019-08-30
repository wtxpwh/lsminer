
from lsminer import *
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

logging.basicConfig(level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


subprocess = subprocess.Popen('ping www.baidu.com -t', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
for line in iter(subprocess.stdout.readline, ''):
    print(line.decode('gbk'))


#commond queue
q = queue.Queue(0)

class lsminerClient(object):
    def __init__(self):
        self.state = None
        self.cfg = None
        self.sock = None
        self.minerargs = None
        self.minerpath = None
        self.subprocess = None

    def __del__(self):
        pass

    def connectSrv(self):
        try:
            self.sock = socket.create_connection((self.cfg['ip'], self.cfg['port']), 3)
            self.sock.setblocking(True)
            self.sock.settimeout(None)
        except Exception as e:
            logging.error('connectSrv exception. msg: ' + str(e))
            time.sleep(3)
            q.put(1)
    
    def sendLoginReq(self):
        try:
            n = getNvidiaCount()
            a = getAMDCount()
            reqData = {}
            reqData['method'] = 1
            reqData['accesskey'] = self.cfg['accesskey']
            reqData['wkname'] = self.cfg['wkname']
            reqData['wkid'] = getWkid()
            reqData['devicename'] = getVedioCard()
            reqData['devicecnt'] = a + n
            reqData['appver'] = self.cfg['appver']
            reqData['platform'] = 1 if n > a else 2
            reqData['driverver'] = self.cfg['driverver']
            reqData['os'] = self.cfg['os']
            reqjson = json.dumps(reqData)
            reqjson += '\r\n'
            self.sock.sendall(reqjson.encode("utf-8"))
        except Exception as e:
            logging.error('sendLoginReq exception. msg: ' + str(e))
        

    def sendGetMinerArgsReq(self):
        reqData = {}
        reqData['method'] = 2
        reqData['os'] = self.cfg['os']
        reqjson = json.dumps(reqData)
        reqjson += '\r\n'
        self.sock.sendall(reqjson.encode("utf-8"))

    def loadCfg(self):
        self.cfg = loadCfg()
        if self.cfg == 0:
            raise ValueError('loadcfg error!')
        if 'ip' not in self.cfg or 'port' not in self.cfg:
            raise ValueError('config file error. missing ip or port!')

    def onWelcome(self, msg):
        logging.info('connect server ok. recv server msg: ' + msg['message'])
        q.put(2)

    def onLoginResp(self, msg):
        if 'result' in msg and msg['result']:
            logging.info('login ok.')
            q.put(3)
        else:
            logging.info('login error. msg: ' + msg['error'])
            q.put(2)
    
    def reportThread(self):
        pass
    
    def minerThread(self):
        args = []
        args.append(self.minerpath)
        minerargs = shlex.split(self.minerargs['customize'])
        args.extend(minerargs)
        self.subprocess = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        thread = threading.Thread(target=lsminerClient.reportThread, args=(self,))
        thread.start()
        for line in iter(self.subprocess.stdout.readline(), ''):
            print(line.decode('gbk'))
        if self.subprocess.returncode < 0:
            logging.info('miner terminated.')
        else:
            q.put(3)

    def onGetMinerArgs(self, msg):
        if 'result' in msg and msg['result']:
            logging.info('get miner args ok.')
            self.minerargs = msg
            if self.subprocess and self.subprocess.poll is None:
                self.subprocess.terminate()
            thread = threading.Thread(target=lsminerClient.minerThread, args=(self,))
            thread.start()
        else:
            logging.info('get miner args error. msg: ' + msg['error'])
            q.put(3)

    def onReportResp(self, msg):
        pass

    def onUpdateMinerArgs(self, msg):
        logging.info('recv update miner args commond.')
        q.put(3)

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
            else:
                logging.info('unknown server msg method! msg: ' + str(msg))
        else:
            logging.info('unknown server msg! msg: ' + str(msg))


    def recvThread(self):
        buffer = []
        while True:
            if self.sock == None:
                logging.info('client socket == None. sleep one second.')
                time.sleep(1)
                continue

            rd = self.sock.recv(4096).decode()
            if rd:
                buffer.append(rd)
                rd = None
                data = ''.join(buffer)
                try:
                    msg = json.loads(data)
                    self.processMsg(msg)
                    buffer.clear()
                except Exception as e:
                    logging.info('recv thread exception. msg: ' + str(e))
                    logging.info('json.loads server data exception.')
            else:
                logging.info('server close socket. exit recv thread.')
                self.sock.close()
                break

    '''cmd list: 1 == connect server, 2 == login server, 3 == get miner config'''
    def processCmd(self, cmd):
        if cmd == 1:
            self.connectSrv()
        elif cmd == 2:
            self.sendLoginReq()
        elif cmd == 3:
            self.sendGetMinerArgsReq()
        else:
            logging.error('unknown cmd. cmd: ' + str(cmd))

    def init(self):
        self.loadCfg()
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
                logging.info("sleep 3 seconds and retry...")
                time.sleep(3)


if __name__ == '__main__':
    client = lsminerClient()
    client.init()
    client.run()



    


