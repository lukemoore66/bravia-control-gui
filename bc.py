from bcbackend import get_tvs, get_ip_and_psk
from bcfrontend import FrontendGUI

ip_and_psk_list = get_ip_and_psk()
tvs = get_tvs(ip_and_psk_list)
interface = FrontendGUI(tvs)
interface.launch()