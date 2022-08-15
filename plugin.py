# Freebox Python Plugin
#
# Author: supermat & ilionel : https://github.com/ilionel/PluginDomoticzFreebox/
# Credit: https://matdomotique.wordpress.com/2018/03/25/plugin-freebox-pour-domoticz/
#
"""
<plugin key="Freebox" name="Freebox (via API)" author="supermat &amp; ilionel" version="2.1.2" wikilink="https://www.domoticz.com/wiki/Plugins" externallink="https://matdomotique.wordpress.com/2018/03/25/plugin-freebox-pour-domoticz">
    <description>
        <br/>
        <h2>Initialisation</h2><br/>
        <h3>Au premier démarrage :</h3><br/>
        <pre>   1.  Laisser le champ "token" vide</pre>
        <pre>   2.  Accepter la demande directement depuis l'écran de la Freebox (vous aurez 30 secondes)</pre>
        <pre>   3a. Copier la clé "Token" affichée dans les logs de Domoticz ("Menu Configuration" &gt; "Log" )</pre>
        <pre>   3b. Coller la clé dans le champ "Token" de la configuration ci-dessous</pre>
        <pre>   4.  Enregistrer les modifications puis redémarrer le serveur Domoticz</pre>
        <pre>   5.  Ajouter les nouveaux dispositifs depuis le menu adéquat de Domoticz</pre><br/>
        <br/><b>Remarque : Les codes de télécommandes sont visibles depuis le Player TV : "Menu Système" &gt; "Informations" &gt; "Player"</b><br/><br/>
    </description>
    <params>
        <param field="Address" label="Freebox URL (avec http[s]://)" width="600px" required="true" default="https://mafreebox.freebox.fr"/>
        <param field="Port" label="Port" width="50px" required="true" default="443"/>
        <param field="Mode1" label="Token" width="600px"/>
        <param field="Mode2" label="Liste d'adresses mac (séparateur ;)" width="600px"/>
        <param field="Mode3" label="Remote TV1" width="200px"/>
        <param field="Mode4" label="Remote TV2" width="200px"/>
        <param field="Mode5" label="Fréquence de rafraîchissement" width="200px">
            <options>
                <option label="10s" value="10"/>
                <option label="30s" value="30"/>
                <option label="60s (default)" value="60" default="true"/>
                <option label="90s" value="90"/>
                <option label="120s (2 minutes)" value="120"/>
                <option label="300s (5 minutes)" value="300"/>
                <option label="600s (10 minutes)" value="600"/>
            </options>
        </param>
        <param field="Mode6" label="Debug" width="200px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true"/>
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
import traceback
# from data import * # Only enable when debug mode
from enum import Enum
import Domoticz

SCHEME = 'https://'
HOST = 'mafreebox.freebox.fr'
PORT = '443'
JSON_FILE = 'devicemapping.json'

POWER_STATE = ("OFF", "ON")
LINK_STATE  = ("DOWN", "UP")
PRESENCE_STATE = ("en ligne", "hors ligne")
RATE_TYPE = {"rate_down": "download", "rate_up": "upload"}
SWITCH_CMD = {"Off": 0, "On": 1}

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
        SYSTEM_SENSOR = 'SystemTemp'
        PRESENCE = 'Presence'
        COMMAND = 'Commande'
        ALARM = 'Alarme'
        PLAYER = 'TVPlayer'

    enabled = False
    token = ""
    freebox_url = SCHEME + HOST + ":" + PORT
    remote_code_tv1 = ""
    remote_code_tv2 = ""
    
    _refresh_interval = 60
    _tick = 0

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
            uid = self.get_first_unused_unit_id(dict_devices)
            dict_types.update({name: uid})
            self.save_all_devices_dict(dict_devices)
            return uid

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
                    Domoticz.Debug("Le dipositif de type " + device.value + " associé à " +
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

    def init(self):
        """
        Initialize the connection with Freebox server.

        Returns:
            bool: True is success else False
        """
        url   = Parameters["Address"]
        port  = Parameters["Port"]
        token = Parameters["Mode1"] # Parameters["Mode1"] == Token field
        debug = Parameters["Mode6"] # Parameters["Mode6"] == Debug field [Debug|Normal]
        self.remote_code_tv1 = Parameters["Mode3"] # Parameters["Mode3"] == TV Player 1 remote code field
        self.remote_code_tv2 = Parameters["Mode4"] # Parameters["Mode4"] == TV Player 2 remote code field
        self._refresh_interval = int(float(Parameters["Mode5"])) # Parameters["Mode5"] == Refresh interval field

        if url != "":
            if port != "":
                url = url + ":" + port
            self.freebox_url = url
        else:
            self.freebox_url = SCHEME + HOST + ":" + PORT

        # If Debug checked
        if debug == "Debug":
            Domoticz.Debugging(1)
        DumpConfigToLog()

        # If Token field is empty
        if token == "":
            Domoticz.Log(
                "C'est votre première connexion, le token n'est pas renseigné.")
            Domoticz.Log(
                "Vous devez autoriser le plugin sur l'écran de la Freebox.")
            Domoticz.Log(
                "Une fois autorisé sur la Freebox, le token s'affichera ici.")
            token = freebox.FbxCnx(self.freebox_url).register(
                "idPluginDomoticz", "Plugin Freebox", "1", "Domoticz")
            # We got a Token thanks to freebox.FbxCnx
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
            self.token = token
            Domoticz.Log("Token déjà présent. OK.")
        return True if self.token else False

    def _create_devices_reboot(self):
        # Create Reboot server switch
        unit_id = self.return_unit_id(
            self.Device.COMMAND, "REBOOT")
        if unit_id not in Devices:
            device = Domoticz.Device(
                Unit=unit_id,
                Name="Reboot Server",
                TypeName="Switch"
                )
            device.Create()
            Domoticz.Log(f"Nouveau dispositif: '{self.Device.COMMAND.value}' -> 'REBOOT'")

    def _create_devices_storages(self, f):
        # Creation of disk devices
        disks = f.ls_storage()
        for disk, value in disks.items():
            unit_id = self.return_unit_id(self.Device.DISK, disk)
            if unit_id not in Devices:
                device = Domoticz.Device(
                    Unit=unit_id,
                    Name="Occupation " + disk,
                    TypeName="Percentage")
                device.Create()
                Domoticz.Log(f"Nouveau dispositif: '{self.Device.DISK.value}' -> '{disk}'")
                # Unfortunately the image in the Percentage device can not be changed. Use Custom device!
                # Domoticz.Device(Unit=_UNIT_USAGE, Name=Parameters["Address"], TypeName="Custom", Options={"Custom": "1;%"}, Image=3, Used=1).Create()
            Domoticz.Log(f"L'espace disque de '{disk}' est occupé à {value}%")
            self.update_device(self.Device.DISK, disk, int(float(value)), str(value))

    def _create_devices_rates(self, f):
        # Connection rates of WAN Freebox interface
        connection_rates = f.connection_rate()
        for rate, value in connection_rates.items():
            unit_id = self.return_unit_id(self.Device.CONNECTION_RATE, rate)
            if unit_id not in Devices:
                device = Domoticz.Device(
                    Unit=unit_id,
                    Name="Débit " + RATE_TYPE[rate],
                    TypeName="Custom",
                    Options={"Custom": "1;ko/s"},
                    Used=1
                )
                device.Create()
                Domoticz.Log(
                    f"Nouveau dispositif: '{self.Device.CONNECTION_RATE.value}' -> '{RATE_TYPE[rate]}'"
                    )
            Domoticz.Log(f"Le débit WAN en '{RATE_TYPE[rate]}' est de {value} ko/s")
            self.update_device(self.Device.CONNECTION_RATE, rate, int(float(value)), str(value))

    def _create_devices_sensors(self, f):
        # Create °C temp devices
        sensors = f.system.sensors()
        for sensor in sensors:
            uid = str(sensor['id'])
            name = sensor['name']
            value = int(sensor['value'])
            unit_id = self.return_unit_id(self.Device.SYSTEM_SENSOR, uid)
            if unit_id not in Devices:
                device = Domoticz.Device(
                    Unit=unit_id,
                    Name=name,
                    TypeName="Temperature"
                    )
                device.Create()
                Domoticz.Log(f"Nouveau dispositif: '{self.Device.SYSTEM_SENSOR.value}' -> '{name}'")
            Domoticz.Log(f"La sonde '{name}' affiche {value}°C")
            self.update_device(self.Device.SYSTEM_SENSOR, uid, value, str(value))

    def _create_devices_alarm(self, f):
        # Create alarms devices
        alarminfo = f.alarminfo()
        for alarm_device in alarminfo:
            Domoticz.Debug("Label " + alarminfo[alarm_device]['label'])
            keyunit = self.return_unit_id(
                self.Device.ALARM, alarminfo[alarm_device]['label'])
            if (keyunit not in Devices):
                if (alarminfo[alarm_device]['type']) == 'alarm_control':
                    device = Domoticz.Device(
                        Unit=keyunit, Name=alarminfo[alarm_device]['label'], TypeName="Switch", Switchtype=0)
                    device.Create()
                    Domoticz.Log(f"Nouveau dispositif: '{self.Device.ALARM.value}' -> '{alarminfo[alarm_device]['label']}'")
                elif (alarminfo[alarm_device]['type']) == 'dws':
                    device = Domoticz.Device(
                        Unit=keyunit, Name=alarminfo[alarm_device]['label'], TypeName="Switch", Switchtype=0)
                    device.Create()
                    Domoticz.Log(f"Nouveau dispositif: '{self.Device.ALARM.value}' -> '{alarminfo[alarm_device]['label']}'")
                elif (alarminfo[alarm_device]["type"]) == 'pir':
                    device = Domoticz.Device(
                        Unit=keyunit, Name=alarminfo[alarm_device]["label"], TypeName="Switch", Switchtype=8)
                    device.Create()
                    Domoticz.Log(f"Nouveau dispositif: '{self.Device.ALARM.value}' -> '{alarminfo[alarm_device]['label']}'")

    def _create_devices_presence(self, f):
        # Create presence sensor
        str_ls_macaddr = Parameters["Mode2"]
        if str_ls_macaddr != "":
            ls_macaddr = str_ls_macaddr.split(";")
            for macaddress in ls_macaddr:
                name = f.get_name_from_macaddress(macaddress)
                if name is None:
                    Domoticz.Log(
                        f"L'adresse mac: '{macaddress}' est inconnue de la Freebox et sera ignorée"
                        )
                else:
                    unit_id = self.return_unit_id(self.Device.PRESENCE, macaddress)
                    if unit_id not in Devices:
                        device = Domoticz.Device(
                            Unit=unit_id,
                            Name="Presence " + name,
                            TypeName="Switch")
                        device.Create()
                        Domoticz.Log(
                            f"Nouveau dispositif: '{self.Device.PRESENCE.value}' -> '{name}'"
                            )
                    presence = 1 if f.reachable_macaddress(macaddress) else 0
                    Domoticz.Log(
                        f"L'équipement '{name}' est actuellement {PRESENCE_STATE[presence]}"
                        )
                    self.update_device(self.Device.PRESENCE, macaddress, presence, str(presence))

    def _create_devices_wifi(self, f):
        # Create ON/OFF WIFI switch
        wifi_state = 1 if f.wifi_state() else 0
        unit_id = self.return_unit_id(
            self.Device.COMMAND, "WIFI")
        if unit_id not in Devices:
            device = Domoticz.Device(
                Unit=unit_id,
                Name="WIFI On/Off",
                TypeName="Switch"
                )
            device.Create()
            Domoticz.Log(f"Nouveau dispositif: '{self.Device.COMMAND.value}' -> 'WIFI'")
        Domoticz.Log("Le WIFI est " + LINK_STATE[wifi_state])
        self.update_device(self.Device.COMMAND, "WIFI", wifi_state, str(wifi_state))

    def _create_devices_wan(self, f):
        # Create WAN status item
        wan_state = 1 if f.wan_state() else 0
        unit_id = self.return_unit_id(
            self.Device.COMMAND, "WANStatus")
        if unit_id not in Devices:
            device = Domoticz.Device(
                Unit=unit_id,
                Name="WAN Status",
                TypeName="Switch"
                )
            device.Create()
            Domoticz.Log(f"Nouveau dispositif: '{self.Device.COMMAND.value}' -> 'WANStatus'")
        Domoticz.Log("La connexion Internet est " + LINK_STATE[wan_state])
        self.update_device(self.Device.COMMAND, "WANStatus", wan_state, str(wan_state))

    def _create_devices_players(self, f):
        # Create FreeboxPlayer
        players = f.players.info
        for player in players:
            uid = str(player['id'])
            player_state = 1 if f.players.state(uid) else 0
            name = player['device_name'] + ' ' + uid
            unit_name = player['device_model'] + '_' + uid
            unit_id = self.return_unit_id(
                        self.Device.PLAYER, unit_name)
            if unit_id not in Devices:
                device = Domoticz.Device(
                    Unit=unit_id,
                    Name=name,
                    TypeName="Switch"
                    )
                device.Create()
                Domoticz.Log(f"Nouveau dispositif: '{self.Device.PLAYER.value}' -> '{name}'")
            Domoticz.Log(f"Le player TV{uid} est " + POWER_STATE[player_state])
            self.update_device(self.Device.PLAYER, unit_name, player_state, str(player_state))

    def _refresh_devices_storages(self, f):
        # Update Disk metics
        disks = f.ls_storage()
        for disk, value in disks.items():
            Domoticz.Debug(f"L'espace disque de '{disk}' est occupé à {value}%")
            self.update_device(self.Device.DISK, disk, int(float(value)), str(value))

    def _refresh_devices_rates(self, f):
        # Update WAN UP/DL Rates
        connection_rates = f.connection_rate()
        for rate, value in connection_rates.items():
            Domoticz.Debug(f"Le débit WAN en '{RATE_TYPE[rate]}' est de {value} ko/s")
            self.update_device(self.Device.CONNECTION_RATE, rate, int(float(value)), str(value))

    def _refresh_devices_sensors(self, f):
        # Update °C temp devices
        sensors = f.system.sensors()
        for sensor in sensors:
            uid = str(sensor['id'])
            value = int(sensor['value'])
            Domoticz.Debug(f"La sonde '{sensor['name']}' affiche {value}°C")
            self.update_device(self.Device.SYSTEM_SENSOR, uid, value, str(value))

    def _refresh_devices_alarm(self, f):
        # Update Alarm informations (Only in option with the Frebox Delta)
        alarminfo = f.alarminfo()
        for alarm_device in alarminfo:
            self.update_device(
                self.Device.ALARM,
                alarminfo[alarm_device]["label"],
                int(alarminfo[alarm_device]["value"]),
                str(alarminfo[alarm_device]["value"]),
                int(alarminfo[alarm_device]["battery"])
                )

    def _refresh_devices_presence(self, f):
        # Update "Presence" Domoticz values
        str_ls_macaddr = Parameters["Mode2"]
        ls_macaddr = str_ls_macaddr.split(";")
        for macaddress in ls_macaddr:
            name = f.get_name_from_macaddress(macaddress)
            if name is not None:
                presence = 1 if f.reachable_macaddress(macaddress) else 0
                Domoticz.Debug(
                        f"L'équipement '{name}' est actuellement {PRESENCE_STATE[presence]}"
                        )
                self.update_device(self.Device.PRESENCE, macaddress, presence, str(presence))

    def _refresh_devices_wifi(self, f):
        # Update "Wifi" Domoticz switch state
        wifi_state = 1 if f.wifi_state() else 0
        Domoticz.Debug("Le WIFI est " + LINK_STATE[wifi_state])
        self.update_device(self.Device.COMMAND, "WIFI", wifi_state, str(wifi_state))

    def _refresh_devices_wan(self, f):
        # Update "WAN interface" Domoticz switch state
        wan_state = 1 if f.wan_state() else 0
        Domoticz.Log("La connexion Internet est " + LINK_STATE[wan_state])
        self.update_device(self.Device.COMMAND, "WANStatus", wan_state, str(wan_state))

    def _refresh_devices_players(self, f):
        # Update "Players" Domoticz values
        players = f.players.info
        for player in players:
            uid = str(player['id'])
            player_state = 1 if f.players.state(uid) else 0
            unit_name = player['device_model'] + '_' + uid
            Domoticz.Debug(f"Le player TV{uid} est " + POWER_STATE[player_state])
            self.update_device(self.Device.PLAYER, unit_name, player_state, str(player_state))

    def _switch_reboot(self, f):
        f.reboot()

    def _switch_wifi(self, f, command):
        f.wifi_enable(SWITCH_CMD[command])
        time.sleep(1)
        # Update Wifi state
        self._refresh_devices_wifi(f)

    def _switch_player(self, f, command, player_id="1"):
        Domoticz.Log(f"Switch 'TV Player{player_id}'")
        if player_id=="1":
            remote_code = self.remote_code_tv1
        elif player_id=="2":
            remote_code = self.remote_code_tv2
        if remote_code is not None and command=="Off" :
            f.players.shutdown(player_id, remote_code)
            time.sleep(1)
            # Update Player state
            self._refresh_devices_players(f)

    def onStart(self):
        """
        Called when the hardware is started, either after Domoticz start, hardware creation or update.
        """
        Domoticz.Log("onStart called")
        try:
            self.init()
            f = freebox.FbxApp("idPluginDomoticz", self.token, self.freebox_url)
            self._create_devices_reboot()
            self._create_devices_storages(f)
            self._create_devices_rates(f)
            self._create_devices_sensors(f)
            self._create_devices_alarm(f)
            self._create_devices_presence(f)
            self._create_devices_wifi(f)
            self._create_devices_wan(f)
            self._create_devices_players(f)
            DumpConfigToLog()
        except Exception as e:
            Domoticz.Error(f"OnStart error: {e}")
            Domoticz.Error(traceback.format_exc())

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
        try:
            f = freebox.FbxApp("idPluginDomoticz", self.token, host=self.freebox_url)
            if Unit == self.return_unit_id(self.Device.COMMAND, "REBOOT"):
                self._switch_reboot(f)
            elif Unit == self.return_unit_id(self.Device.COMMAND, "WIFI"):
                self._switch_wifi(f, Command)
            elif Unit == 11: # FIXME
                self._switch_player(f, Command, str(Unit)[-1:])

        except Exception as e:
            Domoticz.Error(f"onHeartbeat error: {e}")
            Domoticz.Error(traceback.format_exc())

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

        self._tick = self._tick + 10 # Add 10s (i.e. the default heartbeat)
        self._tick = self._tick % self._refresh_interval
        if self._tick != 0:
            return # To skip beacause refresh interval doesn't reach

        if self.token == "":
            Domoticz.Log("Pas de token défini.")
            return

        try:
            f = freebox.FbxApp("idPluginDomoticz", self.token, host=self.freebox_url)
            self._refresh_devices_storages(f)
            self._refresh_devices_rates(f)
            self._refresh_devices_sensors(f)
            self._refresh_devices_alarm(f)
            self._refresh_devices_presence(f)
            self._refresh_devices_wifi(f)
            self._refresh_devices_wan(f)
            self._refresh_devices_players(f)
        except Exception as e:
            Domoticz.Error(f"onHeartbeat error: {e}")
            Domoticz.Error(traceback.format_exc())

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
