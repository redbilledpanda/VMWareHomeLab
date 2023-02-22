# VMWareHomeLab
Recreating the vmware vsphere based lab at home

This page describes what I had done to recreate the vsphere homelab lest I forget or perhaps it might help someone else as well. Let's begin:

# PRE-REQUISITES:
1. [ESX iso installer](https://customerconnect.vmware.com/downloads/details?productId=742&downloadGroup=ESXI670)
2. [vSphere installer iso](https://customerconnect.vmware.com/en/evalcenter?p=vsphere-eval-8)
3. A machine with atleast 32GB of RAM, 4 processors (~ total 8 cores), 500 GB of disk (preferably SSD)
      - even in the small configuration (Tiny), vSphere needs around 14 GB/2vCPUs and around 100G of disk space
      - ESX itself would require 4GB/2vCPUs
4. VMWare workstation 15.x and above (virtualbox is way slower)      
      
# Steps:
## Installing ESXi
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

### Before proceeding, let's take a detour understanding basic virtual Networking:

Shown below is the network topology that we want to achieve. On the left is a 'vmknic', a logical endpoint for ESXi kernel through which it talks to the outside world. On the right we have the vmnic, which represents the newly added (v)NIC.

![image](https://user-images.githubusercontent.com/46345560/220547436-e4e99d55-e0d9-4d35-b3f5-cf77397211d8.png)

To re-iterate these concepts, here are the vmknic details:

![image](https://user-images.githubusercontent.com/46345560/220551920-d0a98a63-60c2-4a8f-93af-1be4fbae3755.png)

Notice the absence of attributes like the MAC address, link speed etc. Hence this is no more than a logical endpoint for the vmkernel, and is used for things like vMotion, vSAN etc

Here are the details pertaining to the corresponding vmnic:

![image](https://user-images.githubusercontent.com/46345560/220552546-a8aaac11-bd60-44d7-b3ee-bb6cb786b7c3.png)

As expected, it has details pertaining to link speed, it's PCI address, MAC address etc.

_Continuing the steps_:
4. Log into through the web interface https://{ip-address-of-mgmt-networkadapter} .
   - From storage tab, create a VMFS datastore over the newly added 100GB disk
   - From networking tab, create a new vSwitch and select the host-only vNIC as it's uplink
   - add a new vmknic to this vSwitch
      . every vmknic is part of a portgroup, so this new vmknic will be part of a portgroup that we'll call StoragePG
      . this vmknic should be configured with static IP in the 172.x subnet and once configured make sure it is pingable from host

## vCenter Server:
- Extract/Mount the ISO
- Navigate to `\VMware-VCSA-all-8.0.0-21216066\vcsa-cli-installer\templates\install`
- copy `embedded_vCSA_on_ESXi.json` to `\VMware-VCSA-all-8.0.0-21216066\vcsa-cli-installer\win32`

This is how it looks:
```json
{
    "__version": "2.13.0",
    "__comments": "Sample template to deploy a vCenter Server Appliance with an embedded Platform Services Controller on an ESXi host.",
    "new_vcsa": {
        "esxi": {
            "hostname": "<FQDN or IP address of the ESXi host on which to deploy the new appliance>",
            "username": "root",
            "password": "<Password of the ESXi host root user. If left blank, or omitted, you will be prompted to enter it at the command console during template verification.>",
            "deployment_network": "VM Network",
            "datastore": "<A specific ESXi host datastore, or a specific datastore in a datastore cluster.>"
        },
        "appliance": {
            "__comments": [
                "You must provide the 'deployment_option' key with a value, which will affect the vCenter Server Appliance's configuration parameters, such as the vCenter Server Appliance's number of vCPUs, the memory size, the storage size, and the maximum numbers of ESXi hosts and VMs which can be managed. For a list of acceptable values, run the supported deployment sizes help, i.e. vcsa-deploy --supported-deployment-sizes"
            ],
            "thin_disk_mode": true,
            "deployment_option": "small",
            "name": "Embedded-vCenter-Server-Appliance"
        },
        "network": {
            "ip_family": "ipv4",
            "mode": "static",
            "system_name": "<FQDN or IP address for the appliance. Optional when the mode is Static. Remove this if using dhcp.>",
            "ip": "<Static IP address. Remove this if using dhcp.>",
            "prefix": "<Network prefix length. Use only when the mode is 'static'. Remove if the mode is 'dhcp'. This is the number of bits set in the subnet mask; for instance, if the subnet mask is 255.255.255.0, there are 24 bits in the binary version of the subnet mask, so the prefix length is 24. If used, the values must be in the inclusive range of 0 to 32 for IPv4 and 0 to 128 for IPv6.>",
            "gateway": "<Gateway IP address. Remove this if using dhcp.>",
            "dns_servers": [
                "<DNS Server IP Address. Optional when the mode is Static. Remove this if using dhcp.>"
            ]
        },
        "os": {
            "password": "<Appliance root password; refer to --template-help for password policy. If left blank, or omitted, you will be prompted to enter it at the command console during template verification.>",
            "ntp_servers": "time.nist.gov",
            "ssh_enable": false
        },
        "sso": {
            "password": "<vCenter Single Sign-On administrator password; refer to --template-help for password policy. If left blank, or omitted, you will be prompted to enter it at the command console during template verification.>",
            "domain_name": "vsphere.local"
        }
    },
    "ceip": {
        "description": {
            "__comments": [
                "++++VMware Customer Experience Improvement Program (CEIP)++++",
                "VMware's Customer Experience Improvement Program (CEIP) ",
                "provides VMware with information that enables VMware to ",
                "improve its products and services, to fix problems, ",
                "and to advise you on how best to deploy and use our ",
                "products. As part of CEIP, VMware collects technical ",
                "information about your organization's use of VMware ",
                "products and services on a regular basis in association ",
                "with your organization's VMware license key(s). This ",
                "information does not personally identify any individual. ",
                "",
                "Additional information regarding the data collected ",
                "through CEIP and the purposes for which it is used by ",
                "VMware is set forth in the Trust & Assurance Center at ",
                "http://www.vmware.com/trustvmware/ceip.html . If you ",
                "prefer not to participate in VMware's CEIP for this ",
                "product, you should disable CEIP by setting ",
                "'ceip_enabled': false. You may join or leave VMware's ",
                "CEIP for this product at any time. Please confirm your ",
                "acknowledgement by passing in the parameter ",
                "--acknowledge-ceip in the command line.",
                "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
            ]
        },
        "settings": {
            "ceip_enabled": true
        }
    }
}
```

From the above JSON, cull the comment from CEIP and set it to disabled
```json
    "ceip": {
        "settings": {
            "ceip_enabled": false
        }
    }
```

Next, change the OS section so that it looks like this:
```json
        "os": {
            "password": "SomeSillyPwd", <--- used by the 'root' user
            "time_tools_sync": true,
            "ssh_enable": true
        },
```

Next, unless you have a properly configured DNS server, set it to the loopback address like so:
```json
        "network": {
            "ip_family": "ipv4",
            "mode": "static",
            "system_name": "192.168.160.170", <--|
            "ip": "192.168.160.170", <-----------| - both of these should be the same if no DNS server configured
            "prefix": "24",
            "gateway": "192.168.160.2",
            "dns_servers": [
                "127.0.0.1" <--- set it to loopback address is no DNS server configured
            ]
        },
```

Finally in the appliance section, change the `deployment_option` to `tiny` and make sure `thin_disk_mode` is set to true. 

Finally, note that we have two password sections in the config. One of them is the os section described above. It is used for logging the 'root' user into the  VAMI (Virtual Appliance Management Interface) accessed via "https://{vcsa-address}:5480", where vcsa-address in this case is 192.168.160.170. Second in the password for user `Administrator` for the `vsphere.local` domain name. It is this user that will actually administer the vSphere web client interface available at "https://{vcsa-address}/ui". 

```json
        "sso": {
            "password": "SomeSillyPwd1",
            "domain_name": "vsphere.local"
        }
```
Finally, make sure all other details are properly matching and then save the file. Navigate to `\VMware-VCSA-all-8.0.0-21216066\vcsa-cli-installer\win32` and run the following command: `.\vcsa-deploy.exe install --accept-eula --skip-ovftool-verification --verbose --no-ssl-certificate-verification embedded_vCSA_on_ESXi.json`

If everything goes fine, you'll see a VM in the virtual machines section of ESXi. It took me little more than 90m for this to get deployed. This is nested virtualization in action.
![image](https://user-images.githubusercontent.com/46345560/220574294-d9c85e63-0d52-4ba6-b866-4f1c7a3fc9e7.png)

Finally, turn the VM ON, it will take around 15m to be fully ON. Wait until you see the vCenter console like this:
![image](https://user-images.githubusercontent.com/46345560/220575313-bfbfb541-fcd7-4cf5-a4c6-3a1e27f1f393.png)

Hover your mouse over this and log in using the `root` user. Make sure that the management network is what you had setup in the JSON file above and that it is static. Next log into the web client interface at `https://192.168.160.170/ui` using the Administrator@vsphere.local account and the SSO password that you set up in the JSON above. It should look like this:
![image](https://user-images.githubusercontent.com/46345560/220589463-edc3d198-7f79-4213-a8d8-8c3211ce0990.png)

Then log into the VAMI at https://192.168.160.170:5480/ with the Administrator@vsphere.local account and check the services tab to make sure the vSphere client service is healthy and started. Often times on systems with restricted resources, this service takes time to start. Your CPU fans are blowing at max speed when this service starts and once when CPU utilization is back to 'normal' (aka not 100%), most often your vSphere client service has started. 
![image](https://user-images.githubusercontent.com/46345560/220589724-1b01f8b0-1f57-44c9-88b8-78061a75f761.png)

Finally we can now log into the vSphere client with our SSO credentials. Once in, navigate to the Administration section (using the hamburger menu) and under Single Sign on, click on 'Users and Groups', then select the Users tab and add two new users, `pyvmomi` and `pyvmomiReadOnly` for the 'vsphere.local' domain. 
![image](https://user-images.githubusercontent.com/46345560/220582992-a6f6f657-d584-487c-994c-a3ca19e8f0e2.png)

Next, navigate to the Administrator group under the 'Groups' tab and click on the 'Administrators' group. Add the pyvmomi user to this group:
![image](https://user-images.githubusercontent.com/46345560/220583748-02b50d81-5355-49a1-88cc-7c52d060a27e.png)

Next, under the groups tab, search for `readonly` (single word), select the `ReadOnlyUsers` group and add pyvmomiReadOnly user to it
![image](https://user-images.githubusercontent.com/46345560/220584294-d1ec47ba-d341-4594-86fc-fe80273588d7.png)

This completes our initial setup 



