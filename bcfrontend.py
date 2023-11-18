import gradio as gr
from bcbackend import RESTClient, RESTRequest
from bcbackend import get_auth_status, get_power_status, get_input, get_inputs, get_apps
from time import sleep

class FrontendGUI:
    def __init__(self, tvs):
        self.tvs = tvs
        self.tvs_index = None
        self.tv = None
        self.client = None
        self.auth_status = None
        self._psk = None
        self.inputs = None
        self.input = None
        self.power_status = None
        self.volume_status = None
        self.apps = None
        self.app_index = None

        self.tvs_dropdown = None
        self.psk_textbox = None
        self.power_button = None
        self.power_textbox = None
        self.inputs_dropdown = None
        self.input_button = None
        self.input_textbox = None
        self.volume_dropdown = None
        self.volume_index = None
        self.volume_slider = None
        self.volume_button = None
        self.volume_textbox = None
        self.mute_checkbox = None
        self.app_gallery = None
        self.app_launch_button = None
        self.app_terminate_button = None

        self.components = None

        self.launch = None

        with gr.Blocks(title='Bravia Control') as interface:
            heading = '# Bravia Control'
            bravia_link_1 = '[BRAVIA IP Control Documentation]'
            bravia_link_2 = '(https://pro-bravia.sony.net/develop/integrate/ip-control/index.html)'
            github_link_1 = '[Bravia Control GitHub]'
            github_link_2 = '()'
            gr.Markdown(f'{heading}\n{bravia_link_1}{bravia_link_2} {github_link_1}{github_link_2}')
            with gr.Row():
                with gr.Row():
                    self.tvs_dropdown = self.get_tvs_dropdown()
                    self.auth_textbox = self.get_auth_textbox()
                self.psk_textbox = self.get_psk_textbox()

            with gr.Row():
                self.power_button = self.get_power_button()
                self.power_textbox = self.get_power_textbox()
            
            self.inputs_dropdown = self.get_inputs_dropdown()
            with gr.Row():
                self.input_button = self.get_input_button()
                self.input_textbox = self.get_input_textbox()

            with gr.Column():
                self.volume_dropdown = self.get_volume_dropdown()
                self.volume_slider = self.get_volume_slider()
                with gr.Row():
                    self.volume_button = self.get_volume_button()
                    self.volume_textbox = self.get_volume_textbox()
                    self.mute_checkbox = self.get_mute_checkbox()
            
            self.app_gallery = self.get_app_gallery()
            with gr.Row():
                self.app_launch_button = self.get_app_launch_button()
                self.app_terminate_button = self.get_app_terminate_button()

            self.components = [self.auth_textbox, self.psk_textbox, self.power_button, self.power_textbox,
                               self.inputs_dropdown, self.input_button, self.input_textbox, self.volume_dropdown,
                               self.volume_slider, self.volume_button, self.volume_textbox, self.mute_checkbox,
                               self.app_gallery, self.app_launch_button, self.app_terminate_button]

            self.psk_textbox.submit(self.set_psk_textbox, inputs=self.psk_textbox,
                                    outputs=[self.tvs_dropdown] + self.components)
            self.tvs_dropdown.change(self.set_tvs_dropdown, inputs=self.tvs_dropdown, outputs=self.components)
            self.power_button.click(self.set_power_button, outputs=self.components)
            self.input_button.click(self.set_input_button, inputs=self.inputs_dropdown,
                                    outputs=[self.inputs_dropdown, self.input_textbox])
            self.volume_dropdown.change(self.set_volume_dropdown, inputs=self.volume_dropdown,
                                        outputs = [self.volume_slider, self.volume_button,
                                                   self.volume_textbox, self.mute_checkbox])
            self.volume_button.click(self.set_volume_button, inputs=self.volume_slider,
                                     outputs=[self.volume_slider, self.volume_textbox])
            self.mute_checkbox.input(self.set_mute_checkbox, inputs=self.mute_checkbox,
                                     outputs=self.mute_checkbox)
            self.app_gallery.select(self.set_app_gallery)
            self.app_launch_button.click(self.set_app_launch_button)
            self.app_terminate_button.click(self.set_app_terminate_button)

            self.launch = interface.launch
    
    @property
    def psk(self):
        return self._psk

    @psk.setter
    def psk(self, psk):
        self._psk = psk
        if self.client: self.client.psk = psk

    def get_tvs_dropdown(self):
        choices = [i['modelName'] for i in self.tvs]
        return gr.Dropdown(choices=choices, label='Available TVs', type='index',
                           interactive=True, scale=2)
    
    def refresh_interface(self):
        return [self.get_auth_textbox(), self.get_psk_textbox(), self.get_power_button(),
                self.get_power_textbox(), self.get_inputs_dropdown(), self.get_input_button(),
                self.get_input_textbox(), self.get_volume_dropdown(), self.get_volume_slider(),
                self.get_volume_button(), self.get_volume_textbox(), self.get_mute_checkbox(),
                self.get_app_gallery(), self.get_app_launch_button(), self.get_app_terminate_button()]

    def set_tvs_dropdown(self, tvs_index):
        self.tvs_index = tvs_index
        if self.tvs_index is None:
            self.tv = None
            return self.refresh_interface()
        self.tv = self.tvs[self.tvs_index]
        if self.tv['psk'] is not None: self.psk = self.tv['psk']
        self.client = RESTClient(self.tv['ip'], psk=self.psk)
        self.auth_status = get_auth_status(self.client)
        self.power_status = get_power_status(self.client)
        return self.refresh_interface()
    
    def get_auth_textbox(self):
        value = 'Authenticated' if self.auth_status else 'Not Authenticated'
        return gr.Textbox(label='Authentication Status', value=value, interactive=False)

    def get_psk_textbox(self):
        return gr.Textbox(label='Pre-Shared Key', value=self.psk, type='password', interactive=True)
    
    def set_psk_textbox(self, psk):
        self.psk = psk
        if self.tv: self.auth_status = get_auth_status(self.client)
        tvs_dropdown = self.get_tvs_dropdown()
        return [tvs_dropdown] + self.refresh_interface()
    
    def get_power_button(self):
        interactive = self.auth_status
        return gr.Button(value='Toggle Power', interactive=interactive)

    def set_power_button(self):
        status = get_power_status(self.client)
        set_request = RESTRequest('system', 'setPowerStatus', params={'status': not status})
        _ = self.client.send_request(set_request)
        sleep(5.0)
        self.power_status = status
        return self.refresh_interface()

    def get_power_textbox(self):
        if not self.tv:
            value = 'No TV Selected.'
        else:
            status = get_power_status(self.client)
            value = 'Active' if status else 'Standby'
        return gr.Textbox(value=value, label='Current Power State', interactive=False)
    
    def get_inputs_dropdown(self):
        if not self.tv:
            choices = ['No TV Selected.']
            value = choices[0]
            interactive = False
        else:
            inputs_request = RESTRequest('avContent', 'getCurrentExternalInputsStatus', ver=1.1)
            inputs_response = self.client.send_request(inputs_request)
            self.inputs = get_inputs(inputs_response)
            choices = [f'{item["index"]} : {item["title"]} : {item["label"]}' for item in self.inputs]
            value = choices[0]
            input_request = RESTRequest('avContent', 'getPlayingContentInfo')
            input_response = self.client.send_request(input_request)
            input = get_input(input_response, inputs_response)
            if input: value = f'{input["index"]} : {input["title"]} : {input["label"]}'
            interactive = True
        return gr.Dropdown(choices=choices, value=value, label='Inputs',
                           interactive=interactive, type='index')
    
    def get_input_button(self):
        interactive = self.auth_status and self.power_status
        return gr.Button(value='Set Input', interactive=interactive)

    def set_input_button(self, input_index):
        uri = self.inputs[input_index]['uri']
        set_request = RESTRequest('avContent', 'setPlayContent', params={'uri': uri})
        _ = self.client.send_request(set_request)
        sleep(5.0)
        self.input = self.inputs[input_index]
        inputs_dropdown = self.get_inputs_dropdown()
        input_textbox = self.get_input_textbox()
        return [inputs_dropdown, input_textbox]
    
    def get_input_textbox(self):
        if not self.tv or not self.auth_status:
            value = 'No TV Selected or Unauthorized'
        else:
            value = 'No External Input Detected'
            input_request = RESTRequest('avContent', 'getPlayingContentInfo')
            input_response = self.client.send_request(input_request)
            inputs_request = RESTRequest('avContent', 'getCurrentExternalInputsStatus', ver=1.1)
            inputs_response = self.client.send_request(inputs_request)
            input = get_input(input_response, inputs_response)
            if input: value = f'{input["index"]} : {input["title"]} : {input["label"]}'
        return gr.Textbox(value=value, label='Current Input', interactive=False)
    
    def get_volume_dropdown(self):
        choices = ['No Target(s) Available']
        interactive = False
        if self.auth_status:
            request = RESTRequest('audio', 'getVolumeInformation')
            response = self.client.send_request(request)
            result = response.data.get('result')
            if result:
                result = result[0]
                choices = [item['target'].capitalize() for item in result]
                interactive = True
        return gr.Dropdown(choices=choices, value=choices[0], label='Volume Target',
                           interactive=interactive, type='index')
    
    def set_volume_dropdown(self, volume_index):
        request = RESTRequest('audio', 'getVolumeInformation')
        response = self.client.send_request(request)
        self.volume_index = None
        self.volume_status = None
        if response.data.get('result'):
            result = response.data['result'][0]
            self.volume_index = volume_index
            self.volume_status = result[volume_index]
        volume_slider = self.get_volume_slider()
        volume_button = self.get_volume_button()
        volume_textbox = self.get_volume_textbox()
        mute_checkbox = self.get_mute_checkbox()
        return [volume_slider, volume_button, volume_textbox, mute_checkbox]
    
    def get_volume_slider(self):
        value = 0
        minimum = 0
        maximum = 100
        interactive = False
        if self.auth_status and self.volume_status:
            self.volume_status = self.set_volume_status()
            if self.volume_status:
                value = self.volume_status['volume']
                minimum = self.volume_status['minVolume']
                maximum = self.volume_status['maxVolume']
                interactive = True
        return gr.Slider(value=value, minimum=minimum, maximum=maximum,
                         label='Target Volume', interactive=interactive)
    
    def get_volume_button(self):
        interactive = self.auth_status and bool(self.volume_status)
        return gr.Button(value='Set Volume', interactive=interactive)
    
    def set_volume_button(self, volume):
        interactive = self.auth_status and bool(self.volume_status)
        if interactive:
            params = {
                'target': self.volume_status['target'],
                'volume': str(volume),
                'ui': None
            }
            while self.volume_status['volume'] != volume:
                request = RESTRequest('audio', 'setAudioVolume', params=params, ver=1.2)
                _ = self.client.send_request(request)
                sleep(1.0)
                self.volume_status = self.set_volume_status()
        volume_slider = self.get_volume_slider()
        volume_textbox = self.get_volume_textbox()
        return [volume_slider, volume_textbox]
    
    def get_volume_textbox(self):
        value = 'N/A'
        if self.auth_status and self.volume_status:
            self.volume_status = self.set_volume_status()
            if self.volume_status:
                value = self.volume_status['volume']
        return gr.Textbox(value=value, label='Current Volume', interactive=False)
    
    def get_mute_checkbox(self):
        value = False
        interactive = bool(self.tv) and self.auth_status and bool(self.volume_status)
        if interactive:
            self.volume_status = self.set_volume_status()
            if self.volume_status:
                value = self.volume_status['mute']
        return gr.Checkbox(value=value, label='Muted', info='Current Mute State',
                           interactive=interactive)
            
    def set_mute_checkbox(self, mute):
        interactive = self.auth_status and bool(self.volume_status)
        if interactive:
            request = RESTRequest('audio', 'setAudioMute', params={'status': mute})
            _ = self.client.send_request(request)
            self.volume_status = self.set_volume_status()
            if self.volume_status:
                mute = self.volume_status['mute']
        return gr.Checkbox(value=mute, label='Muted', info='Current Mute State',
                           interactive=interactive)
    
    def set_volume_status(self):
        request = RESTRequest('audio', 'getVolumeInformation')
        response = self.client.send_request(request)
        if response.data.get('result'):
            result = response.data['result'][0]
            status = result[self.volume_index]
            return status
        return None
    
    def get_app_gallery(self):
        value = None
        self.apps = None
        if self.auth_status:
            self.apps = get_apps(self.client)
            value = [(item['cached_icon_path'], item['title']) for item in self.apps]
        return gr.Gallery(value=value, label='Apps', allow_preview=False,
                           object_fit='scale-down', columns=9)
        
    def set_app_gallery(self, evt: gr.SelectData):
        self.app_index = evt.index
    
    def get_app_launch_button(self):
        interactive = self.auth_status and bool(self.apps)
        return gr.Button(value='Launch Selected App', interactive=interactive)
    
    def get_app_terminate_button(self):
        interactive = self.auth_status
        return gr.Button(value='Terminate All Apps', interactive=interactive)
    
    def set_app_launch_button(self):
        if self.app_index is not None:
            app_uri = self.apps[self.app_index]['uri']
            request = RESTRequest('appControl', 'setActiveApp', params={'uri': app_uri})
            _ = self.client.send_request(request)
    
    def set_app_terminate_button(self):
        request = RESTRequest('appControl', 'terminateApps')
        _ = self.client.send_request(request)