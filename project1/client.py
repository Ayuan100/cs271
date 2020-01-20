import socket
import sys
import common
import thread
import multiprocessing
import heapq
import time

myname = ''

def pipeThread(pipe, socketForServer, socketsForClients):
    replyQueue = []
    transactionQueue = []
    gclock = 0
 
    def sendToPeer(s, msg):
        reply = (str(getNewClock()), myname, msg)
        thread.startTemp(sendMsg, (s, reply,))
        
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

    while True:
        src, msg, clock, s =  pipe.recv()
        # print('pipe recev:', src, msg, clock)

        if src == "server":
            # case 1: receive RELEASE from server
            # send release to peers
            for peer in socketsForClients:
                sendToPeer(peer, 'RELEASE')
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
            # print('QUEUE:', transactionQueue)

            if msg == 'REPLY' or msg == 'RELEASE':
                if msg == 'REPLY':
                    # put into reply queue
                    heapq.heappush(replyQueue, clock)
                elif msg == 'RELEASE':
                    # delete earliest transaction
                    heapq.heappop(transactionQueue)
                if transactionQueue:
                    # check enough reply
                    clock, client, command = transactionQueue[0]
                    if client == myname:
                        if len(replyQueue) >= len(socketsForClients):
                            heapq.heappop(transactionQueue)
                            for s in socketsForClients:
                                heapq.heappop(replyQueue)
                            # get grant, send to server
                            data = (client, command)
                            socketForServer.send(','.join(data).encode())
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
        clock, sender, msg = data.split(',')
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
    send_pipe, recv_pipe = multiprocessing.Pipe()

    thread.startThread(pipeThread, (recv_pipe, socketForServer, socketsForClients))

    # start threads for socket
    thread.startThread(receiveServerMessage, (send_pipe, socketForServer))
    for s in socketsForClients:
        thread.startThread(receivePeerMessage, (send_pipe, s))

    # read keyboard
    getInput(send_pipe)
    
    

if (__name__ == '__main__'): 
    main()