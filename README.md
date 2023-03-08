# Background
This repository mainly contains some python scripts that I'm writing to revise about pyvmomi, that I had worked with sometime back. Recreating the vmware vsphere based lab at home is a moderately involved procedure, the details of which can be read from [here](mysite-not-up-yet). [pyvmomi](https://github.com/vmware/pyvmomi) is a vmware supplied SDK for the VMware vSphere API that allows you to manage ESX, ESXi, and vCenter. A (very) brief introduction to it can be read from [here](https://blogs.vmware.com/vsphere/2012/02/introduction-to-the-vsphere-api-part-1.html).

## Testing the setup

### Retrieving information from the vcenter server
We'll test our setup with a small python script that [lists all VMs](https://github.com/redbilledpanda/VMWareHomeLab/blob/WIP/listVMs.py) on the Vcenter Server Appliance (henceforth referred to as vcsa). (Install pyvmomi)[https://pypi.org/project/pyvmomi/], preferably in a virtualenv if you don't want to have it installed system-wide. 

Once done, run the script like so: `python.exe .\listVMs.py ${vcsaHostIp} pyvmomi@vsphere.local ${SSO Password} 443`. It will print the name(s) of VMs and the datacenter(s). In my case here, I have just one VM, which is the vcsa VM and a single datacenter.

### Creating a new VM
A VM is an object, which (much like a real machine), is made up of many other objects that work together to run it. Imagine things like a vdisk, vCPUs, network adapters, SCSI controllers and the likes. All this constitutes the 'configuration specification (ConfigSpec)' of that particular VM and is the basis of VM construction through pyvmomi (or any other automation tool).

Needless to say, elements within the config spec are all represented by objects. These objects are all linked together in a sort of a tree (hierarchical ordering) with the VM object (that which describes a VM) at the 'root'. So it looks somewhat like this:
VM

    Configuration Specification
    |---->Devices
          |---->Network device
          |-------->Link1
          |-------->Link2
          |---->Disk Controller
          |-------->Disk1
          |-------->Disk2

We refer to [this](https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/create_vm.py) example from the pyvmomi community samples. A brief snippet from it is shown here:

