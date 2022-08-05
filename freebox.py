# Thanks to http://www.manatlan.com/blog/freeboxv6_api_v3_avec_python & https://github.com/supermat/PluginDomoticzFreebox
# Code under GPLv3
# AUTHOR : supermat & ilionel
# CONTRIBUTOR : https://github.com/ilionel/PluginDomoticzFreebox/graphs/contributors
# Please not that supermat don't maintain this software anymore

import urllib.request
import hmac
import json
import hashlib
import time
from urllib.request import urlopen, Request
from socket import timeout
import Domoticz

# Globals CONSTANT
HOST = 'mafreebox.freebox.fr'   # FQDN of freebox
API_VER = 'v4'                  # API version
REGISTER_TMOUT = 30             # Timout in sec (for Obtain an app_token)
API_TMOUT = 4                   # Timout in sec (for API response)


class FbxCnx:
    """
    FbxCnx describes methods to communicate with Freebox
    """

    def __init__(self, host=HOST, api=API_VER):
        self.host = host
        self.api_ver = api

    def _request(self, path, method='GET', headers=None, data=None):
        """ Send a request to Freebox API

        Args:
            path (str): api_url
            method (str, optional): method used for each request GET|POST|PUT. Defaults to 'GET'.
            headers (dict of str: str, optional): HTTP HEADERS. Defaults to None.
            data (dict of str: str, optional): POST or PUT datas. Defaults to None.

        Returns:
            (dict of str: str): Freebox API Response as dictionary
        """
        url = self.host + '/api/' + self.api_ver + '/' + path
        Domoticz.Debug('API REQUEST - URL: ' + url)
        Domoticz.Debug('API REQUEST - Method: ' + method)
        Domoticz.Debug('API REQUEST - Headers: ' + f"{headers}")
        Domoticz.Debug('API REQUEST - Data: ' + f"{data}")
        if data is not None:
            data = json.dumps(data)
            data = data.encode()
        request = Request(url=url, data=data, method=method)
        if headers is not None:
            request.headers.update(headers)
        api_response = urlopen(request, timeout=API_TMOUT).read()
        Domoticz.Debug('<- API Response: ' + f"{api_response}")
        dict_response = json.loads(api_response.decode())
        return dict_response

    def register(self, app_id, app_name, version, device_name, wait=REGISTER_TMOUT):
        """
        register method is used to obtain a "app_token" (ak. grant access to Freebox)

        You must gain access to Freebox API before being able to use the api.

        This is the first step, the app will ask for an app_token using the following call.
        A message will be displayed on the Freebox LCD asking the user to grant/deny access
        to the requesting app.
        Once the app has obtained a valid app_token, it will not have to do this procedure again
        unless the user revokes the app_token.

        Args:
            app_id (str): A unique application identifier string
            app_name (str): A descriptive application name (will be displayed on lcd)
            version (str): app version
            device_name (str): The name of the device on which the app will be used
            wait (int, optional): seconds before timeout. Defaults to REGISTER_TMOUT.

        Returns:
            str: "app_token" if success else "error message"
        """
        data = {
            'app_id': app_id,
            'app_name': app_name,
            'app_version': version,
            'device_name': device_name
        }
        response = self._request('login/authorize/', 'POST', None, data)
        status = 'pending'
        if not response['success'] and response['msg']:
            return False or f"Registration error: {response['msg']}"
        track_id, app_token = response['result']['track_id'], response['result']['app_token']
        while status != 'granted' and wait != 0:
            status = self._request(f"login/authorize/{track_id}")
            status = status['result']['status']
            wait = wait - 1
            time.sleep(1)
        return status == 'granted' and app_token

    def _mksession(self, app_id, app_token):
        """
        Create a new session (to make an authenticated call to the API)

        To protect the "app_token" secret, it will never be used directly to authenticate
        the application, instead the API will provide a challenge the app will combine to
        its "app_token" to open a session and get a "session_token"

        The app will then have to include the session_token in the HTTP headers of the
        following requests

        Args:
            app_id (str): A unique application identifier string
            app_token (str): Secret application token

        Returns:
            str: "session_token"
        """
        challenge = self._request('login/')['result']['challenge']
        Domoticz.Debug("Challenge: " + challenge)
        data = {
            "app_id": app_id,
            "password": hmac.new(app_token.encode(), challenge.encode(), hashlib.sha1).hexdigest()
        }
        session_token = self._request(
            'login/session/', 'POST', None, data)['result']['session_token']
        Domoticz.Debug("Session Token: " + session_token)
        return session_token

    def _disconnect(self, session_token):
        """
        Closing the current session

        Returns:
            (dict of str: str): Freebox API Response as dictionary
        """
        result = self._request(
            'login/logout/',
            'POST',
            {'Content-Type': 'application/json', 'X-Fbx-App-Auth': session_token})
        Domoticz.Debug("Disconnect" + result)
        return result


