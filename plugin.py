# Freebox Python Plugin
#
# Author: supermat & ilionel : https://github.com/ilionel/PluginDomoticzFreebox/
# Credit: https://matdomotique.wordpress.com/2018/03/25/plugin-freebox-pour-domoticz/
#
"""
<plugin key="Freebox" name="Freebox Python Plugin" author="supermat & ilionel" version="1.4" wikilink="https://www.domoticz.com/wiki/Plugins" externallink="https://matdomotique.wordpress.com/2018/03/25/plugin-freebox-pour-domoticz">
    <params>
        <param field="Address" label="Freebox URL (avec http[s]://)" width="400px" required="true" default="https://mafreebox.freebox.fr"/>
        <param field="Port" label="Port" width="100px" required="true" default="443"/>
        <param field="Mode1" label="Token" width="600px"/>
        <param field="Mode2" label="Liste mac adresse pour présence (séparé par ;)" width="600px"/>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
        </param>
    </params>
</plugin>
"""

import freebox
import json
import os
import datetime
import time
#import ssl
# from data import * # Only enable when debug mode
from enum import Enum
import Domoticz

SCHEME = 'https://'
HOST = 'mafreebox.freebox.fr'
PORT = '443'
JSON_FILE = 'devicemapping.json'


class FreeboxPlugin:
    """
    Domoticz plugin for Freebox. Freebox is an appliance provided by Free ISP (Iliad group)
    """
    class Device(Enum):
        """
        List of constants type for devices
        """
        DISK = 'Disk'
        CONNECTION_RATE = 'ConnectionRate'
        SYSTEM_INFO = 'SystemInfo'
        PRESENCE = 'Presence'
        COMMAND = 'Commande'
        ALARM = 'Alarme'

    enabled = False
    token = ""
    freebox_url = SCHEME + HOST + ":" + PORT
    _lastExecution = datetime.datetime.now()

    def __init__(self):
        return

    def get_all_devices_dict(self):
        """
        List all Domoticz devices created by the Freebox plugin

        Returns:
            (dict of str: str): {Type:{List},...}
        """
        dictionary = {}
        if os.path.isfile(Parameters["HomeFolder"] + JSON_FILE):
            with open(Parameters["HomeFolder"] + JSON_FILE, encoding='utf-8') as data_file:
                dictionary = json.load(data_file)
        return dictionary

    def save_all_devices_dict(self, dictionary):
        """
        Save the list of Domoticz devices (create by Freebox plugin) to file

        Args:
            dictionary (dict of str: str): List of all devices as dictionary
        """
        with open(Parameters["HomeFolder"] + JSON_FILE, 'w', encoding='utf-8') as data_file:
            json.dump(dictionary, data_file)

    def get_first_unused_unit_id(self, dictionary):
        """
        Position of first available ID of dictionary

        Args:
            dictionary (dict of str: str): List of all devices as dictionary

        Returns:
            int: Unused position
        """
        position = 0
        for device in dictionary:
            position = position + len(dictionary[device])
        return position + 1

    def return_unit_id(self, device, name):
        """
        Find device ID number from is type and name

        Args:
            device (str): device type as Device(Enum)
            name (str): device name

        Returns:
            str: unit id (integer as string)
        """
        dict_devices = self.get_all_devices_dict()
        dict_types = {}
        if device.value in dict_devices:
            dict_types = dict_devices[device.value]
        else:
            dict_devices.update({device.value: dict_types})
        if name in dict_types:
            return dict_types[name]
        else:
            position = self.get_first_unused_unit_id(dict_devices)
            dict_types.update({name: position})
            self.save_all_devices_dict(dict_devices)
            return position

    def unit_exist(self, device, name):
        """
        Find device ID number from is type and name

        Args:
            device (str): device type as Device(Enum)
            name (str): device name

        Returns:
            bool: True if device exist else False
        """
        dict_devices = self.get_all_devices_dict()
        if device.value in dict_devices:
            dict_types = dict_devices[device.value]
            if name in dict_types:
                return True
        return False

    def update_device(self, device, name, n_value, s_value, battery_level=None):
        """
        Update Domoticz value of a Freebox device

        Args:
            device (str): device type as Device(Enum)
            name (str): device name
            n_value (int): Domoticz numeric value
            s_value (str): Domoticz string value
            battery_level (int, optional): Domoticz battery level. Defaults to None.
        """
        if self.unit_exist(device, name):
            unit_id = self.return_unit_id(device, name)
            if unit_id in Devices:
                if ((device.value == self.Device.ALARM.value) and (
                        (Devices[unit_id].sValue != s_value) or (
                            Devices[unit_id].BatteryLevel != battery_level)
                )
                ):
                    Domoticz.Debug("Le dipositif de type0 " + device.value + " associé à " +
                                   name + " a été mis à jour " + str(n_value) + "/" + str(s_value) +
                                   "/"+str(Devices[unit_id].BatteryLevel) + "/" + str(battery_level))
                    Devices[unit_id].Update(
                        nValue=n_value, sValue=s_value, BatteryLevel=battery_level)
                    Domoticz.Debug("Le dipositif de type "+ device.value + " associé à " +
                                   name + " a été mis à jour " + str(n_value) + "/" + str(s_value))
                # Test if PRESENCE are already up-to-date
                elif device.value != self.Device.PRESENCE.value \
                        or (
                            device.value == self.Device.PRESENCE.value
                            and
                            Devices[unit_id].sValue != s_value
                            ):
                    Devices[unit_id].Update(nValue=n_value, sValue=s_value)
                    Domoticz.Debug("Le dipositif de type " + device.value + " associé à " +
                                   name + " a été mis à jour " + str(n_value) + "/" + str(s_value))
                else:
                    Domoticz.Debug("Le dipositif de type " + device.value +
                                   " associé à " + name + " est déjà à jour.")
            else:
                Domoticz.Debug("Le dipositif de type " + device.value +
                               " associé à " + name + " a été supprimé dans Domoticz.")
        else:
            Domoticz.Debug("Le dipositif de type " + device.value + " associé à " + name +
                           " n'a pas été créé dans Domoticz. Veuillez désactiver et réactiver le plugin, en autorisant l'ajout de nouveaux dispositifs.")

    def onStart(self):
        """
        Called when the hardware is started, either after Domoticz start, hardware creation or update.
        """
        Domoticz.Debug("onStart called")
        try:
            if Parameters["Address"] != "":
                self.freebox_url = Parameters["Address"]
                if Parameters["Port"] != "":
                    self.freebox_url = self.freebox_url + ":" + Parameters["Port"]
            # If Debug checked
            if Parameters["Mode6"] == "Debug":
                Domoticz.Debugging(1)
            DumpConfigToLog()
            if Parameters["Mode1"] == "":  # Parameters["Mode1"] == Token
                Domoticz.Log(
                    "C'est votre première connexion, le token n'est pas renseigné.")
                Domoticz.Log(
                    "Vous devez autoriser le plugin sur l'écran de la Freebox.")
                Domoticz.Log(
                    "Une fois autorisé sur la Freebox, le token s'affichera ici.")
                token = freebox.FbxCnx(self.freebox_url).register(
                    "idPluginDomoticz", "Plugin Freebox", "1", "Domoticz")
                if token:
                    Domoticz.Log(
                        "------------------------------------------------------------------------------")
                    Domoticz.Log(
                        "Veuillez copier ce token dans la configuration du plugin Reglages > Matériel")
                    Domoticz.Log(token)
                    Domoticz.Log(
                        "------------------------------------------------------------------------------")
                else:
                    Domoticz.Log(
                        "Vous avez été trop long (ou avez refusé), veuillez désactiver et réactiver le matériel Reglages > Matériel.")
            else:
                # Parameters["Mode1"] == Token
                self.token = Parameters["Mode1"]
                Domoticz.Log("Token déjà présent. OK.")

                f = freebox.FbxApp("idPluginDomoticz",
                                   self.token, host=self.freebox_url)

                # Creation of disk devices
                disks = f.ls_storage()
                for disk in disks:
                    unit_id = self.return_unit_id(
                        self.Device.DISK, disk)
                    if unit_id not in Devices:
                        device = Domoticz.Device(
                            Unit=unit_id, Name="Utilisation " + disk, TypeName="Percentage")
                        device.Create()
                        Domoticz.Log("Création du dispositif " +
                                     "Utilisation " + disk)
                        # Unfortunately the image in the Percentage device can not be changed. Use Custom device!
                        # Domoticz.Device(Unit=_UNIT_USAGE, Name=Parameters["Address"], TypeName="Custom", Options={"Custom": "1;%"}, Image=3, Used=1).Create()

                # Connection rates of WAN Freebox interface
                connection_rates = f.connection_rate()
                for rate in connection_rates:
                    unit_id = self.return_unit_id(
                        self.Device.CONNECTION_RATE, rate)
                    if unit_id not in Devices:
                        device = Domoticz.Device(
                            Unit=unit_id,
                            Name="Débit " + rate,
                            TypeName="Custom",
                            Options={"Custom": "1;Ko"},
                            Used=1
                        )
                        device.Create()
                        Domoticz.Log("Création du dispositif " +
                                     "Débit " + rate)

                # Create °C temp devices
                sysinfo = f.sysinfo()
                for info in sysinfo:
                    unit_id = self.return_unit_id(
                        self.Device.SYSTEM_INFO, info)
                    if unit_id not in Devices:
                        device = Domoticz.Device(
                            Unit=unit_id,
                            Name="System " + info,
                            TypeName="Temperature"
                        )
                        device.Create()
                        Domoticz.Log("Création du dispositif " +
                                     "System " + info)

                # Create alarms devices
                alarminfo = f.alarminfo()
                for alarm_device in alarminfo:
                    Domoticz.Debug("Label "+alarminfo[alarm_device]["label"])
                    keyunit = self.return_unit_id(
                        self.Device.ALARM, alarminfo[alarm_device]["label"])
                    if (keyunit not in Devices):
                        if (alarminfo[alarm_device]["type"]) == 'alarm_control':
                            v_dev = Domoticz.Device(
                                Unit=keyunit, Name=alarminfo[alarm_device]["label"], TypeName="Switch", Switchtype=0)
                            v_dev.Create()
                        elif (alarminfo[alarm_device]["type"]) == 'dws':
                            v_dev = Domoticz.Device(
                                Unit=keyunit, Name=alarminfo[alarm_device]["label"], TypeName="Switch", Switchtype=0)
                            v_dev.Create()
                            Domoticz.Log("Création du dispositif " +
                                         "Alarm "+alarminfo[alarm_device]["label"])
                        elif (alarminfo[alarm_device]["type"]) == 'pir':
                            v_dev = Domoticz.Device(
                                Unit=keyunit, Name=alarminfo[alarm_device]["label"], TypeName="Switch", Switchtype=8)
                            v_dev.Create()
                            Domoticz.Log("Création du dispositif " +
                                         "Alarm "+alarminfo[alarm_device]["label"])

                # Create presence sensor
                str_ls_macaddr = Parameters["Mode2"]
                if str_ls_macaddr != "":
                    ls_macaddr = str_ls_macaddr.split(";")
                    for macaddress in ls_macaddr:
                        name = f.get_name_from_macaddress(macaddress)
                        if name is not None:
                            unit_id = self.return_unit_id(
                                self.Device.PRESENCE, macaddress)
                            if unit_id not in Devices:
                                device = Domoticz.Device(
                                    Unit=unit_id, Name="Presence " + name, TypeName="Switch")
                                device.Create()
                                Domoticz.Log(
                                    "Création du dispositif " + "Presence " + name)
                        else:
                            Domoticz.Log(
                                "La mac adresse " + macaddress + " est inconnu de la freebox, on ne crée aucun dispositif.")

                # Create ON/OFF WIFI switch
                wifi_state = 1 if f.wifi_state() else 0
                Domoticz.Log("Etat WIFI : " + str(wifi_state))
                unit_id = self.return_unit_id(
                    self.Device.COMMAND, "WIFI")
                if unit_id not in Devices:
                    device = Domoticz.Device(
                        Unit=unit_id, Name="WIFI On/Off", TypeName="Switch")
                    device.Create()
                    Domoticz.Log("Création du dispositif " + "WIFI On/Off")
                self.update_device(
                    self.Device.COMMAND, "WIFI", wifi_state, str(wifi_state))

                # Create Reboot server switch
                unit_id = self.return_unit_id(
                    self.Device.COMMAND, "REBOOT")
                if unit_id not in Devices:
                    device = Domoticz.Device(
                        Unit=unit_id, Name="Reboot Server", TypeName="Switch")
                    device.Create()
                    Domoticz.Log("Création du dispositif " + "Reboot Server")

                # Create WAN status item
                constatus = 1 if f.connection_state() else 0
                Domoticz.Log("Etat connexion : " + str(constatus))
                unit_id = self.return_unit_id(
                    self.Device.COMMAND, "WANStatus")
                if unit_id not in Devices:
                    device = Domoticz.Device(
                        Unit=unit_id, Name="WAN Status", TypeName="Switch")
                    device.Create()
                    Domoticz.Log("Création du dispositif " + "WAN Status")
                self.update_device(
                    self.Device.COMMAND, "WANStatus", constatus, str(constatus))

                DumpConfigToLog()
        except Exception as e:
            Domoticz.Log("OnStart error: " + str(e))

    def onStop(self):
        """
        Called when the hardware is stopped or deleted from Domoticz. 
        """
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        """
        Called when connection to remote device either succeeds or fails,
        or when a connection is made to a listening Address:Port.
        Connection is the Domoticz Connection object associated with the event.
        Zero Status indicates success. If Status is not zero then the Description will describe
        the failure.
        This callback is not called for connectionless Transports such as UDP/IP.
        """
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data, Status, Extra):
        """
        Called when a single, complete message is received from the external hardware
        (as defined by the Protocol setting). This callback should be used to interpret
        messages from the device and set the related Domoticz devices as required.
        Connection is the Domoticz Connection object associated with the event.
        Data is normally a ByteArray except where the Protocol for the Connection has
        structure (such as HTTP or ICMP), in that case Data will be a Dictionary containing
        Protocol specific details such as Status and Headers. 
        """
        Domoticz.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        """
        Called by Domoticz in response to a script or Domoticz Web API call sending a command
        to a Unit in the Device's Units dictionary
        """
        Domoticz.Log("onCommand called for Unit " + str(Unit) +
                     ": Parameter '" + str(Command) + "', Level: " + str(Level))
        # 2018-04-02 20:26:01.192 User: Admin initiated a switch command (17/Freebox - Presence iPhonedMatthieu/On)
        # 2018-04-02 20:26:01.209 (Freebox) onCommand called for Unit 5: Parameter 'On', Level: 0
        # 2018-04-02 20:27:50.550 User: Admin initiated a switch command (17/Freebox - Presence iPhonedMatthieu/Off)
        # 2018-04-02 20:27:50.552 (Freebox) onCommand called for Unit 5: Parameter 'Off', Level: 0
        # 2018-04-02 20:28:44.350 User: Admin initiated a switch command (18/Freebox - Presence iPhonedTiphaine/On)
        # 2018-04-02 20:28:44.380 (Freebox) onCommand called for Unit 6: Parameter 'On', Level: 0
        unit_id = self.return_unit_id(
            self.Device.COMMAND, "WIFI")
        if unit_id == Unit:
            f = freebox.FbxApp("idPluginDomoticz",
                               self.token, host=self.freebox_url)
            if str(Command) == "On":
                f.wifi_enable(1)
            else:
                f.wifi_enable(0)
            time.sleep(1)
            # Update Wifi state
            wifi_state = 1 if f.wifi_state() else 0
            self.update_device(
                self.Device.COMMAND, "WIFI", wifi_state, str(wifi_state))

        unit_id = self.return_unit_id(
            self.Device.COMMAND, "REBOOT")
        if unit_id == Unit:
            f = freebox.FbxApp("idPluginDomoticz",
                               self.token, host=self.freebox_url)
            f.reboot()

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        """
        Called when any Domoticz device generates a notification.
        Name parameter is the device that generated the notification, the other parameters
        contain the notification details. Hardware that can handle notifications should
        be notified as required.
        """
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text +
                     "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        """
        Called after the remote device is disconnected.
        Connection is the Domoticz Connection object associated with the event.
        This callback is not called for connectionless Transports such as UDP/IP. 
        """
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        """
        Called every 'heartbeat' seconds (default 10) regardless of connection status.
        Heartbeat interval can be modified by the Heartbeat command.
        Allows the Plugin to do periodic tasks including request reconnection if the connection
        has failed.
        """
        Domoticz.Debug("onHeartbeat called")
        try:
            if self._lastExecution.minute == datetime.datetime.now().minute:
                return
            self._lastExecution = datetime.datetime.now()
            if self.token == "":
                Domoticz.Log("Pas de token défini.")
                return
            f = freebox.FbxApp("idPluginDomoticz",
                               self.token,
                               host=self.freebox_url
                               )

           # Alarm on Frebox Delta
            alarminfo = f.alarminfo()
            for alarm_device in alarminfo:
                self.updateDeviceIfExist(self.Device.ALARM,
                                         alarminfo[alarm_device]["label"],
                                         int(alarminfo[alarm_device]["value"]),
                                         str(alarminfo[alarm_device]["value"]),
                                         int(alarminfo[alarm_device]
                                             ["battery"])
                                         )

            if self._lastExecution.minute == datetime.datetime.now().minute:
                return
            self._lastExecution = datetime.datetime.now()

            usageDisk = f.ls_storage()
            for disk in usageDisk:
                self.update_device(self.Device.DISK, disk, int(
                    float(usageDisk[disk])), str(usageDisk[disk]))

            connections = f.connection_rate()
            for connection in connections:
                self.update_device(
                    self.Device.CONNECTION_RATE,
                    connection,
                    int(float(connections[connection])),
                    str(connections[connection])
                )

            sysinfo = f.sysinfo()
            for info in sysinfo:
                self.update_device(
                    self.Device.SYSTEM_INFO,
                    info,
                    int(float(sysinfo[info])),
                    str(sysinfo[info])
                )

            str_ls_macaddr = Parameters["Mode2"]
            ls_macaddr = str_ls_macaddr.split(";")
            for macaddress in ls_macaddr:
                name = f.get_name_from_macaddress(macaddress)
                presence = 0
                if name != None:
                    if f.reachable_macaddress(macaddress):
                        presence = 1
                self.update_device(
                    self.Device.PRESENCE,
                    macaddress,
                    presence,
                    str(presence)
                )

            online_devices = f.online_devices()
            for device in online_devices:
                Domoticz.Debug(
                    online_devices[device] + " (" + device + ") présent")

            wifi_state = 1 if f.wifi_state() else 0
            self.update_device(
                self.Device.COMMAND,
                "WIFI",
                wifi_state,
                str(wifi_state)
            )

            connection_state = 1 if f.connection_state() else 0
            self.update_device(
                self.Device.COMMAND,
                "WANStatus",
                connection_state,
                str(connection_state)
            )

        except Exception as e:
            Domoticz.Log("onHeartbeat error: " + str(e))


global _plugin
_plugin = FreeboxPlugin()


def onStart():
    global _plugin
    # on fait une pause de 10 secondes au démarrage pour attendre la Freebox si besoin
    # correction apporté par Gells qui avait des erreur au démarrage
    # https://easydomoticz.com/forum/viewtopic.php?f=10&t=6222&p=55468#p55442
    time.sleep(5)
    _plugin.onStart()


def onStop():
    """
    Called when the hardware is stopped or deleted from Domoticz.
    """
    global _plugin
    _plugin.onStop()


def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)


def onMessage(Connection, Data, Status, Extra):
    global _plugin
    _plugin.onMessage(Connection, Data, Status, Extra)


def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)


def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status,
                           Priority, Sound, ImageFile)


def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions


def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
        Domoticz.Debug("Options:         '" + str(Devices[x].Options) + "'")
    return