```python
def create_vm(si, vm_name, datacenter_name, host_ip, datastore_name=None):

    content = si.RetrieveContent()
    destination_host = pchelper.get_obj(content, [vim.HostSystem], host_ip)
    source_pool = destination_host.parent.resourcePool
    if datastore_name is None:
        datastore_name = destination_host.datastore[0].name

    config = create_config_spec(datastore_name=datastore_name, name=vm_name)
    for child in content.rootFolder.childEntity:
        if child.name == datacenter_name:
            vm_folder = child.vmFolder  # child is a datacenter
            break
    else:
        print("Datacenter %s not found!" % datacenter_name)
        sys.exit(1)

    try:
        WaitForTask(vm_folder.CreateVm(config, pool=source_pool, host=destination_host))
        print("VM created: %s" % vm_name)
    except vim.fault.DuplicateName:
        print("VM duplicate name: %s" % vm_name, file=sys.stderr)
    except vim.fault.AlreadyExists:
        print("VM name %s already exists." % vm_name, file=sys.stderr)
```
'*si*' is the `service instance` that is obtained by way of the `connect.SmartConnect` function, usage of which was described in the 'listVMs.py' file above. The `destination_host` is an object that denotes the host on which we'd like to host our new VM. A 'resource pool' is what the name says it is, aka a pool of resources. From the perspective of a host machine, all the physical resources that a host provides are it's resources. With vSphere, since everything has been engineered from the ground up with distributed computing in mind, vSphere first clusters all discrete resources from all hosts in the datacenter and then flattens it. This is then referred to as a 'resource pool' and can then be used within 
the vim ecosystem as a shared resource. This is a crude explanation of it, but I hope we get the picture. [Here](https://vdc-repo.vmware.com/vmwb-repository/dcr-public/1ef6c336-7bef-477d-b9bb-caa1767d7e30/82521f49-9d9a-42b7-b19b-9e6cd9b30db1/vim.ResourcePool.html) is the official documentation from vmware.

If the user has no preference for a particular datastore, the very first datastore belonging to the host is selected. Next, a 'config spec' as described above is created from scratch using the `create_config_spec` routine which looks like this:
```python
def create_config_spec(datastore_name, name, memory=4, guest="otherGuest",
                       annotation="Sample", cpus=1):
    config = vim.vm.ConfigSpec()
    config.annotation = annotation
    config.memoryMB = int(memory)
    config.guestId = guest
    config.name = name
    config.numCPUs = cpus
    files = vim.vm.FileInfo()
    files.vmPathName = "["+datastore_name+"]"
    config.files = files
    return config
```
As can be seen, the datastore name as well as the VM name are required parameters whereas other parameters have default values. Lets take a sneak peek at the `vim.vm.ConfigSpec` object provided by vmware. Here's [more](https://vdc-repo.vmware.com/vmwb-repository/dcr-public/c476b64b-c93c-4b21-9d76-be14da0148f9/04ca12ad-59b9-4e1c-8232-fd3d4276e52c/SDK/vsphere-ws/docs/ReferenceGuide/vim.vm.ConfigSpec.html) on that. As we can see from that, it has a bunch of properties, almost all of them optional (*btw isn't it weird vmware marks all optional properties with a* <span style="color:red">*</span> *??*). But what good is a VM without many of those properties anyways, which is why we add a bunch of properties here. This routine creates a VM with no network or storage controllers. We can extend this by adding a bunch of devices as part of the *deviceChange* property (which is of type [VirtualDeviceConfigSpec](https://vdc-repo.vmware.com/vmwb-repository/dcr-public/c476b64b-c93c-4b21-9d76-be14da0148f9/04ca12ad-59b9-4e1c-8232-fd3d4276e52c/SDK/vsphere-ws/docs/ReferenceGuide/vim.vm.device.VirtualDeviceSpec.html)). Let's add a NIC to it like so:
```python
vmControllers = []

nicspec = vim.vm.device.VirtualDeviceSpec()
nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
nic_type = vim.vm.device.VirtualVmxnet3()
nicspec.device = nic_type
nicspec.device.deviceInfo = vim.Description()
nicspec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
nicspec.device.backing.network = net_name
nicspec.device.backing.deviceName = net_name.name
nicspec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
nicspec.device.connectable.startConnected = True
nicspec.device.connectable.allowGuestControl = True
vmControllers.append(nicspec)
```
Documentation on the virtual device object is [here](https://vdc-repo.vmware.com/vmwb-repository/dcr-public/c476b64b-c93c-4b21-9d76-be14da0148f9/04ca12ad-59b9-4e1c-8232-fd3d4276e52c/SDK/vsphere-ws/docs/ReferenceGuide/vim.vm.device.VirtualDevice.html). This gets extended by various virtual devices like a virtual NIC, virtual Disk, virtual floppy etc, each providing some unique set of attributes making sense for only that particular device type. In this case we are adding a [vmxnet3](https://vdc-repo.vmware.com/vmwb-repository/dcr-public/c476b64b-c93c-4b21-9d76-be14da0148f9/04ca12ad-59b9-4e1c-8232-fd3d4276e52c/SDK/vsphere-ws/docs/ReferenceGuide/vim.vm.device.VirtualVmxnet3.html) device as the NIC.

In a similar manner, we now add a [SCSI controller](https://vdc-repo.vmware.com/vmwb-repository/dcr-public/3d076a12-29a2-4d17-9269-cb8150b5a37f/8b5969e2-1a66-4425-af17-feff6d6f705d/doc/vim.vm.device.VirtualSCSIController.html):
```python
scsi_ctlr = vim.vm.device.VirtualDeviceSpec()
scsi_ctlr.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
scsi_ctlr.device = vim.vm.device.ParaVirtualSCSIController()
scsi_ctlr.device.deviceInfo = vim.Description()
scsi_ctlr.device.slotInfo = vim.vm.device.VirtualDevice.PciBusSlotInfo()
scsi_ctlr.device.slotInfo.pciSlotNumber = 16
scsi_ctlr.device.controllerKey = 100
scsi_ctlr.device.unitNumber = 3
scsi_ctlr.device.busNumber = 0
scsi_ctlr.device.hotAddRemove = True
scsi_ctlr.device.sharedBus = 'noSharing'
scsi_ctlr.device.scsiCtlrUnitNumber = 7
vmControllers.append(scsi_ctlr)
```
A SCSI controller controls SCSI disks and sits on it's own bus and can drive a maximum of 15 devices. More information [here](https://docs.vmware.com/en/VMware-vSphere/7.0/com.vmware.vsphere.vm_admin.doc/GUID-5872D173-A076-42FE-8D0B-9DB0EB0E7362.html) and [here](https://www.nakivo.com/blog/scsi-controller-and-other-vmware-controller-types/). Above values are typical values

Finally, let's attach a [vDisk](https://vdc-repo.vmware.com/vmwb-repository/dcr-public/c476b64b-c93c-4b21-9d76-be14da0148f9/04ca12ad-59b9-4e1c-8232-fd3d4276e52c/SDK/vsphere-ws/docs/ReferenceGuide/vim.vm.device.VirtualDisk.html) to the above controller:
```python
unit_number = 0
sizeGB = 16
controller = scsi_ctr.device
disk_spec = vim.vm.device.VirtualDeviceSpec()
disk_spec.fileOperation = "create"
disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
disk_spec.device = vim.vm.device.VirtualDisk()
disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
disk_spec.device.backing.diskMode = 'persistent'
disk_spec.device.backing.fileName = '[%s] %s/%s.vmdk' % ( datastore.name, vm_name, vm_name )
disk_spec.device.unitNumber = unit_number
disk_spec.device.capacityInKB = sizeGB * 1024 * 1024
disk_spec.device.controllerKey = controller.key
vmControllers.append(disk_spec)
```
We can finally add pass this device list to the `config spec` as part of the `create_config_spec` function so the snippet loks like so:
```python
    config = vim.vm.ConfigSpec()
    config.annotation = annotation
    config.memoryMB = int(memory)
    config.guestId = guest
    config.name = name
    config.numCPUs = cpus
        
    config.deviceChange = vmControllers # <--- we added this
    files = vim.vm.FileInfo()
    files.vmPathName = "["+datastore_name+"]"
    config.files = files
```
Having extended the config, the rest of the code is exactly as described in the [sample](https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/create_vm.py)
