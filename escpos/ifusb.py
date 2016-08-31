# -*- coding: utf-8 -*-
#
# escpos/usb.py
#
# Copyright 2015 Base4 Sistemas Ltda ME
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
#
import re

import usb.core
import usb.util


PRINTER_CLASS = 0x07


class PrinterFinder(object):

    def __init__(self, device_class=PRINTER_CLASS):
        self._device_class = device_class


    def __call__(self, device):
        if device.bDeviceClass == self._device_class:
            print '(A) ---'
            return True

        for config in device:
            interface = usb.util.find_descriptor(
                    config,
                    bInterfaceClass=self._device_class)
            if interface is not None:
                print '(B) ---'
                return True

        return False


def find_printers(**kwargs):
    """

    :returns: Tuple of ``usb.core.Device`` objects found.

    :rtype: tuple

    """
    devices = []
    query = usb.core.find(custom_match=PrinterFinder(), **kwargs)
    for result in query:
        if isinstance(result, usb.core.Device):
            devices.append(result)
        if isinstance(result, usb.core.Configuration):
            devices.append(result.device)
    return tuple(devices)


class USBConnection(object):
    """Implements a simple USB connection."""

    RE_VENDOR_PRODUCT = re.compile(r'((0x)?(?P<vendor>[0-9a-f]*)):((0x)?(?P<product>[0-9a-f]*))', re.I)
    RE_KEY_VALUE = re.compile(r'(?P<key>\w+)\ *={1}\ *((0x)?(?P<value>[0-9a-f]*))', re.I)


    @staticmethod
    def create(setting):
        """Instantiate a :class:`USBConnection` object based on settings
        string like ``0492:8760,interface=0,out_ep=3,in_ep=0``.
        """
        defaults = dict(interface=0, ep_in=0, ep_out=0)

        match = USBConnection.RE_VENDOR_PRODUCT.match(setting)
        if match is None:
            raise ValueError('Invalid settings string: {!r}'.format(setting))

        vendor_id = int(match.group('vendor'), 16)
        product_id = int(match.group('product'), 16)

        for match in USBConnection.RE_KEY_VALUE.finditer(setting):
            defaults[match.group('key')] = int(match.group('value'), 16)

        return USBConnection(vendor_id, product_id, **defaults)


    def __init__(self, vendor_id, product_id,
            interface=0,
            ep_in=0,
            ep_out=0,
            timeout=2000):
        super(USBConnection, self).__init__()
        self.usbport = None
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.interface = interface
        self.ep_in = ep_in
        self.ep_out = ep_out
        self.timeout = timeout


    def __repr__(self):
        r = '{0}(0x{1:04x}, 0x{2:04x}, interface=0x{3:x}, ep_in=0x{4:x}, ep_out=0x{5:x})'
        return r.format(self.__class__.__name__,
                self.vendor_id, self.product_id,
                self.interface, self.ep_in, self.ep_out)


    def _raise_with_details(self, message, exctype=RuntimeError):
        raise exctype('{}: {!r} (idVendor={:04x}, idProduct={:04x}, '
                'interface={:x}, ep_in={:x}, ep_out={:x})'.format(
                        message,
                        self.usbport,
                        self.vendor_id,
                        self.product_id,
                        self.interface,
                        self.ep_in,
                        self.ep_out))


    def catch(self):
        self.usbport = usb.core.find(
                idVendor=self.vendor_id, idProduct=self.product_id)

        if self.usbport is None:
            self._raise_with_details('cannot find specified printer',
                    exctype=ValueError)

        if self.usbport.is_kernel_driver_active(self.interface):
            try:
                self.usbport.detach_kernel_driver(self.interface)
            except usb.core.USBError as e:
                msg = 'unable to detach kernel driver: {:s}'.format(e)
                self._raise_with_details(msg, exctype=usb.core.USBError)

        try:
            self.usbport.set_configuration()
            self.usbport.reset()
        except usb.core.USBError as e:
            msg = 'unable to set configuration: {:s}'.format(e)
            self._raise_with_details(msg, exctype=usb.core.USBError)


    def write(self, data):
        self.usbport.write(self.ep_out, data, timeout=self.timeout)


    def read(self):
        return ''
