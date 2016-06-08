# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
QEMU VM implementation.
"""

from gns3.node import Node
from gns3.image_manager import ImageManager
from gns3.ports.ethernet_port import EthernetPort
from .settings import QEMU_VM_SETTINGS


import logging
log = logging.getLogger(__name__)


class QemuVM(Node):

    """
    QEMU VM.

    :param module: parent module for this node
    :param server: GNS3 server instance
    """
    URL_PREFIX = "qemu"

    def __init__(self, module, server, project):
        super().__init__(module, server, project)

        log.info("QEMU VM instance is being created")
        self._port_name_format = None
        self._port_segment_size = 0
        self._first_port_name = None
        self._linked_clone = True

        qemu_vm_settings = {"usage": "",
                            "qemu_path": "",
                            "hda_disk_image": "",
                            "hdb_disk_image": "",
                            "hdc_disk_image": "",
                            "hdd_disk_image": "",
                            "hda_disk_interface": QEMU_VM_SETTINGS["hda_disk_interface"],
                            "hdb_disk_interface": QEMU_VM_SETTINGS["hdb_disk_interface"],
                            "hdc_disk_interface": QEMU_VM_SETTINGS["hdc_disk_interface"],
                            "hdd_disk_interface": QEMU_VM_SETTINGS["hdd_disk_interface"],
                            "cdrom_image": "",
                            "hda_disk_image_md5sum": "",
                            "hdb_disk_image_md5sum": "",
                            "hdc_disk_image_md5sum": "",
                            "hdd_disk_image_md5sum": "",
                            "cdrom_image_md5sum": "",
                            "boot_priority": QEMU_VM_SETTINGS["boot_priority"],
                            "options": "",
                            "ram": QEMU_VM_SETTINGS["ram"],
                            "cpus": QEMU_VM_SETTINGS["cpus"],
                            "console": None,
                            "console_host": None,
                            "console_type": QEMU_VM_SETTINGS["console_type"],
                            "adapters": QEMU_VM_SETTINGS["adapters"],
                            "adapter_type": QEMU_VM_SETTINGS["adapter_type"],
                            "mac_address": QEMU_VM_SETTINGS["mac_address"],
                            "legacy_networking": QEMU_VM_SETTINGS["legacy_networking"],
                            "platform": QEMU_VM_SETTINGS["platform"],
                            "acpi_shutdown": QEMU_VM_SETTINGS["acpi_shutdown"],
                            "cpu_throttling": QEMU_VM_SETTINGS["cpu_throttling"],
                            "process_priority": QEMU_VM_SETTINGS["process_priority"],
                            "initrd": "",
                            "kernel_image": "",
                            "initrd_md5sum": "",
                            "kernel_image_md5sum": "",
                            "kernel_command_line": ""}

        self.settings().update(qemu_vm_settings)

    def _addAdapters(self, adapters):
        """
        Adds adapters.

        :param adapters: number of adapters
        """

        interface_number = segment_number = 0
        for adapter_number in range(0, adapters):
            if self._first_port_name and adapter_number == 0:
                port_name = self._first_port_name
            else:
                port_name = self._port_name_format.format(
                    interface_number,
                    segment_number,
                    port0=interface_number,
                    port1=1 + interface_number,
                    segment0=segment_number,
                    segment1=1 + segment_number)
                interface_number += 1
                if self._port_segment_size and interface_number % self._port_segment_size == 0:
                    segment_number += 1
                    interface_number = 0
            new_port = EthernetPort(port_name)
            new_port.setAdapterNumber(adapter_number)
            new_port.setPortNumber(0)
            new_port.setHotPluggable(False)
            self._ports.append(new_port)
            log.debug("Adapter {} with port {} has been added".format(adapter_number, port_name))

    def create(self, qemu_path, name=None, node_id=None, port_name_format="Ethernet{0}", port_segment_size=0,
              first_port_name="", linked_clone=True, additional_settings={}, default_name_format=None):
        """
        Creates this QEMU VM.

        :param name: optional name
        :param node_id: Node identifier
        """

        self._linked_clone = linked_clone
        params = {"qemu_path": qemu_path,
                  "linked_clone": linked_clone}
        self._port_name_format = port_name_format
        self._port_segment_size = port_segment_size
        self._first_port_name = first_port_name
        params.update(additional_settings)
        self._create(name, node_id, params, default_name_format)

    def _createCallback(self, result):
        """
        Callback for create.

        :param result: server response
        """

        # create the ports on the client side
        self._addAdapters(self._settings.get("adapters", 0))

    def update(self, new_settings):
        """
        Updates the settings for this QEMU VM.

        :param new_settings: settings dictionary
        """

        params = {}
        for name, value in new_settings.items():
            if name in self._settings and self._settings[name] != value:
                params[name] = value
        if params:
            self._update(params)

    def _updateCallback(self, result):
        """
        Callback for update.

        :param result: server response
        """

        nb_adapters_changed = False
        for name, value in result.items():
            if name in self._settings and self._settings[name] != value:
                log.info("{}: updating {} from '{}' to '{}'".format(self.name(), name, self._settings[name], value))
                if name == "name":
                    # update the node name
                    self.updateAllocatedName(value)
                if name == "adapters":
                    nb_adapters_changed = True
                self._settings[name] = value

        if nb_adapters_changed:
            log.debug("number of adapters has changed to {}".format(self._settings["adapters"]))
            # TODO: dynamically add/remove adapters
            self._ports.clear()
            self._addAdapters(self._settings["adapters"])

    def dump(self):
        """
        Returns a representation of this QEMU VM instance.
        (to be saved in a topology file).

        :returns: representation of the node (dictionary)
        """

        qemu_vm = super().dump()
        qemu_vm["linked_clone"] = self._linked_clone
        qemu_vm["port_name_format"] = self._port_name_format

        if self._port_segment_size:
            qemu_vm["port_segment_size"] = self._port_segment_size
        if self._first_port_name:
            qemu_vm["first_port_name"] = self._first_port_name

        # add the properties
        for name, value in self._settings.items():
            if value is not None and value != "":
                qemu_vm["properties"][name] = value

        return qemu_vm

    def info(self):
        """
        Returns information about this QEMU VM instance.

        :returns: formated string
        """

        if self.status() == Node.started:
            state = "started"
        else:
            state = "stopped"

        info = """QEMU VM {name} is {state}
  Node ID is {id}, server's node ID is {node_id}
  QEMU VM's server runs on {host}
  Console is on port {console} and type is {console_type}
