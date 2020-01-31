import socket
import pickle
import sys
import json
import threading
import multiprocessing
import heapq
import time
from random import randrange

# my client name
myname = ''
# local logic clock
gclock = 0
# log (clock, sender, receiver, amount)
blockchain = []
# Time Table
TT = []
data_lock = threading.Lock()

def startThread(f, arguments):
    p = threading.Thread(target=f, args=arguments)
    p.daemon = True
    p.start()
    return p
def readjson():
    # read from file
    with open('config.json') as json_file:
        data = json.load(json_file)
    # format data
    for client in data['clients']:
        client['port'] = int(client['port'])
    return data

def sendPeerMessage(s, pipe, peername):
    while True:
        data = pipe.recv()
        print('sendPeerMessage to client', peername, ':', data)
        time.sleep(randrange(5))
        s.send(pickle.dumps(data))

def recvPeerMessage(s, peername):
    while True:
        data = s.recv(1024)
        if not data:
            s.close()
            break

        data = pickle.loads(data)
        print('receivePeerMessage from client', peername, ':', data)
        # update TT and log
        otherTT, log = data
        with data_lock:
            updateTT(otherTT, peername)
            # update log
            # ???? performance
            for t in log:
                if t not in blockchain:
                    blockchain.append(t)

def updateTT(otherTT, owner):
    NUM = len(TT)
    for j in range(NUM):
        for k in range(NUM):
            TT[j][k] = max(TT[j][k], otherTT[j][k])
    i = int(myname)-1
    k = int(owner)-1
    for j in range(NUM):
        TT[i][j] = max(TT[i][j], otherTT[k][j])

def getInput(peers):
    EXIT_COMMAND = "exit"
    print('Ready for keyboard input:')
    while True:
        input_str = input()
        if input_str == EXIT_COMMAND:
            break
        command = input_str.split()
        if command[0] == 'M' and len(command) == 2:
            x, peer = command
            if peer == myname:
                print("Don't send message to yourself!")
                continue
            # send TT + Log
            sendLogs = []
            with data_lock:
                # check TT[peer] to add logs and send to peer
                for t in blockchain:
                    (clock, sender, receiver, amount) = t
                    # if peer don't know sender's t of this clock, send t
                    if TT[int(peer)-1][int(sender)-1] < clock:
                        sendLogs.append(t)
            next(x for x in peers if x['name'] == peer)['send_pipe'].send((TT, sendLogs,))
            print("Message Sent to client", peer)
        elif command[0] == 'B' and len(command) == 2:
            x, owner = command
            # get balance
            balance = 10
            with data_lock:
                for t in blockchain:
                    clock, sender, receiver, amount = t
                    if sender == owner:
                        balance -= amount
                    if receiver == owner:
                        balance += amount
            print('Balance of client', owner, 'is :', balance)
        elif command[0] == 'T' and len(command) == 3:
            # transaction
            c, recevier, amount = command
            with data_lock:
                # update clock
                global gclock
                gclock += 1
                # update log
                blockchain.append((gclock, myname, recevier, int(amount)))
                # update TT
                TT[int(myname)-1][int(myname)-1] = gclock
            print("Transaction Completed")
        else:
            print('WRONG COMMAND!')


def main():
    # 1. get client name
    global myname
    myname = sys.argv[1]
    print('launching client', myname)

    # 2. get ip+port list
    data = readjson()
    me = next(client for client in data['clients'] if client['name'] == myname)
    if not me:
        print('client name not correct!')
        return
    # peers: all client information
    # in each client: 
    #   name:
    #   ip:
    #   port:
    #   socket:
    #   send_pipe:
    #   recv_pipe:
    peers = [client for client in data['clients'] if client['name'] != myname]
    for client in data['clients']:
        TT.append([0 for client in data['clients']])

    # 3. try connect to other clients
    for p in peers:
        ip = p['ip']
        port = p['port']
        peername = p['name']
        print('try to connect client:', peername, ip, port)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, port))
            s.send(myname.encode())
            print('*****Connected to client', peername)
            p['socket'] = s
        except socket.error as msg:
            print("Could not connect client", peername)
    print('*******connected ', len([client for client in peers if 'socket' in client]), ' clients')

    # 4. if not connected, listen to other clients
    if len([client for client in peers if 'socket' in client]) < len(peers):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', me['port']))
        s.listen(1)

        print('listening on port', me['port'], '...')
        while 1:
            conn, addr = s.accept()
            peername = conn.recv(1024).decode()
            print('client', peername, addr, 'connected')

            next(x for x in peers if x['name'] == peername)['socket'] = conn
            if len([p for p in peers if 'socket' in p]) == len(peers):
                print('******All clients connected')
                s.close()
                break
    else:
        print('*****All clients connected')
    # finish connecting*******************************************

    # Start Threads
    for p in peers:
        send_pipe, recv_pipe = multiprocessing.Pipe()
        p['send_pipe'] = send_pipe
        p['recv_pipe'] = recv_pipe
        startThread(sendPeerMessage, (p['socket'], recv_pipe, p['name']))
        startThread(recvPeerMessage, (p['socket'], p['name'],))

    # read keyboard
    getInput(peers)
     
if (__name__ == '__main__'): 
    main()