#Code adapté de http://www.manatlan.com/blog/freeboxv6_api_v3_avec_python

import urllib.request,hmac,json,hashlib,time,Domoticz
from urllib.request import urlopen,Request
from socket import timeout

class FbxCnx:
    def __init__(self,host="mafreebox.freebox.fr"):
        self.host=host

    def register(self,appid,appname,version,devname):
        data={'app_id': appid,'app_name': appname,'app_version':version,'device_name': devname}
        result=self._com("login/authorize/",data)
        if not result["success"]:
            return "Erreur Reponse Freebox : " + result["msg"]
        r=result["result"]
        trackid,token=r["track_id"],r["app_token"]
        s="pending"
        nbWait = 0
        while s=="pending":
            s=self._com("login/authorize/%s"%trackid)
            s = s["result"]["status"]
            time.sleep(1)
            nbWait = nbWait + 1
            if nbWait > 30:
                s = "TropLong"
        return s=="granted" and token

    def _com(self,method,data=None,headers=None):
        url = self.host+"/api/v4/"+method
        if data: 
            data = json.dumps(data) #On transforme en string le dict
            data = data.encode() #On transforme en tableau de byte le string pour Request
            request = Request(url, data=data)
            request.get_method = lambda:"POST"
        else:
            if headers:
                request = Request(url,headers=headers)
            else:
                request = Request(url)
        res = urlopen(request,timeout=4).read()
        return json.loads(res.decode())

    def _put(self,method,data=None,headers=None):
        url = self.host+"/api/v4/"+method
        if data: 
            data = json.dumps(data) #On transforme en string le dict
            data = data.encode() #On transforme en tableau de byte le string pour Request
            if headers:
                request = Request(url,data=data,headers=headers)
            else:
                request = Request(url, data=data)
            request.get_method = lambda:"PUT"
        else:
            if headers:
                request = Request(url,headers=headers)
            else:
                request = Request(url)
        res = urlopen(request,timeout=4).read()
        return json.loads(res.decode())

    def _get(self,method,data=None,headers=None):
        url = self.host+"/api/v4/"+method
        if headers:
            request = Request(url,headers=headers)
        else:
            request = Request(url)
        request.get_method = lambda:"GET"
        res = urlopen(request,timeout=4).read()
        return json.loads(res.decode())

    def _mksession(self):
        challenge=self._com("login/")["result"]["challenge"]
        data={
          "app_id": self.appid,
          "password": hmac.new(self.token.encode(),challenge.encode(),hashlib.sha1).hexdigest()
        }
        return self._com("login/session/",data)["result"]["session_token"]
    
    def _disconnect(self, method, headers=None):
        url = self.host+"/api/v4/"+method
        request = Request(url,headers=headers)
        request.get_method = lambda:"POST"
        res = urlopen(request,timeout=4).read()
        return json.loads(res.decode())
    
