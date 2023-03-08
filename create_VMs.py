#!/usr/bin/env python
#
# VMware vSphere Python SDK
# Copyright (c) 2021 VMware, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Example for creating a VM
"""

import sys
from pyVmomi import vim
from pyVim.task import WaitForTask
import atexit
import ssl

from pyVim import connect
from pyVmomi import vim
import pdb
import sys
import os
import math

def vconnect(hostIP, username=None, password=None, port=None):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # disable our certificate checking for lab

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
    return service_instance

def create_vm(si, vm_name, minMHz, minMem, minStorage, datacenter_name=None, host_ip=None, datastore_name=None):
    content = si.RetrieveContent()

    container = content.rootFolder  # starting point to look into
    viewType = [vim.ResourcePool]  # object types to look for
    recursive = True  # whether we should look into it recursively
    containerView = content.viewManager.CreateContainerView(container, viewType, recursive)  # create container view
    resourcePools = containerView.view

    datastoreFound = False
    SelectedHost = None
    SelectedDS = None
    SelectedPool = None
    for pool in resourcePools:
        # get pool quick stats
        quickStats = pool.summary.quickStats

        # get memory info
        ConfiguredHostMem = pool.summary.configuredMemoryMB
        HostMemUsage = quickStats.hostMemoryUsage
        GuestConsumedMem = quickStats.guestMemoryUsage
        GuestPrivateMem = quickStats.privateMemory
        sharedMem = quickStats.sharedMemory
        AvailMem = ConfiguredHostMem - HostMemUsage

        # get Compute info
        CurrentCPUDemand = quickStats.overallCpuDemand
        MaxcpuAllocation = pool.summary.config.cpuAllocation.limit
        AvailMHz = MaxcpuAllocation - CurrentCPUDemand
        print(f"Available Mem is {AvailMem}MB and available compute capacity is {AvailMHz}MHz for {pool.name}")

        if 'mhz' in minMHz.lower():
            minMHz = int([x for x in minMHz.lower().split('mhz')][0])
        if 'mb' in minMem.lower():
            minMem = int([x for x in minMem.lower().split('mb')][0])
        if 'gb' in minStorage.lower():
            minStorage = int([x for x in minStorage.lower().split('gb')][0])

        if ((AvailMem < minMem) or (AvailMHz < minMHz)):
            print(f"Unable to allocate enough resources on the \"{pool.name}\" resource pool")
            continue

        # get host info
        cpu = pool.parent
        hostList = cpu.host

        for host in hostList:
            if host.summary.overallStatus.lower() is 'red':
                continue
            else:
                dsList = host.datastore
                for datastore in dsList:
                    freespace = datastore.summary.freeSpace
                    freespace = math.floor(freespace/(1024*1024*1024))
                    if (freespace) < int(minStorage):
                        continue
                    else:
                        SelectedHost = host
                        SelectedDS = datastore
                        SelectedPool = pool
                        datastoreFound = True
                        break
                if (datastoreFound):
                    break
        
        if (datastoreFound):
            print(f"Selected datastore \"{datastore.summary.name}\" with {freespace}GB on it")
            break

    if not (datastoreFound):
        print(f"Unable to allocate enough resources on any resource pool, quitting")
        sys.exit(1)
    else:
        datastore_path = '[' + SelectedDS.name + '] ' + vm_name
        config = create_config_spec(SelectedDS.name, vm_name, minMem, SelectedHost.network[0], int(minStorage))

        vmfolder = SelectedDS.parent.parent.vmFolder
        try:
            WaitForTask(vmfolder.CreateVm(config, pool=SelectedPool, host=SelectedHost))
            print(f"VM {vm_name} created")
        except vim.fault.DuplicateName:
            print("VM duplicate name: %s" % vm_name, file=sys.stderr)
        except vim.fault.AlreadyExists:
            print("VM name %s already exists." % vm_name, file=sys.stderr)

def create_config_spec(datastore_name, name, memory, network, sizeGB, guest="otherGuest",
                       annotation="Sample", cpus=1):
    config = vim.vm.ConfigSpec()
    config.annotation = annotation
    config.memoryMB = int(memory)
    config.guestId = guest
    config.name = name
    config.numCPUs = cpus

    # List of all device controllers we plan to attach to this VM
    vmControllers = []

    # Adding the NIC
    nicspec = vim.vm.device.VirtualDeviceSpec()
    nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    nic_type = vim.vm.device.VirtualVmxnet3()
    nicspec.device = nic_type
    nicspec.device.deviceInfo = vim.Description()
    nicspec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
    nicspec.device.backing.network = network
    nicspec.device.backing.deviceName = network.name
    nicspec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
    nicspec.device.connectable.startConnected = True
    nicspec.device.connectable.allowGuestControl = True
    vmControllers.append(nicspec)

    # SCSI controller
    scsi_ctlr = vim.vm.device.VirtualDeviceSpec()
    scsi_ctlr.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    scsi_ctlr.device = vim.vm.device.ParaVirtualSCSIController()
    scsi_ctlr.device.deviceInfo = vim.Description()
    #scsi_ctlr.device.slotInfo = vim.vm.device.VirtualDevice.PciBusSlotInfo()
    #scsi_ctlr.device.slotInfo.pciSlotNumber = 16
    scsi_ctlr.device.controllerKey = 100
    scsi_ctlr.device.unitNumber = 3
    scsi_ctlr.device.busNumber = 0
    scsi_ctlr.device.hotAddRemove = True
    scsi_ctlr.device.sharedBus = 'noSharing'
    scsi_ctlr.device.scsiCtlrUnitNumber = 7
    vmControllers.append(scsi_ctlr)    

    # vDisk
    unit_number = 0
    controller = scsi_ctlr.device # this is the controller we defined above
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.fileOperation = "create"
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk_spec.device = vim.vm.device.VirtualDisk()
    disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
    disk_spec.device.backing.diskMode = 'persistent'
    disk_spec.device.backing.thinProvisioned = True
    disk_spec.device.backing.fileName = '[%s]%s.vmdk' % ( datastore_name, name )
    disk_spec.device.unitNumber = unit_number
    disk_spec.device.capacityInKB = sizeGB * 1024 * 1024
    disk_spec.device.controllerKey = controller.key
    vmControllers.append(disk_spec)
    
    # finalizing the spec
    files = vim.vm.FileInfo()
    files.vmPathName = "[" + datastore_name + "] " + name
    config.files = files
    config.deviceChange = vmControllers
    return config

def main():
    try:
        vcsahostIP = sys.argv[1]
        vcsaUserName = sys.argv[2]
        vcsaPasswd = sys.argv[3]
        vcsaAdminPort = sys.argv[4]
        vmName = sys.argv[5]
        minimumMHz = sys.argv[6]
        minimumMBs = sys.argv[7]
        minimumGB = sys.argv[8]
        
    except IndexError as e:
        print(f"usage:\n{sys.argv[0]} vcsahostIP vcsaUserName vcsaPasswd vcsaAdminport vmName compute-capacity-MHz memory-in-MB disk-space-GB")
        print(e)
        sys.exit(1)

    si = vconnect(vcsahostIP,vcsaUserName,vcsaPasswd,vcsaAdminPort)
    create_vm(si, vmName, minimumMHz, minimumMBs, minimumGB)

# start this thing
if __name__ == "__main__":
    main()
