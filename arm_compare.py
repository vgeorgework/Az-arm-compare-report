#!/usr/bin/python
# Import the needed credential and management objects from the libraries.
from azure.identity import AzureCliCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
# import os

# Acquire a credential object using CLI-based authentication.
credential = AzureCliCredential()

# Retrieve subscription ID from environment variable.
#subscription_id = <YOUR SID>
# Obtain the management object for resources.
resource_client = ResourceManagementClient(credential, subscription_id)
compute_client = ComputeManagementClient(credential, subscription_id)

# Retrieve the list of resource groups
group_list = resource_client.resource_groups.list()

summary_list_vmss=list()#used for vmss summary report
summary_list_images=list()#used for image summary report
def generate_report(data_list,rg_group):  
    """Show the groups in formatted output"""
    
    # For VMSS
    if data_list[0]=='v' and len(data_list)>1:
        print("*" * (35 * 6))
        print("\nVirtual Machine SS Comparison Report for Resource Group: "+rg_group)
        column_width = 35
        print("\nResource Name".ljust(column_width)+ "ScaleSetCount".ljust(column_width)+\
            "Resource Name".ljust(column_width)+"ARM Count".ljust(column_width)+"Comments")
        print("-" * (column_width * 5))
        for data in data_list[1:]:
            print(f"{data[0]:<{column_width}}{data[1]:<{column_width}}{data[2]:<{column_width}}{data[3]:<{column_width}}{data[4]}")
            if data[4]:
                summary_list_vmss.append((data))
              

    # For VMSS vmsize
    if data_list[0]=='vs' and len(data_list)>1:
        print("\nVMSS VM size comparison Report for Resource Group: "+rg_group)
        column_width = 40
        print("\nScaleSetName".ljust(column_width)+"Resource Value".ljust(column_width)+"ARM Value")
        print("-" * (column_width * 3))
        for data in data_list[1:]:
            print(f"{data[0]:<{column_width}}{data[1]:<{column_width}}{data[2]}")

    #For DISK
    if data_list[0]=='d' and len(data_list)>1:
        print("\nDisk comparision Report for Resource Group: "+rg_group)
        column_width = 40
        print("\nDisk Name".ljust(column_width)+"Disk Type".ljust(30)+"Disk Type in ARM".ljust(20)\
            +"Disk Size in ARM".ljust(20)+"Disk Size in Azure portal".ljust(column_width)+"Comments")
        print("-" * (column_width * 5))
        for data in data_list[1:]:
            print(f"{data[0]:<{column_width}}{data[1]:<{30}}{data[2]:<{20}}{data[3]:<{20}}{data[4]:<{column_width}}{data[5]}")
            if data[5]:
                summary_list_images.append((data))

    #For VM image
    if data_list[0]=='vd' and len(data_list)>1:
        print("\nImage comparision Report for Resource Group: "+rg_group)
        column_width = 40
        print("\nVMSS".ljust(column_width)+"VM instance".ljust(column_width)+"ARM Value".\
            ljust(column_width)+"Image from azure portal")
        print("-" * (column_width * 4))
        for data in data_list[1:]:
            for i in data:
                print(f"{i[0]:<{column_width}}{i[1]:<{column_width}}{i[2]:<{column_width}}{i[3]}")
    
def summary_report():
    #Summary report after each RG 
    if len(summary_list_vmss)>2:
        print("\n########################vmss Summary Report########################")
        column_width = 35
        print("\nResource Name".ljust(column_width)+ "Comments")
        print("-" * (column_width * 2))
        for data in summary_list_vmss:
            print(f"{data[0]:<{column_width}}{data[4]}")
        summary_list_vmss.clear()
    if len(summary_list_images)>2:
        print("\n########################image Summary Report########################")
        column_width = 40
        print("\nDisk Name".ljust(column_width)+"Comments")
        print("-" * (column_width * 2))
        for data in summary_list_images:
            print(f"{data[0]:<{column_width}}{data[5]}")
        print("#" * (column_width * 5))
        summary_list_images.clear()
   

def _find_disk_details(rg,disk_name):
    """params: resource group and disk name returns disk_obj"""
    disk_obj=compute_client.disks.get(rg,disk_name)
    return disk_obj

def _read_arm(get_val):
    """get 2 values find ans and return its dict"""
    import json
    json_file = json.load(open('arms/az-qa-config.json')) #change your ARM file here
    if len(get_val)==1:
        return json_file.get(get_val[0],False)
    elif len(get_val)==3:
        return json_file.get(get_val[0],False).get(get_val[1],False).get(get_val[2],False)

def find_all_resources(rg):
    """To find all the resources from an RG"""
    return resource_client.resources.list_by_resource_group(rg,expand = "createdTime,changedTime")