class FbxApp(FbxCnx):
    def __init__(self,appid,token,session=None,host="mafreebox.free.fr"):
        FbxCnx.__init__(self,host)
        self.appid,self.token=appid,token
        self.session=session if session else self._mksession()

    def __del__(self):
        try:
            self.disconnect( "login/logout")
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('La Freebox semble indisponible : '+ error.msg)
        except timeout:
            Domoticz.Error('Timeout') #on ne fait rien

    def disconnect(self, method):
        return self._disconnect( method,{"X-Fbx-App-Auth": self.session})        
    
    def com(self,method,data=None):
        return self._com(method,data,{"X-Fbx-App-Auth": self.session})

    def put(self,method,data=None):
        return self._put(method,data,{"X-Fbx-App-Auth": self.session})

    def get(self,method,data=None):
        return self._get(method,data,{"X-Fbx-App-Auth": self.session})

    def diskinfoRaw(self):
        listDiskRaw = self.com( "storage/disk/")
        if (listDiskRaw is not None):
            return json.dumps(listDiskRaw)
        else:
            return "null"

    def diskinfo(self):
        retour = {}
        try:
            listDisk = self.com( "storage/disk/")
            if ("result" in listDisk): #Pour la box mini 4K qui n'a pas de disk
                for disk in listDisk["result"]:
                    if ("partitions" in disk): #Pour la box mini 4K qui n'a pas de disk
                        for partition in disk["partitions"]:
                            label = partition["label"]
                            used =partition["used_bytes"]
                            total=partition["total_bytes"]
                            Domoticz.Debug('Disk '+label+' '+str(used)+'/'+str(total))
                            percent = 0
                            if (total is not None):
                                if (total > 0):
                                    percent = used/total*100
                                    # print(str(label)+"=>"+str(round(percent,2))+"%")
                                    retour.update({str(label):str(round(percent,2))})   
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('La Freebox semble indisponible : '+ error.msg)
            return retour
        except timeout:
            Domoticz.Error('Timeout') #on ne fait rien, on retourne une liste vide
            return retour
        return retour
 
    def alarminfo(self):
            retour = {}
            try:
                listNodes= self.com( "home/tileset/all")  #listNodes 
                if ("result" in listNodes): #
                    for node in listNodes["result"]:
                        device = {}
                        label=''
                        if node["type"]=="alarm_control" :
                            device.update({"type":str(node["type"])})  
                            for data in node["data"]:
                                if  (data["ep_id"]== 11)  and  node["type"]=="alarm_control" :
                                        label = data["label"]
                                        if data['value']=='alarm1_armed' :
                                                value=1
                                                device.update({"alarm1_status":str(value)}) 
                                        elif data['value']=='alarm1_arming' :
                                                value=-1
                                                device.update({"alarm1_status":str(value)})  
                                        else:
                                                value=0
                                                device.update({"alarm1_status":str(value)})  
                                        if data['value']=='alarm2_armed':
                                                value=1
                                                device.update({"alarm2_status":str(value)}) 
                                        elif data['value']=='alarm2_arming' :
                                                value=-1
                                                device.update({"alarm2_status":str(value)})  
                                        else:
                                                value=0
                                                device.update({"alarm2_status":str(value)})  
                                        device.update({"label":str(label)}) 
                                elif  (data["ep_id"]== 13)  and  node["type"]=="alarm_control" :       #error
                                        status_error= data ["value"]
                                        device.update({"status_error":str(status_error)}) 
                                elif  (data["name"]== 'battery_warning') :
                                        battery= data ["value"]
                                        device.update({"battery":str(battery)}) 
                                device1=device.copy()    
                                device2=device.copy()    
                                if 'alarm1_status' in device1: 
                                    device1['value']=device1['alarm1_status']
                                    device1['label']=device1['label']+'1'
                                if 'alarm2_status' in device2:  
                                    device2['value']=device2['alarm2_status']
                                    device2['label']=device2['label']+'2'
                                retour.update({device1['label']:device1}) 
                                retour.update({device2['label']:device2}) 

                listNodes= self.com( "home/nodes")
                if ("result" in listNodes): #
                    for node in listNodes["result"]:
                        device = {}
                        label=''
                        if  ( (node["category"] == "pir")  or (node["category"] == "dws")  ) : 
                            label = node["label"]
                            device.update({"label":str(label)}) 
                            device.update({"type":str(node["category"] )})
                            for ep in node["show_endpoints"]:
                                if (  ep["name"] == 'battery'):
                                    battery= ep ["value"]
                                    device.update({"battery":str(battery)}) 
                                elif ( ep["name"] == 'trigger'):
                                            if (ep["value"]): 
                                                device.update({"value":0})
                                            elif (not ep["value"]): 
                                                device.update({"value":1})
                                retour.update({label:device}) 
            except (urllib.error.HTTPError, urllib.error.URLError) as error:
                #Domoticz.Error('La Freebox semble indisponible : '+ error.msg)
                return retour
            except timeout:
                #Domoticz.Error('Timeout') #on ne fait rien, on retourne une liste vide
                return retour
            return retour
 
    def getNameByMacAdresse(self,p_macAdresse):
        try:
            listePeriph = self.com( "lan/browser/pub/")
            for periph in listePeriph["result"]:
                macAdresse = periph["id"]
                if(("ETHER-"+p_macAdresse.upper()) == macAdresse.upper()):
                    return periph["primary_name"]
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('La Freebox semble indisponible : '+ error.msg)
        except timeout:
            return ""
    
    def isPresenceByMacAdresse(self,p_macAdresse):
        try:
            listePeriph = self.com( "lan/browser/pub/")
            for periph in listePeriph["result"]:
                macAdresse = periph["id"]
                if(("ETHER-"+p_macAdresse.upper()) == macAdresse.upper()):
                    reachable = periph["reachable"]
                    active = periph["active"]
                    if reachable and active:
                        return True
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('La Freebox semble indisponible : '+ error.msg)
        except timeout:
            Domoticz.Error('Timeout') #on ne fait rien, on retourne faux
        return False

    def lanPeripherique(self):
        retour = {}
        try:
            listePeriph = self.com( "lan/browser/pub/")
            for periph in listePeriph["result"]:
                name = periph["primary_name"]
                reachable = periph["reachable"]
                active = periph["active"]
                macAdresse = periph["id"]
                if reachable and active:
                    retour.update({macAdresse:name})
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('La Freebox semble indisponible : '+ error.msg)
        except timeout:
            Domoticz.Error('Timeout') #on ne fait rien, on retourne une liste vide
        return retour

    def sysinfo(self):
        retour = {}
        try:
            sys = self.com( "system/")
            retour.update({str('temp_cpub'):str(round(sys["result"]["temp_cpub"],2))})
            retour.update({str('temp_sw'):str(round(sys["result"]["temp_sw"],2))})
            retour.update({str('temp_cpum'):str(round(sys["result"]["temp_cpum"],2))})
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('La Freebox semble indisponible : '+ error.msg)
        except timeout:
            Domoticz.Error('Timeout') #on ne fait rien, on retourne une liste vide
        return retour

    def isOnWIFI(self):
        try:
            v_result = self.get("wifi/config/")
            if(v_result["result"]["enabled"]):
                return 1
            else:
                return 0
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('La Freebox semble indisponible : '+ error.msg)
        except timeout:
            return 0

    def setOnOFFWifi(self, p_isPutOn):
        isOn = None
        if p_isPutOn:
            # data = {'ap_params': {'enabled': True}}
            data = {'enabled': True}          
        else:
            # data = {'ap_params': {'enabled': False}}
            data = {'enabled': False}
        try:
            v_result = self.put( "wifi/config/",data)
            isOn = False
            if True == v_result['success']:
                if v_result['result']['enabled']: #v_result['result']['ap_params']['enabled']:
                    Domoticz.Debug( "Wifi is now ON")
                    isOn = True
                else:
                    Domoticz.Debug("Wifi is now OFF")
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('setOnOFFWifi Erreur '+ error.msg)
        except timeout:
            if not p_isPutOn:
                # If we are connected using wifi, disabling wifi will close connection
                # thus PUT response will never be received: a timeout is expected
                Domoticz.Error("Wifi désactivé")
                return False
            else:
                # Forward timeout exception as should not occur
                raise timeout
        # Response received
        # ensure status_code is 200, else raise exception
        # if requests.codes.ok != r.status_code:
        #     raise FbxOSException("Put error: %s" % r.text)
        # rc is 200 but did we really succeed?
        
        # else:
        #     raise FbxOSException("Challenge failure: %s" % resp)
        # self._logout()
        return isOn
    
    def reboot(self):
        #challenge=self.com("login/")["result"]["challenge"]
        #data={
        #  "app_id": self.appid,
        #  "password": hmac.new(self.token.encode(),challenge.encode(),hashlib.sha1).hexdigest()
        #}
        #v_result = self.com( "system/reboot/",data)
        v_result = self.com("system/reboot/")
        if not v_result['success']:
            Domoticz.Error("Erreur lors du Reboot")
        else:
            Domoticz.Debug("Freebox Server en cours de reboot.")
