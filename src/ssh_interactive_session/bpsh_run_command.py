import paramiko
from retrying import retry
import time

RETRY_SECOND = 1000
RETRY_MINUTE = RETRY_SECOND * 60


def run_cmd(cmd, ssh_host, username, password):
    ssh = paramiko.SSHClient()
    run_cmd_retry(cmd, ssh_host, username, password, ssh)
    ssh.close()


@retry(stop_max_delay=RETRY_MINUTE * 10, wait_fixed=RETRY_SECOND * 60)
def run_cmd_retry(cmd, ssh_host, username, password, ssh):
    expiration = time.time() + 60 * 5  # 5 minutes from now
    while time.time() < expiration:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ssh_host, username=username, password=password)

        chan = ssh.invoke_shell()
        buff = ''
        while not buff.endswith('bps> '):
            resp = chan.recv(9999)
            buff += resp
            print(resp)

        # Ssh and wait for the password prompt.
        chan.send('bpsh' + '\n')

        buff = ''
        while not buff.endswith('% '):
            resp = chan.recv(9999)
            buff += resp
            print(resp)

        chan.send(cmd + '\n')

        buff = ''
        while not buff.endswith('% '):
            resp = chan.recv(9999)
            buff += resp
            print(resp)

