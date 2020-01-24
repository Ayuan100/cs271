import threading
import queue
import time
import socket
import json
import sys
import common

blockchain = []
def getBalance(clientName):
    balance = 10
    for t in blockchain:
        sender, receiver, amount = t
        if sender == clientName:
            balance -= amount
        if receiver == clientName:
            balance += amount
    return balance

def transferMoney(sender, receiver, amount):
    blockchain.append((sender, receiver, amount))

def process(owner, msg):
    print('process:', owner, msg)

    if not owner:
        return None
    
    if msg == 'B':
        return 'Balance: ' + str(getBalance(owner))
    command, receiver, amount = msg.split()
    if command == 'T':
        amount = int(amount)
        if getBalance(owner) >= amount:
            transferMoney(owner, receiver, amount)
            return 'SUCCESS'
        else:
            return 'INCORRECT'
    return None

def recvThread(s):
    global test
    print('RECV Thread listening')
    while True:
        data = s.recv(1024).decode()
        print('----------------')
        print('receive:', data)
        if not data:
            s.close()
            break
        try:
            owner, msg = data.split(',')
            result = process(owner, msg)
            print('send result:', result)
            s.send(result.encode())
        except:
            print(f"Something went wrong....oops...")
            s.send('EXCEPTION'.encode())
            continue


def main():
    data = common.readjson()
    myport = data['server']['port']

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', myport))
    s.listen(1)

    print('listening on port', myport, '...')

    threads = []
    while True:
        print('wait to accept..')
        conn, addr = s.accept()
        print(conn, addr, 'connected')
        x = threading.Thread(target=recvThread, args=(conn,))
        x.start()
        threads.append(x)
    for t in threads:
        thread.releaseThread(t)

if (__name__ == '__main__'): 
    main()