def find_vm_from_vmss(ss_name,rg):
    """To find the vms from vmss 
    params: resource group and scaleset name
    return VM list"""
    return [vm for vm in compute_client.virtual_machine_scale_set_vms.list(rg,ss_name)]

def find_rg():
    """To find all the RG from a subscription which have tags"""
    return [rg for rg in group_list if ((rg.tags) and (rg.tags.get('env_type',False)))]

def _find_deviation(current_val,arm_val):
    """helper func to get the diff and return result in HRF """
    if current_val<arm_val:
        txt="expected value is: "+str(arm_val)+", Difference: "+str(arm_val-current_val)
        return txt
    if current_val>arm_val:
        txt="expected value is: "+str(arm_val)+", Difference: "+str(current_val-arm_val)
        return txt
    else:
        return ""


r_count_list=list('v')
disk_list=list('d')
vm_size=["vs"]
vm_details=["vd"]
#vm.os_profile.admin_username
def find_vm_count(resource,rg_name):  
    """func to create list for report generate """
    if (resource.type=="Microsoft.Compute/virtualMachineScaleSets" and resource.name.find("storm-ss")!=-1):
        vm_objs=find_vm_from_vmss(resource.name,rg_name)
        arm_val=_read_arm(["parameters","machineImageName","value"])
        # vm_details.append([[resource.name,vm.name,arm_val,vm.storage_profile.image_reference.id.split('/')[-1]] for vm in vm_objs])
        vm_count=len(vm_objs)
        arm_val=_read_arm(["parameters","stormCount","value"])
        r_count_list.append([resource.name,vm_count,"stormCount",arm_val,_find_deviation(vm_count,arm_val)])
        vm_size.append([resource.name,resource.sku.name,_read_arm(["parameters","stormVMSize","value"])])

    if (resource.type=="Microsoft.Compute/virtualMachineScaleSets" and resource.name.find("swarm-manager-ss")!=-1):
        vm_objs=find_vm_from_vmss(resource.name,rg_name)
        arm_val=_read_arm(["parameters","machineImageName","value"])
        # vm_details.append([[resource.name,vm.name,arm_val,vm.storage_profile.image_reference.id.split('/')[-1]] for vm in vm_objs])
        vm_count=len(vm_objs)
        arm_val=_read_arm(["parameters","managerCount","value"])
        r_count_list.append([resource.name,vm_count,"managerCount",arm_val,_find_deviation(vm_count,arm_val)])
        vm_size.append([resource.name,resource.sku.name,_read_arm(["parameters","managerVMSize","value"])])

    if (resource.type=="Microsoft.Compute/virtualMachineScaleSets" and resource.name.find("sensu-ss")!=-1):
        vm_objs=find_vm_from_vmss(resource.name,rg_name)
        arm_val=_read_arm(["parameters","machineImageName","value"])
        # vm_details.append([[resource.name,vm.name,arm_val,vm.storage_profile.image_reference.id.split('/')[-1]] for vm in vm_objs])
        vm_count=len(vm_objs)
        arm_val=_read_arm(["parameters","sensuCount","value"])
        r_count_list.append([resource.name,vm_count,"sensuCount",arm_val,_find_deviation(vm_count,arm_val)])
        vm_size.append([resource.name,resource.sku.name,_read_arm(["parameters","sensuVMSize","value"])])

    if (resource.type=="Microsoft.Compute/virtualMachineScaleSets" and resource.name.find("tools-ss")!=-1):
        vm_objs=find_vm_from_vmss(resource.name,rg_name)
        arm_val=_read_arm(["parameters","machineImageName","value"])
        # vm_details.append([[resource.name,vm.name,arm_val,vm.storage_profile.image_reference.id.split('/')[-1]] for vm in vm_objs])
        vm_count=len(vm_objs)
        arm_val=_read_arm(["parameters","toolsCount","value"])
        r_count_list.append([resource.name,vm_count,"toolsCount",arm_val,_find_deviation(vm_count,arm_val)])
        vm_size.append([resource.name,resource.sku.name,_read_arm(["parameters","toolsVMSize","value"])])

    if (resource.type=="Microsoft.Compute/virtualMachineScaleSets" and resource.name.find("utilset1-ss")!=-1):
        vm_objs=find_vm_from_vmss(resource.name,rg_name)
        arm_val=_read_arm(["parameters","machineImageName","value"])
        # vm_details.append([[resource.name,vm.name,arm_val,vm.storage_profile.image_reference.id.split('/')[-1]] for vm in vm_objs])
        vm_count=len(vm_objs)
        arm_val=_read_arm(["parameters","utilSet1Count","value"])
        r_count_list.append([resource.name,vm_count,"utilSet1Count",arm_val,_find_deviation(vm_count,arm_val)])
        vm_size.append([resource.name,resource.sku.name,_read_arm(["parameters","utilSet1VMSize","value"])])

    if (resource.type=="Microsoft.Compute/virtualMachineScaleSets" and resource.name.find("utilset2-ss")!=-1):
        vm_objs=find_vm_from_vmss(resource.name,rg_name)
        arm_val=_read_arm(["parameters","machineImageName","value"])
        # vm_details.append([[resource.name,vm.name,arm_val,vm.storage_profile.image_reference.id.split('/')[-1]] for vm in vm_objs])
        vm_count=len(vm_objs)
        arm_val=_read_arm(["parameters","utilSet2Count","value"])
        r_count_list.append([resource.name,vm_count,"utilSet2Count",arm_val,_find_deviation(vm_count,arm_val)])
        vm_size.append([resource.name,resource.sku.name,_read_arm(["parameters","utilSet2VMSize","value"])])

    if (resource.type=="Microsoft.Compute/virtualMachineScaleSets" and resource.name.find("zk-kafka-ss")!=-1):
        vm_objs=find_vm_from_vmss(resource.name,rg_name)
        arm_val=_read_arm(["parameters","machineImageName","value"])
        # vm_details.append([[resource.name,vm.name,arm_val,vm.storage_profile.image_reference.id.split('/')[-1]] for vm in vm_objs])
        vm_count=len(vm_objs)
        arm_val=_read_arm(["parameters","zookeeperCount","value"])
        r_count_list.append([resource.name,vm_count,"zookeeperCount",arm_val,_find_deviation(vm_count,arm_val)])
        vm_size.append([resource.name,resource.sku.name,_read_arm(["parameters","zookeeperKafkaVMSize","value"])])

    if (resource.type=="Microsoft.Compute/virtualMachineScaleSets" and resource.name.find("elk-ss")!=-1):
        vm_objs=find_vm_from_vmss(resource.name,rg_name)
        arm_val=_read_arm(["parameters","machineImageName","value"])
        # vm_details.append([[resource.name,vm.name,arm_val,vm.storage_profile.image_reference.id.split('/')[-1]] for vm in vm_objs])
        vm_count=len(vm_objs)
        arm_val=_read_arm(["parameters","elkCount","value"])
        r_count_list.append([resource.name,vm_count,"elkCount",arm_val,_find_deviation(vm_count,arm_val)])
        vm_size.append([resource.name,resource.sku.name,_read_arm(["parameters","elkVMSize","value"])])

    if (resource.type=="Microsoft.Compute/virtualMachineScaleSets" and resource.name.find("nim1-ss")!=-1):
        vm_objs=find_vm_from_vmss(resource.name,rg_name)
        arm_val=_read_arm(["parameters","machineImageName","value"])
        # vm_details.append([[resource.name,vm.name,arm_val,vm.storage_profile.image_reference.id.split('/')[-1]] for vm in vm_objs])
        vm_count=len(vm_objs)
        arm_val=_read_arm(["parameters","esNim1Count","value"])
        r_count_list.append([resource.name,vm_count,"esNim1Count",arm_val,_find_deviation(vm_count,arm_val)])
        vm_size.append([resource.name,resource.sku.name,_read_arm(["parameters","esNim1VMSize","value"])])

    if (resource.type=="Microsoft.Compute/virtualMachineScaleSets" and resource.name.find("nim2-ss")!=-1):
        vm_objs=find_vm_from_vmss(resource.name,rg_name)
        arm_val=_read_arm(["parameters","machineImageName","value"])
        # vm_details.append([[resource.name,vm.name,arm_val,vm.storage_profile.image_reference.id.split('/')[-1]] for vm in vm_objs])
        vm_count=len(vm_objs)
        arm_val=_read_arm(["parameters","esNim2Count","value"])
        r_count_list.append([resource.name,vm_count,"esNim2Count",arm_val,_find_deviation(vm_count,arm_val)])
        vm_size.append([resource.name,resource.sku.name,_read_arm(["parameters","esNim2VMSize","value"])])

    if (resource.type=="Microsoft.Compute/virtualMachineScaleSets" and resource.name.find("es-ss")!=-1):
        vm_objs=find_vm_from_vmss(resource.name,rg_name)
        arm_val=_read_arm(["parameters","machineImageName","value"])
        # vm_details.append([[resource.name,vm.name,arm_val,vm.storage_profile.image_reference.id.split('/')[-1]] for vm in vm_objs])
        vm_count=len(vm_objs)
        arm_val=_read_arm(["parameters","esCount","value"])
        r_count_list.append([resource.name,vm_count,"esCount",arm_val,_find_deviation(vm_count,arm_val)])
        vm_size.append([resource.name,resource.sku.name,_read_arm(["parameters","esVMSize","value"])])
            
    #Disk compare
    if (resource.type=="Microsoft.Compute/disks" and resource.name.find("ss-es")!=-1):
        arm_val_size=_read_arm(["parameters","sizeOfEsDiskInGB","value"])
        arm_disk_type=_read_arm(["parameters","esDiskType","value"])
        curr_dsk_siz=_find_disk_details(rg_name,resource.name).disk_size_gb
        disk_list.append([resource.name,resource.sku.name,arm_disk_type,curr_dsk_siz,arm_val_size,_find_deviation(curr_dsk_siz,arm_val_size)])

    if (resource.type=="Microsoft.Compute/disks" and resource.name.find("ss-zk")!=-1):
        arm_val_size=_read_arm(["parameters","sizeOfZookeeperDiskInGB","value"])
        arm_disk_type=_read_arm(["parameters","zkDiskType","value"])
        curr_dsk_siz=_find_disk_details(rg_name,resource.name).disk_size_gb
        disk_list.append([resource.name,resource.sku.name,arm_disk_type,curr_dsk_siz,arm_val_size,_find_deviation(curr_dsk_siz,arm_val_size)])

    if (resource.type=="Microsoft.Compute/disks" and resource.name.find("ss-kafka")!=-1):
        arm_val_size=_read_arm(["parameters","sizeOfKafkaDiskInGB","value"])
        arm_disk_type=_read_arm(["parameters","kafkaDiskType","value"])
        curr_dsk_siz=_find_disk_details(rg_name,resource.name).disk_size_gb
        disk_list.append([resource.name,resource.sku.name,arm_disk_type,curr_dsk_siz,arm_val_size,_find_deviation(curr_dsk_siz,arm_val_size)])

    if (resource.type=="Microsoft.Compute/disks" and resource.name.find("influxdb")!=-1):
        arm_val_size=_read_arm(["parameters","sizeOfInfluxdbDiskInGB","value"])
        arm_disk_type=_read_arm(["parameters","influxDiskType","value"])
        curr_dsk_siz=_find_disk_details(rg_name,resource.name).disk_size_gb
        disk_list.append([resource.name,resource.sku.name,arm_disk_type,curr_dsk_siz,arm_val_size,_find_deviation(curr_dsk_siz,arm_val_size)])

    if (resource.type=="Microsoft.Compute/disks" and resource.name.find("elk-ss-elk")!=-1):
        arm_val_size=_read_arm(["parameters","sizeOfElkDiskInGB","value"])
        arm_disk_type=_read_arm(["parameters","elkDiskType","value"])
        curr_dsk_siz=_find_disk_details(rg_name,resource.name).disk_size_gb
        disk_list.append([resource.name,resource.sku.name,arm_disk_type,curr_dsk_siz,arm_val_size,_find_deviation(curr_dsk_siz,arm_val_size)])

    if (resource.type=="Microsoft.Compute/disks" and resource.name.find("nimbus1")!=-1):
        arm_val_size=_read_arm(["parameters","sizeOfNimbusDiskInGB","value"])
        arm_disk_type=_read_arm(["parameters","nimbusDiskType","value"])
        curr_dsk_siz=_find_disk_details(rg_name,resource.name).disk_size_gb
        disk_list.append([resource.name,resource.sku.name,arm_disk_type,curr_dsk_siz,arm_val_size,_find_deviation(curr_dsk_siz,arm_val_size)])

    if (resource.type=="Microsoft.Compute/disks" and resource.name.find("nimbus2")!=-1):
        arm_val_size=_read_arm(["parameters","sizeOfNimbusDiskInGB","value"])
        arm_disk_type=_read_arm(["parameters","nimbusDiskType","value"])
        curr_dsk_siz=_find_disk_details(rg_name,resource.name).disk_size_gb
        disk_list.append([resource.name,resource.sku.name,arm_disk_type,curr_dsk_siz,arm_val_size,_find_deviation(curr_dsk_siz,arm_val_size)])
            
flag=0 #;-)
for rg in find_rg():
    if rg.tags.get('env_type')=="dev": #change your tag here
        r_count_list=list('v') #quick fix
        disk_list=list('d')
        vm_size=["vs"]
        # vm_details=["vd"]
        for resource in find_all_resources(rg.name):
            find_vm_count(resource,rg.name)
            flag=1
        if flag==1:
            generate_report(r_count_list,rg.name)
            generate_report(vm_size,rg.name)
            # generate_report(vm_details,rg.name)
            generate_report(disk_list,rg.name)
            summary_report()
            r_count_list.clear()
            vm_size.clear()
            disk_list.clear()
            # vm_details.clear()
            flag=0
# print(">>>>>>>>>>>>>>>>>>>>>>>>>>..",r_count_list)

# generate_report(r_count_list)
# generate_report(vm_size)
# generate_report(disk_list)
# generate_report(vm_details)