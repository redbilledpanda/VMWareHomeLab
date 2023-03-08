import atexit
import ssl
import subprocess

from pyVim import connect
from pyVmomi import vim
import pdb
import sys
import os

def vconnect(hostIP, username=None, password=None, port=None):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # disable our certificate checking for lab

    #pdb.set_trace()
    hostIP = hostIP.strip('[\'\"]')
    username = username.strip('[\'\"]')
    password = password.strip('[\'\"]')
    port = port.strip('[\'\"]')


    if '@' not in username:
        sys.exit("Please include domain name with username")
    service_instance = connect.SmartConnect(host=str(hostIP),  # build python connection to vSphere
                                            #user="Administrator@vsphere.local",
                                            user=username,
                                            pwd=password,
                                            port=int(port),
                                            sslContext=context)

    atexit.register(connect.Disconnect, service_instance)  # build disconnect logic

    content = service_instance.RetrieveContent()

    container = content.rootFolder  # starting point to look into
    viewType = [vim.VirtualMachine]  # object types to look for
    recursive = True  # whether we should look into it recursively
    containerView = content.viewManager.CreateContainerView(container, viewType, recursive)  # create container view
    children = containerView.view

    for child in children:  # for each statement to iterate all names of VMs in the environment
        summary = child.summary
        print(summary.config.name)

    print('++++++++++++++++++++++++++++++++++++++++++++++++')
    container = content.rootFolder  # starting point to look into
    viewType = [vim.Datacenter]  # object types to look for
    recursive = True  # whether we should look into it recursively
    containerView = content.viewManager.CreateContainerView(container, viewType, recursive)  # create container view
    children = containerView.view

    for child in children:  # for each statement to iterate all names of VMs in the environment
        datacentername = child.name
        print(datacentername)

# doing this allows us to prevent side affects while importing this package
# into the interpreter. Used to check execution environment
# were we called directly from the command-line?
if __name__ == '__main__':
    try:
        vcsahostIP = sys.argv[1]
        vcsaUserName = sys.argv[2]
        vcsaPasswd = sys.argv[3]
        vcsaAdminPort = sys.argv[4]
    except IndexError as e:
        print("usage:\n listVMs.py vcsahostIP vcsaUserName vcsaPasswd vcsaAdminport")
        print(e)

    vconnect(vcsahostIP, vcsaUserName, vcsaPasswd, vcsaAdminPort)
