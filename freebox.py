#Code adapté de http://www.manatlan.com/blog/freeboxv6_api_v3_avec_python

import urllib.request,hmac,json,hashlib,time,Domoticz
from urllib.request import urlopen,Request
from socket import timeout

class FbxCnx:
    def __init__(self,host="mafreebox.free.fr"):
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
        res = urlopen(request,timeout=2).read()
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
        res = urlopen(request,timeout=2).read()
        return json.loads(res.decode())

    def _get(self,method,data=None,headers=None):
        url = self.host+"/api/v4/"+method
        if headers:
            request = Request(url,headers=headers)
        else:
            request = Request(url)
        request.get_method = lambda:"GET"
        res = urlopen(request,timeout=2).read()
        return json.loads(res.decode())

    def _mksession(self):
        challenge=self._com("login/")["result"]["challenge"]
        data={
          "app_id": self.appid,
          "password": hmac.new(self.token.encode(),challenge.encode(),hashlib.sha1).hexdigest()
        }
        return self._com("login/session/",data)["result"]["session_token"]

    # def _disconnect(self):
    #     # result = self._com("/login/logout",None,{'Content-Type': 'application/json','X-Fbx-App-Auth': self.session})
    #     result = self._com("/login/logout")
    #     print (result)
    #     # return

class FbxApp(FbxCnx):
    def __init__(self,appid,token,session=None,host="mafreebox.free.fr"):
        FbxCnx.__init__(self,host)
        self.appid,self.token=appid,token
        self.session=session if session else self._mksession()

    # def __del__(self):
    #     self._disconnect()
    #     print ('died')

    def com(self,method,data=None):
        return self._com(method,data,{"X-Fbx-App-Auth": self.session})

    def put(self,method,data=None):
        return self._put(method,data,{"X-Fbx-App-Auth": self.session})

    def get(self,method,data=None):
        return self._get(method,data,{"X-Fbx-App-Auth": self.session})

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
                            percent = used/total*100
                            # print(str(label)+"=>"+str(round(percent,2))+"%")
                            retour.update({str(label):str(round(percent,2))})
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Log('La Freebox semble indisponible : '+ error.msg)
        except timeout:
            1 #on ne fait rien, on retourne une liste vide
        return retour
    
    def getNameByMacAdresse(self,p_macAdresse):
        try:
            listePeriph = self.com( "lan/browser/pub/")
            for periph in listePeriph["result"]:
                macAdresse = periph["id"]
                if(("ETHER-"+p_macAdresse.upper()) == macAdresse.upper()):
                    return periph["primary_name"]
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Log('La Freebox semble indisponible : '+ error.msg)
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
            Domoticz.Log('La Freebox semble indisponible : '+ error.msg)
        except timeout:
            1 #on ne fait rien, on retourne faux
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
            Domoticz.Log('La Freebox semble indisponible : '+ error.msg)
        except timeout:
            1 #on ne fait rien, on retourne une liste vide
        return retour

    def sysinfo(self):
        retour = {}
        try:
            sys = self.com( "system/")
            retour.update({str('temp_cpub'):str(round(sys["result"]["temp_cpub"],2))})
            retour.update({str('temp_sw'):str(round(sys["result"]["temp_sw"],2))})
            retour.update({str('temp_cpum'):str(round(sys["result"]["temp_cpum"],2))})
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Log('La Freebox semble indisponible : '+ error.msg)
        except timeout:
            1 #on ne fait rien, on retourne une liste vide
        return retour

    def isOnWIFI(self):
        try:
            v_result = self.get("wifi/config/")
            if(v_result["result"]["enabled"]):
                return 1
            else:
                return 0
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Log('La Freebox semble indisponible : '+ error.msg)
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
                    Domoticz.Log( "Wifi is now ON")
                    isOn = True
                else:
                    Domoticz.Log("Wifi is now OFF")
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Log('setOnOFFWifi Erreur '+ error.msg)
        except timeout:
            if not p_isPutOn:
                # If we are connected using wifi, disabling wifi will close connection
                # thus PUT response will never be received: a timeout is expected
                Domoticz.Log("Wifi désactivé")
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
        v_result = self.com( "system/reboot")
        if not v_result['success']:
            Domoticz.Log("Erreur lors du Reboot")
        Domoticz.Log("Freebox Server en cours de reboot.")
