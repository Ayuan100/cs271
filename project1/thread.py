from multiprocessing import Process
from multiprocessing import current_process
import threading

def startTemp(f, arguments):
    p = threading.Thread(target=f, args=arguments)
    p.daemon = True
    p.start()
    return p

def startThread(f, arguments):
    p = Process(target=f, args=arguments)
    p.start()
    return p

def releaseThread(p):
    p.join()

def getID():
    return current_process()