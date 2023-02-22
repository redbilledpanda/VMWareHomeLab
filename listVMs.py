import atexit
import ssl
from pyVim import connect
from pyVmomi import vim
import pdb
import sys
import os

def vconnect(hostIP, username=None, password=None, port=None):
    if (True):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # disable our certificate checking for lab
    else:
        context = ssl.create_default_context()
        context.options |= ssl.OP_NO_TLSv1_3
    #cipher = 'DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-GCM-SHA256'
    #context.set_ciphers(cipher)
   
    pdb.set_trace()
    if (port):
        if '@' not in username:
            sys.exit("Please include domain name with username")
        service_instance = connect.SmartConnect(host=str(hostIP),  # build python connection to vSphere
                                                #user="Administrator@vsphere.local",
                                                user=username,
                                                pwd=password,
                                                port=port,
                                                sslContext=context)
    else:
        service_instance = connect.SmartConnect(host=str(hostIP),  # build python connection to vSphere
                                                user=username,
                                                pwd=password,
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
