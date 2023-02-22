# VMWareHomeLab
Recreating the vmware vsphere based lab at home

This page describes what I had done to recreate the vsphere homelab lest I forget or perhaps it might help someone else as well. Let's begin:

PRE-REQUISITES:
1. [ESX iso installer](https://customerconnect.vmware.com/downloads/details?productId=742&downloadGroup=ESXI670)
2. [vSphere installer iso](https://customerconnect.vmware.com/en/evalcenter?p=vsphere-eval-8)
3. A machine with atleast 32GB of RAM, 4 processors (~ total 8 cores), 500 GB of disk (preferably SSD)
      - even in the small configuration (Tiny), vSphere needs around 14 GB/2vCPUs and around 100G of disk space
      - ESX itself would require 4GB/2vCPUs
4. VMWare workstation 15.x and above (virtualbox is way slower)      
      
Steps:
1. Install ESXi on the workstation as you would any other VM (but use custom setup)
    - HW compatibility at 15.x
    - at least 2 vCPUs and 4GB of RAM
    - 2 network adapters (1 configured for NAT and other a host-only network, configure workstation using network editor so your host only network is a part of       the 172.x subnet
    - around 5GB of backing store for the OS (10 is preferred, preferrably on an SSD)
2. Log into the console and configure the management network by assigning a static IP on it, 
   - I prefer keeping ipv6 disabled
   - DNS server addr = gateway IP
   - From troubleshooting options, enable ESXi shell and SSH
   - Once all config done, turn it off (F2)
3. Add another vDisk (100 GB recommended, since vSphere VM itself needs around 50G, even with thin provisioning) and then turn the VM on.

Before proceeding, let's take a detour understanding basic virtual Networking:
Shown below is the network topology that we want to achieve. On the left is a 'vmknic', a logical endpoint for ESXi kernel through which it talks to the outside world. On the right we have the vmnic, which represents the newly added (v)NIC.
![image](https://user-images.githubusercontent.com/46345560/220547436-e4e99d55-e0d9-4d35-b3f5-cf77397211d8.png)

To re-iterate these concepts, here are the vmknic details:
![image](https://user-images.githubusercontent.com/46345560/220551920-d0a98a63-60c2-4a8f-93af-1be4fbae3755.png)
Notice the absence of attributes like the MAC address, link speed etc. Hence this is no more than a logical endpoint for the vmkernel, and is used for things like vMotion, vSAN etc

Here are the details pertaining to the corresponding vmnic:
![image](https://user-images.githubusercontent.com/46345560/220552546-a8aaac11-bd60-44d7-b3ee-bb6cb786b7c3.png)
As expected, it has details pertaining to link speed, it's PCI address, MAC address etc.

Continuing the steps:
4. Log into through the web interface https://{ip-address-of-mgmt-networkadapter} .
   - From storage tab, create a VMFS datastore over the newly added 100GB disk
   - From networking tab, create a new vSwitch and select the host-only vNIC as it's uplink
   - add a new vmknic to this vSwitch
      . every vmknic is part of a portgroup, so this new vmknic will be part of a portgroup that we'll call StoragePG
      . this vmknic should be configured with static IP in the 172.x subnet and once configured make sure it is pingable from host
