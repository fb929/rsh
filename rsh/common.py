#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import inspect
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

        defName = inspect.stack()[0][3]
        self.logger.debug("%s: '%s'" % (defName,commands))
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
                    self.logger.logging.error("%s: failed runCmd, cmd='%s', error='%s'" % (defName,commands,traceback.format_exc()))
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
