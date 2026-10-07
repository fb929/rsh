#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import subprocess
import json
import traceback

# common functions
class CommonMixin:
    def runCmd(self,commands,communicate=True,stdoutJson=True):
        """ run shell command, returned hash:
        {
            "stdout": stdout,
            "stderr": stderr,
            "exitCode": exitCode,
        }
        """

        self.logger.debug("'%s'", commands)
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
                    self.logger.error("failed parse JSON from cmd='%s', exitCode=%s, stderr='%s', error='%s'", commands,returnCode,err.decode("utf-8", "replace").rstrip(),traceback.format_exc())
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
