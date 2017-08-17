import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.73.168', username='admin', password='admin')
#
# def ssh_call(stdin, stdout, string, *args):
#     data = 'puts [{}]\n\r'.format(string % args)
#     stdin.write(data)
#     stdin.flush()
#     l = len(stdout.channel.in_buffer)
#     while not l:
#         l = len(stdout.channel.in_buffer)
#     data = stdout.read(l)
#     return data


def run_command(command):
    stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)
    return stdout.read() + '\n' + stderr.read()


# stdin, stdout, stderr = ssh.exec_command('')

# print ssh_call(stdin, stdout, 'ls -a')
print run_command('bash -l -c "bpsh;"')
print run_command('source .bashrc')
print run_command('source .bash_profile')
print run_command('echo $PATH')
print run_command('echo "puts [info var]" > test5.tcl')
# print run_command('echo "\$bps iluAddLicenseServers 192.168.26.26" >> test.tcl')

print run_command('bpsh test5.tcl')
print ''
