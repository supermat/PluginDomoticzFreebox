# Freebox Python Plugin
#
# Author: https://matdomotique.wordpress.com/
# https://matdomotique.wordpress.com/2018/03/25/plugin-freebox-pour-domoticz/
#
"""
<plugin key="Freebox" name="Freebox Python Plugin" author="nachonam <-> supermat" version="1.2.0" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://matdomotique.wordpress.com/2018/03/25/plugin-freebox-pour-domoticz">
    <params>
        <param field="Address" label="URL de la Box avec http devant" width="400px" required="true" default="http://mafreebox.free.fr"/>
        <param field="Port" label="Port" width="100px" required="true" default="80"/>
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
import Domoticz,freebox,json,os,datetime,time
# from data import * #Pour le debug local sinon à mettre en commentaire
from enum import Enum

class FreeboxPlugin:
    class DeviceType(Enum):
        deviceTypeDisk = 'DiskDevice'
        deviceSystemInfo = 'SystemInfoDevice'
        devicePresence = 'PresenceDevice'
        deviceCommande = 'Commande'
        deviceAlarm='AlarmDevice'
    _fileNameDeviceMapping = 'devicemapping.json'
    enabled = False
    token = ""
    freeboxURL = "http://mafreebox.free.fr"
    _UNIT_DISK = {}
    _lastExecution = datetime.datetime.now()
    def __init__(self):
        #self.var = 123
        return

    def getDicoUnitAllDevice(self):
        v_UnitKeyDico = {}
        if (os.path.isfile(Parameters["HomeFolder"]+self._fileNameDeviceMapping)):
                with open(Parameters["HomeFolder"]+self._fileNameDeviceMapping) as data_file:
                    v_UnitKeyDico = json.load(data_file)
        return v_UnitKeyDico

    def saveDicoUnitDevice(self, p_dicoToSave):
        with open(Parameters["HomeFolder"]+self._fileNameDeviceMapping, 'w', encoding='utf-8') as data_file:
                json.dump(p_dicoToSave, data_file)

    def getNextUnsuedUnit(self,p_dicoAll):
        v_count = 0
        for deviceType in p_dicoAll:
            v_count = v_count + len(p_dicoAll[deviceType])
        return v_count+1

    def getOrCreateUnitIdForDevice(self, p_deviceType, p_deviceFreeboxName):
        # v_UnitKeyDico = self.getDicoUnitForDeviceType(p_deviceType)
        v_dicoAll = self.getDicoUnitAllDevice()
        if(p_deviceType.value in v_dicoAll):
            v_dicoDeviceType = v_dicoAll[p_deviceType.value]
        else:
            v_dicoDeviceType = {}
            v_dicoAll.update({p_deviceType.value:v_dicoDeviceType})
        if(p_deviceFreeboxName in v_dicoDeviceType):
            return v_dicoDeviceType[p_deviceFreeboxName]
        else:
            v_unit = self.getNextUnsuedUnit(v_dicoAll)
            v_dicoDeviceType.update({p_deviceFreeboxName:v_unit})
            self.saveDicoUnitDevice(v_dicoAll)
            return v_unit
    
    def isUnitExist(self, p_deviceType, p_deviceFreeboxName):
        v_dicoAll = self.getDicoUnitAllDevice()
        if(p_deviceType.value in v_dicoAll):
            v_dicoDeviceType = v_dicoAll[p_deviceType.value]
        else:
            return False
        if(p_deviceFreeboxName in v_dicoDeviceType):
            return True
        else:
            return False

    def updateDeviceIfExist(self,  p_deviceType, p_deviceFreeboxName, p_nValue, p_sValue,p_nBatteryLevel=None):
        if self.isUnitExist(p_deviceType,p_deviceFreeboxName):
            v_unitKey = self.getOrCreateUnitIdForDevice(p_deviceType,p_deviceFreeboxName)
            if v_unitKey in Devices:
                if ( (p_deviceType.value == self.DeviceType.deviceAlarm.value)   and ( (Devices[v_unitKey].sValue != p_sValue) or  (Devices[v_unitKey].BatteryLevel != p_nBatteryLevel) )  ):
                        Domoticz.Debug("Le dipositif de type0 "+p_deviceType.value +" associé à "+ p_deviceFreeboxName + " a été mis à jour " + str(p_nValue) + "/" + str(p_sValue)+"/"+str(Devices[v_unitKey].BatteryLevel ) +"/"+ str(p_nBatteryLevel))
                        Devices[v_unitKey].Update(nValue=p_nValue, sValue=p_sValue, BatteryLevel=p_nBatteryLevel)
                        Domoticz.Debug("Le dipositif de type "+p_deviceType.value +" associé à "+ p_deviceFreeboxName + " a été mis à jour " + str(p_nValue) + "/" + str(p_sValue))
                # On ne met pas à jour un device de type devicePresence s'il est déjà à jour
                elif ( (p_deviceType.value != self.DeviceType.devicePresence.value and p_deviceType.value != self.DeviceType.deviceAlarm.value)
                   or (p_deviceType.value == self.DeviceType.devicePresence.value
                        and Devices[v_unitKey].sValue != p_sValue)
                ):
                    Devices[v_unitKey].Update(nValue=p_nValue, sValue=p_sValue)
                    Domoticz.Debug("Le dipositif de type "+p_deviceType.value +" associé à "+ p_deviceFreeboxName + " a été mis à jour " + str(p_nValue) + "/" + str(p_sValue))
                else:
                    Domoticz.Debug("Le dipositif de type "+p_deviceType.value +" associé à "+ p_deviceFreeboxName + " est déjà à jour.")
            else:
                Domoticz.Debug("Le dipositif de type "+p_deviceType.value +" associé à "+ p_deviceFreeboxName + " a été supprimé dans Domoticz.")
        else:
            Domoticz.Debug("Le dipositif de type "+p_deviceType.value +" associé à "+ p_deviceFreeboxName + " n'a pas été créé dans Domoticz. Veuillez désactiver et réactiver le plugin, en autorisant l'ajout de nouveaux dispositifs.")

    def onStart(self):
        Domoticz.Debug("onStart called")
        try:
            self.freeboxURL = Parameters["Address"]+":"+Parameters["Port"]
            if Parameters["Mode6"] == "Debug":
                Domoticz.Debugging(1)
            DumpConfigToLog()
            if Parameters["Mode1"] == "": # Le Token
                Domoticz.Log("C'est votre première connexion, le token n'est pas renseigné.")
                Domoticz.Log("Vous avez 30 secondes pour autoriser le plugin sur l'écran de la Freebox.")
                Domoticz.Log("Une fois autorisé sur la Freebox, le token s'affichera ici.")
                Token = freebox.FbxCnx(self.freeboxURL).register("idPluginDomoticz","Plugin Freebox","1","Domoticz")
                if Token:
                    Domoticz.Log("------------------------------------------------------------------------------")
                    Domoticz.Log("Veuillez copier ce token dans la configuration du plugin Reglages > Matériel")
                    Domoticz.Log(Token)
                    Domoticz.Log("------------------------------------------------------------------------------")
                else:
                    Domoticz.Log("Vous avez été trop long (ou avez refusé), veuillez désactiver et réactiver le matériel Reglages > Matériel.")
            else:
                self.token = Parameters["Mode1"]
                Domoticz.Log("Token déjà présent. OK.")

                f=freebox.FbxApp("idPluginDomoticz",self.token,host=self.freeboxURL)

                #Pour trouver le pb avec la FreeBox Delta, on affiche le json
                #if Parameters["Mode6"] == "Debug":
                #    jsonUsageDisk = f.diskinfoRaw()
                #    Domoticz.Debug(jsonUsageDisk)

                #Creation des device Disque Dur de la Freebox
                usageDisk = f.diskinfo()
                for disk in usageDisk:
                    keyunit = self.getOrCreateUnitIdForDevice(self.DeviceType.deviceTypeDisk,disk)
                    if (keyunit not in Devices):
                        v_dev = Domoticz.Device(Unit=keyunit, Name="Utilisation "+disk, TypeName="Percentage")
                        v_dev.Create()
                        Domoticz.Log("Création du dispositif "+"Utilisation "+disk)
                        # Unfortunately the image in the Percentage device can not be changed. Use Custom device!
                        # Domoticz.Device(Unit=_UNIT_USAGE, Name=Parameters["Address"], TypeName="Custom", Options={"Custom": "1;%"}, Image=3, Used=1).Create()
                
                #Creation des device infos systeme de la Freebox
                sysinfo = f.sysinfo()
                for info in sysinfo:
                    keyunit = self.getOrCreateUnitIdForDevice(self.DeviceType.deviceSystemInfo,info)
                    if (keyunit not in Devices):
                        v_dev = Domoticz.Device(Unit=keyunit, Name="System "+info, TypeName="Temperature")
                        v_dev.Create()
                        Domoticz.Log("Création du dispositif "+"System "+info)
                        
                #Creation des devices  l'alarme Freebox
                alarminfo = f.alarminfo()
                for alarm_device in alarminfo:
                        Domoticz.Debug("Label "+alarminfo[alarm_device]["label"])
                        keyunit = self.getOrCreateUnitIdForDevice(self.DeviceType.deviceAlarm,alarminfo[alarm_device]["label"])
                        if (keyunit not in Devices):
                            if (alarminfo[alarm_device]["type"]) == 'alarm_control':
                                v_dev = Domoticz.Device(Unit=keyunit, Name=alarminfo[alarm_device]["label"], TypeName="Switch", Switchtype=0)
                                v_dev.Create()
                            elif  (alarminfo[alarm_device]["type"]) == 'dws':
                                v_dev = Domoticz.Device(Unit=keyunit, Name=alarminfo[alarm_device]["label"], TypeName="Switch", Switchtype=0)
                                v_dev.Create()
                                Domoticz.Log("Création du dispositif "+"Alarm "+alarminfo[alarm_device]["label"])
                            elif (alarminfo[alarm_device]["type"]) == 'pir':
                                v_dev = Domoticz.Device(Unit=keyunit, Name=alarminfo[alarm_device]["label"], TypeName="Switch", Switchtype=8)
                                v_dev.Create()
                                Domoticz.Log("Création du dispositif "+"Alarm "+alarminfo[alarm_device]["label"])
                                
                #Creation des device presence de la Freebox
                listeMacString = Parameters["Mode2"]
                if(listeMacString != ""):
                    listeMac = listeMacString.split(";")
                    for macAdresse in listeMac:
                        name = f.getNameByMacAdresse(macAdresse)
                        if (name != None):
                            keyunit = self.getOrCreateUnitIdForDevice(self.DeviceType.devicePresence,macAdresse)
                            if (keyunit not in Devices):
                                v_dev = Domoticz.Device(Unit=keyunit, Name="Presence "+name, TypeName="Switch")
                                v_dev.Create()
                                Domoticz.Log("Création du dispositif "+"Presence "+name)
                        else:
                            Domoticz.Log("La mac adresse "+macAdresse+" est inconnu de la freebox, on ne crée aucun dispositif.")
                
                #Creation du device d'activation/désactivation du WIFI
                v_etatWIFI = f.isOnWIFI()
                Domoticz.Log("Etat WIFI : "+ str(v_etatWIFI))
                keyunit = self.getOrCreateUnitIdForDevice(self.DeviceType.deviceCommande,"WIFI")
                if (keyunit not in Devices):
                    v_dev = Domoticz.Device(Unit=keyunit, Name="WIFI On/Off", TypeName="Switch")
                    v_dev.Create()
                    Domoticz.Log("Création du dispositif "+"WIFI On/Off")
                self.updateDeviceIfExist(self.DeviceType.deviceCommande,"WIFI",v_etatWIFI, str(v_etatWIFI))
                #Creation du device de reboot du Freebox server
                #f.reboot()
                keyunit = self.getOrCreateUnitIdForDevice(self.DeviceType.deviceCommande,"REBOOT")
                if (keyunit not in Devices):
                    v_dev = Domoticz.Device(Unit=keyunit, Name="Reboot Server", TypeName="Switch")
                    v_dev.Create()
                    Domoticz.Log("Création du dispositif "+"Reboot Server")
                
                Domoticz.Heartbeat(1)
                DumpConfigToLog()
        except Exception as e:
            Domoticz.Log("OnStart error: "+str(e))

    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data, Status, Extra):
        Domoticz.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        # 2018-04-02 20:26:01.192 User: Admin initiated a switch command (17/Freebox - Presence iPhonedMatthieu/On)
        # 2018-04-02 20:26:01.209 (Freebox) onCommand called for Unit 5: Parameter 'On', Level: 0
        # 2018-04-02 20:27:50.550 User: Admin initiated a switch command (17/Freebox - Presence iPhonedMatthieu/Off)
        # 2018-04-02 20:27:50.552 (Freebox) onCommand called for Unit 5: Parameter 'Off', Level: 0
        # 2018-04-02 20:28:44.350 User: Admin initiated a switch command (18/Freebox - Presence iPhonedTiphaine/On)
        # 2018-04-02 20:28:44.380 (Freebox) onCommand called for Unit 6: Parameter 'On', Level: 0
        keyunit = self.getOrCreateUnitIdForDevice(self.DeviceType.deviceCommande,"WIFI")
        if (keyunit == Unit):
            f=freebox.FbxApp("idPluginDomoticz",self.token,host=self.freeboxURL)
            if(str(Command) == "On"):
                f.setOnOFFWifi(1)
            else:                
                f.setOnOFFWifi(0)
            time.sleep(1)
            #On remet à jour l'état du wifi suite à la modification
            v_etatWIFI = f.isOnWIFI()
            self.updateDeviceIfExist(self.DeviceType.deviceCommande,"WIFI",v_etatWIFI, str(v_etatWIFI))

        keyunit = self.getOrCreateUnitIdForDevice(self.DeviceType.deviceCommande,"REBOOT")
        if (keyunit == Unit):
            f=freebox.FbxApp("idPluginDomoticz",self.token,host=self.freeboxURL)
            f.reboot()

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")
        try:
            if self.token == "" :
                Domoticz.Log("Pas de token défini.")
                return
            f=freebox.FbxApp("idPluginDomoticz",self.token,host=self.freeboxURL)
            #Alarme de la Freebox
            alarminfo = f.alarminfo()
            for alarm_device in alarminfo:
                    self.updateDeviceIfExist(self.DeviceType.deviceAlarm,  alarminfo[alarm_device]["label"],int(alarminfo[alarm_device]["value"]), str(alarminfo[alarm_device]["value"]),int(alarminfo[alarm_device]["battery"]))

            if self._lastExecution.minute == datetime.datetime.now().minute :
                return        
            self._lastExecution = datetime.datetime.now()
            
            usageDisk = f.diskinfo()
            for disk in usageDisk:
                self.updateDeviceIfExist(self.DeviceType.deviceTypeDisk,disk,int(float(usageDisk[disk])), str(usageDisk[disk]))
            
            sysinfo = f.sysinfo()
            for info in sysinfo:
                self.updateDeviceIfExist(self.DeviceType.deviceSystemInfo,info,int(float(sysinfo[info])), str(sysinfo[info]))
            
            listeMacString = Parameters["Mode2"]
            listeMac = listeMacString.split(";")
            for macAdresse in listeMac:
                name = f.getNameByMacAdresse(macAdresse)
                presence = 0
                if (name != None):
                    if(f.isPresenceByMacAdresse(macAdresse)):
                        presence = 1
                self.updateDeviceIfExist(self.DeviceType.devicePresence,macAdresse,presence, str(presence))
            
            lanPeriph = f.lanPeripherique()
            for periph in lanPeriph:            
                Domoticz.Debug(lanPeriph[periph]+" ("+periph+") présent")

            v_etatWIFI = f.isOnWIFI()
            self.updateDeviceIfExist(self.DeviceType.deviceCommande,"WIFI",v_etatWIFI, str(v_etatWIFI))
    
        except Exception as e:
            Domoticz.Log("onHeartbeat error: "+str(e))

global _plugin
_plugin = FreeboxPlugin()

def onStart():
    global _plugin
    # on fait une pause de 10 secondes au démarrage pour attendre la Freebox si besoin
    # correction apporté par Gells qui avait des erreur au démarrage
    #https://easydomoticz.com/forum/viewtopic.php?f=10&t=6222&p=55468#p55442
    time.sleep(1)
    _plugin.onStart()

def onStop():
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
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

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
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
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
