import subprocess
import sys

print ("main")

subprocess.call(['open', '-a', 'Terminal', '--args', '/home'])
# subprocess.call(['lxterminal -e  python3 test.py'], cwd='/home', shell=True)
# subprocess.Popen([sys.executable, 'test.py'], stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.STDOUT, shell=True)
# subprocess.Popen([sys.executable, 'test.py'], creationflags = subprocess.CREATE_NEW_CONSOLE)

# subprocess.Popen("test.py", shell=False)