class FbxApp(FbxCnx):
    """
    FbxApp describe methodes to call specified Freebox API

    Args:
        FbxCnx (FbxCnx): Freebox connection
    """
    def __init__(self, app_id, app_token, session_token=None, host=HOST):
        FbxCnx.__init__(self, host)
        self.app_id, self.app_token = app_id, app_token
        self.session_token = self._mksession(app_id, app_token) if session_token is None else session_token

    def __del__(self):
        self._disconnect(self.session_token)

    def post(self, path, data=None):
        """
        HTTP POST Request to API

        Args:
            path (str): api_url
            data (dict of str: str, optional): _description_. Defaults to None.

        Returns:
            (dict of str: str): Freebox API Response as dictionary
        """
        return self._request(path, 'POST', {"X-Fbx-App-Auth": self.session_token}, data)

    def put(self, path, data=None):
        """
        HTTP PUT Request to API

        Args:
            path (str): api_url
            data (dict of str: str, optional): _description_. Defaults to None.

        Returns:
            (dict of str: str): Freebox API Response as dictionary
        """
        return self._request(path, 'PUT', {"X-Fbx-App-Auth": self.session_token}, data)

    def get(self, path):
        """
        HTTP GET Request to API

        Args:
            path (str): api_url

        Returns:
            (dict of str: str): Freebox API Response as dictionary
        """
        return self._request(path, 'GET', {"X-Fbx-App-Auth": self.session_token})

    def ls_storage(self):
        """
        List storages attached to the Freebox server

        Returns:
            (dict of str: str): {disk_label: % of usage}
        """
        result = {}
        try:
            ls_disk = self.get('storage/disk/')
            if 'result' in ls_disk:  # /!\ Freebox mini 4K don't have any disk
                for disk in ls_disk['result']:
                    if 'partitions' in disk:  # /!\ Freebox mini 4K don't have any disk
                        for partition in disk['partitions']:
                            label = partition['label']
                            used = partition['used_bytes']
                            total = partition['total_bytes']
                            Domoticz.Debug('Disk '+label+' ' +
                                           str(used)+'/'+str(total))
                            if total > 0:
                                percent = used/total*100
                                result.update(
                                    {str(label): str(round(percent, 2))})
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('API Error ("storage/disk/"): ' + error.msg)
        except timeout:
            Domoticz.Error('Timeout when call ("storage/disk/")')
        return result

    def get_name_from_macaddress(self, p_macaddress):
        """
        Find device name by his mac-address

        Args:
            p_macaddress (str): @mac type 01:02:03:04:05:06

        Returns:
            str: device name
        """
        result = ""
        try:
            ls_devices = self.get("lan/browser/pub/")
            for device in ls_devices['result']:
                macaddress = device['id']
                if(("ETHER-" + p_macaddress.upper()) == macaddress.upper()):
                    result = device['primary_name']
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('API Error ("lan/browser/pub/"): ' + error.msg)
        except timeout:
            Domoticz.Error('Timeout')
        return result

    def reachable_macaddress(self, p_macaddress):
        """
        Check if device is reachable by his mac-address

        Args:
            p_macaddress (str): @mac type 01:02:03:04:05:06

        Returns:
            bool: True if reachable else False
        """
        result = False
        try:
            ls_devices = self.get('lan/browser/pub/')
            for device in ls_devices['result']:
                macaddress = device['id']
                if ("ETHER-" + p_macaddress.upper()) == macaddress.upper():
                    reachable = device['reachable']
                    active = device['active']
                    if reachable and active:
                        result = True
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('API Error ("lan/browser/pub/"): ' + error.msg)
        except timeout:
            Domoticz.Error('Timeout')  # False if Error occured
        return result

    def online_devices(self):
        """
        Get online devices

        Returns:
            (dict of str: str): {macaddress: name}
        """
        result = {}
        try:
            ls_devices = self.get("lan/browser/pub/")
            for device in ls_devices['result']:
                name = device['primary_name']
                reachable = device['reachable']
                active = device['active']
                macaddress = device['id']
                if reachable and active:
                    result.update({macaddress: name})
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('API Error ("lan/browser/pub/"): ' + error.msg)
        except timeout:
            Domoticz.Error('Timeout')  # Empty list if Error occured
        return result

    def sysinfo(self):
        """
        Get all temperatures sensors values

        Returns:
            (dict of str: str): {sensor: temp} (in °C)
        """
        result = {}
        try:
            sys = self.get('system/')
            result.update({str('temp_cpub'): str(
                round(sys['result']['temp_cpub'], 2))})
            if sys['result']['board_name'] == 'fbxgw8r':
                Domoticz.Log('Freebox POP')
                result.update({str('temp_t1'): str(
                    round(sys['result']['temp_t1'], 2))})
                result.update({str('temp_t2'): str(
                    round(sys['result']['temp_t2'], 2))})
            else:
                result.update({str('temp_sw'): str(
                    round(sys['result']['temp_sw'], 2))})
                result.update({str('temp_cpum'): str(
                    round(sys['result']['temp_cpum'], 2))})
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('API Error ("system/"): ' + error.msg)
        except timeout:
            Domoticz.Error('Timeout') # Empty list if Error occured
        return result

    def connection_rate(self):
        """
        Get Up and Down rate

        Returns:
            (dict of str: str): {rate_down: rate, rate_up: rate} (Ko/s)
        """
        result = {}
        try:
            connection = self.get('connection/')
            result.update({str('rate_down'): str(
                connection['result']['rate_down']/1024/8)})
            result.update({str('rate_up'): str(
                connection['result']['rate_up']/1024/8)})
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('API Error ("connection/"): ' + error.msg)
        except timeout:
            Domoticz.Error('Timeout') # Empty list if Error occured
        return result

    def connection_state(self):
        """
        Is WAN link UP or DOWN

        Returns:
            bool: True if "UP" else False
        """
        state = None
        try:
            connection = self.get('connection/')
            if connection['result']['state'] == 'up':
                Domoticz.Log('Connection is UP')
                state = True
            else:
                Domoticz.Log('Connection is DOWN')
                state = False
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('API Error ("connection/"): ' + error.msg)
        except timeout:
            Domoticz.Error('Timeout')  # None if Error occured
        return state

    def wifi_state(self):
        """
        Is WLAN state UP or DOWN

        Returns:
            bool: True if "UP" else False
        """
        enabled = None
        try:
            wifi = self.get('wifi/config/')
            if wifi['result']['enabled']:
                enabled = True
            else:
                enabled = False
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('API Error ("wifi/config/"): ' + error.msg)
        except timeout:
            Domoticz.Error('Timeout')  # None if Error occured
        return enabled

    def wifi_enable(self, switch_on):
        """
        Switch wifi ON or OFF

        Args:
            switch_on (bool): True to switch ON or False du switch OFF

        Raises:
            timeout: Catch error if you are disconnected due to wifi switch OFF
            
        Returns:
            bool: wifi state
        """
        status = None
        if switch_on:
            data = {'enabled': True}
        else:
            data = {'enabled': False}
        try:
            response = self.put("wifi/config/", data)
            status = False
            if response['success']:
                if response['result']['enabled']:
                    status = True
                    Domoticz.Debug('Wifi is now ON')
                else:
                    Domoticz.Debug('Wifi is now OFF')
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            Domoticz.Error('API Error ("wifi/config/"): ' + error.msg)
        except timeout:
            if not switch_on:
                # If we are connected using wifi, disabling wifi will close connection
                # thus PUT response will never be received: a timeout is expected
                Domoticz.Error('Wifi disabled')
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
        return status

    def reboot(self):
        """
        Reboot the Freebox server
        """
        Domoticz.Error('Try to reboot with session : ' + self.session_token)
        response = self.post("system/reboot")
        if response['success']:
            Domoticz.Debug('Reboot initiated')
        else:
            Domoticz.Error('Error: You must grant reboot permission')
