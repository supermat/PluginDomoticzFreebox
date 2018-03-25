#Code adapté de http://www.manatlan.com/blog/freeboxv6_api_v3_avec_python

import urllib.request,hmac,json,hashlib,time
from urllib.request import urlopen,Request

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
        res = urlopen(request).read()
        return json.loads(res.decode())

    def _mksession(self):
        challenge=self._com("login/")["result"]["challenge"]
        data={
          "app_id": self.appid,
          "password": hmac.new(self.token.encode(),challenge.encode(),hashlib.sha1).hexdigest()
        }
        return self._com("login/session/",data)["result"]["session_token"]

    # def _disconnect(self):
        # result = self._com("/login/logout",None,{"X-Fbx-App-Auth": self.session})
        # print (result)
        # return

class FbxApp(FbxCnx):
    def __init__(self,appid,token,session=None,host="mafreebox.free.fr"):
        FbxCnx.__init__(self,host)
        self.appid,self.token=appid,token
        self.session=session if session else self._mksession()

    # def __del__(self):
        # self._disconnect()
        # print ('died')

    def com(self,method,data=None):
        return self._com(method,data,{"X-Fbx-App-Auth": self.session})


    def diskinfo(self):
        listDisk = self.com( "storage/disk/")
        retour = {}
        for disk in listDisk["result"]:
            for partition in disk["partitions"]:
                label = partition["label"]
                used =partition["used_bytes"]
                total=partition["total_bytes"]
                percent = used/total*100
                # print(str(label)+"=>"+str(round(percent,2))+"%")
                retour.update({str(label):str(round(percent,2))})
        return retour
    
    def getNameByMacAdresse(self,p_macAdresse):
        listePeriph = self.com( "lan/browser/pub/")
        for periph in listePeriph["result"]:
            macAdresse = periph["id"]
            if(("ether-"+p_macAdresse) == macAdresse):
                return periph["primary_name"]
    
    def isPresenceByMacAdresse(self,p_macAdresse):
        listePeriph = self.com( "lan/browser/pub/")
        for periph in listePeriph["result"]:
            macAdresse = periph["id"]
            if(("ether-"+p_macAdresse) == macAdresse):
                reachable = periph["reachable"]
                active = periph["active"]
                if reachable and active:
                    return True
        return False

    def lanPeripherique(self):
        listePeriph = self.com( "lan/browser/pub/")
        retour = {}
        for periph in listePeriph["result"]:
            name = periph["primary_name"]
            reachable = periph["reachable"]
            active = periph["active"]
            macAdresse = periph["id"]
            if reachable and active:
                retour.update({macAdresse:name})
        return retour

    def sysinfo(self):
        sys = self.com( "system/")
        retour = {}
        retour.update({str('temp_cpub'):str(round(sys["result"]["temp_cpub"],2))})
        retour.update({str('temp_sw'):str(round(sys["result"]["temp_sw"],2))})
        retour.update({str('temp_cpum'):str(round(sys["result"]["temp_cpum"],2))})
        return retour