""".format(name=self.name(),
           id=self.id(),
           node_id=self._node_id,
           state=state,
           host=self.compute().id(),
           console=self._settings["console"],
           console_type=self._settings["console_type"])

        port_info = ""
        for port in self._ports:
            if port.isFree():
                port_info += "     {port_name} is empty\n".format(port_name=port.name())
            else:
                port_info += "     {port_name} {port_description}\n".format(port_name=port.name(),
                                                                            port_description=port.description())

        if "usage" in self._settings and len(self._settings["usage"]) > 0:
            info += "  Usage: {}\n".format(self._settings["usage"])

        return info + port_info

    def load(self, node_info):
        """
        Loads a QEMU VM representation
        (from a topology file).

        :param node_info: representation of the node (dictionary)
        """

        super().load(node_info)
        # for backward compatibility
        node_id = node_info.get("qemu_id")
        if not node_id:
            node_id = node_info.get("node_id")
            if not node_id:
                node_id = node_info.get("vm_id")

        linked_clone = node_info.get("linked_clone", True)
        port_name_format = node_info.get("port_name_format", "Ethernet{0}")
        port_segment_size = node_info.get("port_segment_size", 0)
        first_port_name = node_info.get("first_port_name", "")

        # prepare the VM settings
        vm_settings = {}
        for name, value in node_info["properties"].items():
            if name in self._settings:
                vm_settings[name] = value
        name = vm_settings.pop("name")
        qemu_path = vm_settings.pop("qemu_path")
        log.info("QEMU VM {} is loading".format(name))
        self.create(qemu_path, name, node_id, port_name_format, port_segment_size, first_port_name, linked_clone, vm_settings)

    def console(self):
        """
        Returns the console port for this QEMU VM instance.

        :returns: port (integer)
        """

        return self._settings["console"]

    def configPage(self):
        """
        Returns the configuration page widget to be used by the node properties dialog.

        :returns: QWidget object
        """

        from .pages.qemu_vm_configuration_page import QemuVMConfigurationPage
        return QemuVMConfigurationPage

    @staticmethod
    def defaultSymbol():
        """
        Returns the default symbol path for this node.

        :returns: symbol path (or resource).
        """

        return ":/symbols/qemu_guest.svg"

    @staticmethod
    def symbolName():

        return "QEMU VM"

    @staticmethod
    def categories():
        """
        Returns the node categories the node is part of (used by the device panel).

        :returns: list of node categories
        """

        return [Node.end_devices]

    def __str__(self):

        return "QEMU VM"
