import requests
from ipaddress import ip_address
from concurrent.futures import ThreadPoolExecutor, as_completed
from fnmatch import fnmatch
from tqdm import tqdm
import html
import zlib
import urllib.request
from urllib.parse import urlparse
import os
from pathlib import Path
from ssdpy import SSDPClient

base_path = Path(os.path.realpath(__file__)).parent
cache_path = base_path/'iconcache'
input_filename = 'tvs.txt'

class RESTRequest:
    def __init__(self, service, method, headers=None, params=None, id=1, ver=1.0):
        self.service = service
        self.method = method
        self.headers = headers or {}
        self.params = params or {}
        self.id = id
        self.ver = ver

class RESTResponse:
    def __init__(self, status_code, headers=None, data=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.data = data

class RESTClient:
    def __init__(self, ip, psk=None):
        self.ip = ip_address(ip)
        self.psk = str(psk)
        self.base_url = f'http://{self.ip}/sony/'
        self.headers = {}

    def send_request(self, api_request):
        url = self.base_url + api_request.service
        self.headers['X-Auth-PSK'] = self.psk
        headers = api_request.headers if api_request.headers else self.headers
        params = api_request.params if isinstance(api_request.params, list) else [api_request.params]
        response = requests.post(
            url,
            headers=headers,
            json={
                'method': api_request.method,
                'params': params,
                'id': api_request.id,
                'version': str(api_request.ver)
            }
        )

        return RESTResponse(
            status_code=response.status_code,
            headers=response.headers,
            data=response.json() if response.headers['Content-Type'] == 'application/json' else response.text
        )
    
def get_ip_and_psk():
    tv_list = []
    input_file = base_path/input_filename
    if not input_file.is_file(): return tv_list
    with open(input_file) as file:
        for line in file:
            if not line.strip(): continue
            ip, *psk = line.split(',', 1)
            try: ip = ip_address(ip)
            except: continue
            psk = psk[0] if psk else None
            psk = psk.strip('\n')
            tv_list.append({'ip': ip, 'psk': psk})
    return tv_list

def get_tvs(tv_list=[]):
    print('\nDiscovering TVs. Please Wait...')
    futures_list = []
    if not tv_list:
        client = SSDPClient()
        results = client.m_search()
        for r in results:
            if '::' in r['usn'] and fnmatch(r['usn'].split('::')[-1], '*sony*'):
                ip = ip_address(urlparse(r['location']).hostname)
                tv_list.append(ip)
        tv_list = list(set(tv_list))
        tv_list = [{'ip': ip, 'psk': None} for ip in tv_list]
    
    def proc_request(tv):
        client = RESTClient(tv['ip'])
        request = RESTRequest('system', 'getInterfaceInformation')
        try:
            response = client.send_request(request)
            response.ip = tv['ip']
            response.psk = tv['psk']
        except:
            response = None
        return response

    with tqdm(total=len(tv_list), unit='ip', leave=False) as pbar:
        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(proc_request, tv) for tv in tv_list]
            for future in as_completed(futures):
                futures_list.append(future)
                pbar.update()

    responses = []
    for f in futures:
        response = f.result()
        if response and response.status_code == 200:
            result = response.data['result'][0]
            result['ip'] = response.ip
            result['psk'] = response.psk
            name = result['productName']
            category = result['productCategory'].lower()
            if name and fnmatch(name, '*BRAVIA*') and category == 'tv':
                responses.append(result)

    assert responses, 'No TVs found. Need an SSDP response or IP(s) to proceed.'
    print('\nFound TV(s):')
    [print(r['ip'], ':', r['modelName']) for r in responses]
    print()
    return responses

def get_auth_status(client):
    request = RESTRequest('system', 'getNetworkSettings')
    response = client.send_request(request)
    if response.status_code == 403:
        return False
    return True

def get_power_status(client):
        get_request = RESTRequest('system', 'getPowerStatus')
        result = client.send_request(get_request)
        status = result.data['result'][0]['status']
        status = True if status == 'active' else False
        return status

def get_inputs(response):
    if response.data.get('result'):
        result = response.data['result'][0]
        result = [{'index': i, **item} for i, item in enumerate(result)]
        result = [{key: 'No Label' if key == 'label' and not value
                   else value for key, value in item.items()} for item in result]
        for item in result:
            if item['uri'].startswith('extInput:cec?'):
                item['title'] += ' (CEC)'
        return result
    return None

def get_input(input_response, inputs_response):
    inputs = get_inputs(inputs_response)
    if input_response.data.get('result'):
        input = input_response.data['result'][0]
        for item in inputs:
            if item['uri'] == input['uri']:
                return item
    return None

def get_apps(client):
    request = RESTRequest('appControl', 'getApplicationList')
    response = client.send_request(request)
    if response.data.get('result') is None:
        return None
    result = response.data['result'][0]
    apps = result
    for i, app in enumerate(apps):
        app['index'] = i
        app['title'] = html.unescape(app['title'])
        icon_url = app['icon']
        cached_icon_basename = str(hex(zlib.crc32(icon_url.encode('utf-8')) & 0xffffffff))
        cached_icon_extension = icon_url.split(".")[-1]
        cached_icon_filename = f'{cached_icon_basename}.{cached_icon_extension}'
        try:
            cached_icon_path = str(cache_path/cached_icon_filename)
            urllib.request.urlretrieve(icon_url, cached_icon_path)
        except:
            cached_icon_path = cache_path/'placeholder.png'
        app['cached_icon_path'] = cached_icon_path
    apps = sorted(apps, key=lambda x: x['title'])
    return apps