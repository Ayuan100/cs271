import socket
import sys
import common
import thread
import multiprocessing
import heapq
import time
from random import randrange

myname = ''

def sendPeerMessage(pipe, s):
    while True:
        msg = pipe.recv()
        time.sleep(randrange(5))
        print('sendPeerMessage:', msg)
        s.send((','.join(msg)+'|').encode())
def pipeThread(pipe, socketForServer, socketsForClients, send_pipes_sockets):
    replyDict = {}
    transactionQueue = []
    gclock = 0
 
    # def sendToPeer1(s, msg):
    #     reply = (str(getNewClock()), myname, msg)
    #     thread.startTemp(sendMsg, (s, reply,))
        
    def sendToPeer(s, msg):

        reply = (str(getNewClock()), myname, msg)
        for p in send_pipes_sockets:
            # print(p[0]==s, p[0], s)
            # print(p[0].getpeername()[1], s.getpeername()[1])

            if p[0].getpeername()[1] == s.getpeername()[1]:
                p[1].send(reply)
                break

    def sendMsg(s, reply):
        time.sleep(5)
        s.send(','.join(reply).encode())
    
    def getNewClock():
        nonlocal gclock
        gclock += 1
        return gclock
    def syncClock(receivedlock):
        nonlocal gclock
        gclock = max(gclock, receivedlock)

    def checkReply():
        if transactionQueue:
            # check enough reply
            clock, client, command = transactionQueue[0]
            if client == myname:
                count = 0
                for c in replyDict:
                    if len(replyDict[c]) > 0:
                        count += 1
                if count >= len(socketsForClients):
                    heapq.heappop(transactionQueue)
                    for c in replyDict:
                        heapq.heappop(replyDict[c])
                    # get grant, send to server
                    data = (client, command)
                    print('************ Get Grant for:', clock, command, " ************")
                    socketForServer.send(','.join(data).encode())
    while True:
        src, msg, clock, s =  pipe.recv()
        print('pipe recev:', src, msg, clock)
        print('QUEUE:', transactionQueue)
        print('REPLY:', replyDict)
        if src == "server":
            # case 1: receive RELEASE from server
            # send release to peers
            for peer in socketsForClients:
                sendToPeer(peer, 'RELEASE')
            checkReply()
        elif src == "input":
            # case 2: get user input
            transaction = (getNewClock(), myname, msg)
            # put in local queue
            heapq.heappush(transactionQueue, transaction)
            # send request to peers
            for s in socketsForClients:
                sendToPeer(s, msg)
        else: 
            # case 3: get msg from peer
            clock = int(clock)
            syncClock(clock)
            if msg == 'REPLY':
                # put into reply queue
                if src not in replyDict:
                    replyDict[src] = []
                heapq.heappush(replyDict[src], clock)
                # print(replyDict)
                checkReply()
            elif msg == 'RELEASE':
                # delete earliest transaction
                if transactionQueue[0][1] == myname:
                    print('something wrong!!!!!!!!!!!')
                heapq.heappop(transactionQueue)
                # print('----pop')
                checkReply()
            else:
                # get request from peer
                transaction = (clock, src, msg)
                # put in local queue
                heapq.heappush(transactionQueue, transaction)
                # reply to peer
                sendToPeer(s, 'REPLY')

# main thread 1
# get keyboard input
# send request to peers
def getInput(pipe):
    EXIT_COMMAND = "exit"
    print('Ready for keyboard input:')
    while True:
        input_str = input()
        if input_str == EXIT_COMMAND:
            break
        pipe.send(("input", input_str,'', None))
# Thread 2
# read messages from server
# send release to peers
def receiveServerMessage(pipe, s):
    while True:
        data = s.recv(1024).decode()
        print('receiveServerMessage:', data)
        if not data:
            s.close()
            break
        pipe.send(("server", "RELEASE",'', None))
# Thread 3,4,5
# read messages from peer
def receivePeerMessage(pipe, s):
    while True:
        data = s.recv(1024).decode()
        print('receivePeerMessage:', data)
        if not data:
            s.close()
            break
        messages = data.split('|')
        for info in messages:
            if info:
                clock, sender, msg = info.split(',')
                pipe.send((sender, msg, clock, s))
                
def connect(ip, port, clientname):
    print('try to connect:', ip, port, clientname)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        print('*****Connected to ', clientname)
        return s
    except socket.error as msg:
        print("Could not connect ", clientname)
        return None

def listen(myport, num):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', myport))
    s.listen(1)

    socketsForClients = []

    print('listening on port', myport, '...')

    connected = 0
    sockets = []
    while 1:
        conn, addr = s.accept()
        sockets.append(conn)
        connected += 1
        print(conn, addr, 'connected')
        if connected >= num:
            print('******All clients connected')
            return sockets


def main():
    # 1. get client name
    global myname
    myname = sys.argv[1]
    print('launching ', myname)

    # 2. get ip+port list
    data = common.readjson()
    me = next(client for client in data['clients'] if client['name'] == myname)
    if not me:
        print('client name not correct!')
        return
    peers = [client for client in data['clients'] if client['name'] != myname]
    
    # 3. connect to server
    socketForServer = connect(data['server']['ip'], data['server']['port'], "server")
    if not socketForServer:
        return

    # 4. try connect to other clients
    socketsForClients = []
    for p in peers:
        s = connect(p['ip'], p['port'], p['name'])
        if s:
            socketsForClients.append(s)
    print('*******connected ', len(socketsForClients), ' clients')
    notConnected = len(peers) - len(socketsForClients)

    # 5. if not connected, listen to other clients
    if (notConnected > 0):
        restClients = listen(me['port'], notConnected)
        socketsForClients.extend(restClients)
    else:
        print('*****All clients connected')

    # finish connecting
    # ******************************************
    send_pipe_process, recv_pipe_process = multiprocessing.Pipe()
    send_pipes_sockets = []
    recv_pipes_sockets = []
    for s in socketsForClients:
        send_pipe_socket, recv_pipe_socket = multiprocessing.Pipe()
        send_pipes_sockets.append((s, send_pipe_socket))
        recv_pipes_sockets.append(recv_pipe_socket)

    # print(socketsForClients)
    # print(send_pipes_sockets)
    thread.startThread(pipeThread, (recv_pipe_process, socketForServer, socketsForClients, send_pipes_sockets))

    # start threads for receive/send message
    thread.startThread(receiveServerMessage, (send_pipe_process, socketForServer))
    
    i = 0
    for s in socketsForClients:
        thread.startThread(receivePeerMessage, (send_pipe_process, s, ))
        thread.startThread(sendPeerMessage, (recv_pipes_sockets[i], s,))
        i += 1



    # read keyboard
    getInput(send_pipe_process)
    
    

if (__name__ == '__main__'): 
    main()