# -*- coding: utf-8 -*-
"""Inventory plugin registry: config section name -> plugin class."""

from .aws import AwsInventory
from .gce import GceInventory
from .ovh import OvhInventory

PLUGINS = {
    plugin.config_key: plugin
    for plugin in (AwsInventory, GceInventory, OvhInventory)
}

__all__ = ['PLUGINS', 'AwsInventory', 'GceInventory', 'OvhInventory']
