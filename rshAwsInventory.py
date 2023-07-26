#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/opt/rsh')
import rsh.config
import traceback
import subprocess
import json
import inspect
import re
import os
import yaml

# defs
def runCmd(commands,communicate=True,stdoutJson=True):
    """ запуск shell команд, вернёт хеш:
    {
        "stdout": stdout,
        "stderr": stderr,
        "exitCode": exitCode,
    }
    """

    defName = inspect.stack()[0][3]
    rsh.config.logging.debug("%s: '%s'" % (defName,commands))
    if communicate:
        process = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = process.communicate(commands.encode())
        returnCode = process.returncode
        try:
            outFormatted = out.rstrip().decode("utf-8")
        except:
            outFormatted = out.decode("utf-8")
        if stdoutJson:
            try:
                stdout = json.loads(outFormatted)
            except Exception:
                rsh.config.logging.error("%s: failed runCmd, cmd='%s', error='%s'" % (defName,commands,traceback.format_exc()))
                return None
        else:
            stdout = outFormatted
        return {
            "stdout": stdout,
            "stderr": err,
            "exitCode": returnCode,
        }
    else:
        subprocess.call(commands, shell=True)
        return None

def getInstancesInfo(region):
    defName = inspect.stack()[0][3]

    instancesInfo = list()
    describeInstances = runCmd("aws ec2 --region %s describe-instances" % region)['stdout']
    reservations = describeInstances['Reservations']
    for reservation in reservations:
        instances = reservation['Instances']
        for instance in instances:
            if rsh.config.cfg['awsInventory']['skipNotRunningInstance']:
                if instance['State']['Name'] != 'running':
                    continue
            info = {
                'dc': instance['Placement']['AvailabilityZone'],
                'tags': instance['Tags'],
            }
            for tag in instance['Tags']:
                if tag['Key'] == 'Name':
                    info['host'] = tag['Value']

            info['sshHost'] = instance.get(rsh.config.cfg['awsInventory']['sshHostField'], 'unknown')
            for hostInfoField in rsh.config.cfg['awsInventory']['hostInfoFields']:
                info[hostInfoField] = instance.get(hostInfoField, 'unknown')
            if info not in instancesInfo:
                instancesInfo.append(info)
    return instancesInfo

if __name__ == "__main__":
    defName = "main"
    rsh.config.logging.debug("%s: cfg='%s'" % (defName,json.dumps(rsh.config.cfg,indent=4)))

    if rsh.config.cfg['awsInventory']['regions']:
        regions = rsh.config.cfg['awsInventory']['regions']
    else:
        regions = runCmd("aws ec2 describe-regions --query 'Regions[].RegionName'")['stdout']
    instancesInfoArray = list()
    for region in regions:
        instancesInfoArray = instancesInfoArray + getInstancesInfo(region)

    rsh.config.logging.debug("%s: instancesInfoArray='%s'" % (defName,json.dumps(instancesInfoArray,indent=4)))

    inventory = dict()
    inventory['hosts'] = dict()
    inventory['groups'] = dict()
    for instanceInfo in instancesInfoArray:
        # hosts {{
        host = instanceInfo['host']
        if host not in inventory['hosts']:
            inventory['hosts'][host] = { 'sshHost': instanceInfo['sshHost'] }
            for hostInfoField in rsh.config.cfg['awsInventory']['hostInfoFields']:
                inventory['hosts'][host][hostInfoField] = instanceInfo[hostInfoField]
        # }}
        # groups {{
        for tag in instanceInfo['tags']:
            if tag['Key'] in rsh.config.cfg['awsInventory']['skipTagsForMakeGroups']:
                continue
            groupName = 'tag_' + tag['Key'].replace('-','_') + '_' + tag['Value'].replace('-','_')
            groupName = re.sub(r'\s+', '_', groupName)
            if groupName not in inventory['groups']:
                inventory['groups'][groupName] = list()
            if host not in inventory['groups'][groupName]:
                inventory['groups'][groupName].append(host)
        # }}
        # groups by dc {{
        groupName = 'dc_'+ instanceInfo['dc']
        groupName = re.sub(r'\s+', '_', groupName)
        if groupName not in inventory['groups']:
            inventory['groups'][groupName] = list()
        if host not in inventory['groups'][groupName]:
            inventory['groups'][groupName].append(host)
        # }}

    # generating inventory file {{
    rsh.config.logging.debug("%s: inventory='%s'" % (defName,inventory))
    with open(os.path.expanduser(rsh.config.cfg['inventoryFilePath']), 'w') as f:
        yaml.dump(inventory, f, default_flow_style=False)
    # }}
