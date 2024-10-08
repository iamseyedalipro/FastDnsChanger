import tkinter as tk
from tkinter import ttk
import ctypes
import subprocess
import psutil
import socket
import time
from dns import resolver

def measure_dns_speed(dns_ip):
    """
    Measure the DNS resolution time for a given DNS server IP.

    Args:
        dns_ip (str): The DNS server IP address.
        update_callback (function): Callback function to update UI with results.

    Returns:
        float: The DNS resolution time in milliseconds.
    """
    res = resolver.Resolver()
    res.nameservers = [dns_ip]
    test_domain = "chatgpt.com"

    start_time = time.time()
    try:
        res.resolve(test_domain)
    except Exception as e:
        return float('inf')

    end_time = time.time()
    resolution_time = (end_time - start_time) * 1000  # Convert to milliseconds
    # result = f"DNS {dns_ip} speed: {resolution_time:.2f} ms"
    return resolution_time


def find_fastest_dns(dns_dict, update_callback):
    """
    Find the fastest DNS server from a dictionary of DNS servers.

    Args:
        dns_dict (dict): Dictionary of DNS server names and their IPs.
        update_callback (function): Callback function to update UI with results.

    Returns:
        str: The name of the fastest DNS server.
    """
    best_time = float('inf')
    best_server = None

    for server, ips in dns_dict.items():
        primary_time = measure_dns_speed(ips[0])
        secondary_time = measure_dns_speed(ips[1])
        avg_time = (primary_time + secondary_time) / 2

        result = f"{server} DNS average speed: {avg_time:.2f} ms"
        print(result)
        update_callback(result)

        if avg_time < best_time:
            best_time = avg_time
            best_server = server

    return best_server



dns = {
    "Shecan": ["178.22.122.100", "185.51.200.2"],
    "403": ["10.202.10.202", "10.202.10.102"],
    "Begzar": ["185.55.226.26", "185.55.225.25"],
    "Electro": ["78.157.42.101", "78.157.42.100"],
    #"Hostiran": ["172.29.2.100", "172.29.0.100"],
    #"Radar": ["10.202.10.10", "10.202.10.11"],
    #"Shatel": ["85.15.1.14", "85.15.1.15"],
    #"Level3": ["209.244.0.3", "209.244.0.4"],
    #"OpenDNS": ["208.67.222.222", "208.67.220.220"]

}

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        if self.tooltip_window:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                         background='seashell3', relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class DNSChangerApp:
    def __init__(self, root):
        """
        Initialize the DNS Changer application.

        Args:
            root (tk.Tk): The root Tkinter window object.
        """
        self.root = root
        self.root.title("DNS Changer")
        self.root.geometry("500x300")
        self.root.resizable(False, False)
        photo = tk.PhotoImage(file = 'dnsicon.png')
        self.root.wm_iconphoto(False, photo)

        self.selected_option = tk.StringVar()
        self.interface_selected_option = tk.StringVar()
        
        self.setup_ui()
        
        if not self.is_user_admin():
            self.show_error("Error: This program requires administrative privileges.")
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.DISABLED)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind('<Control-Return>', lambda event: self.connect())
        self.root.bind('<Control-Shift-Return>', lambda event: self.check_speed_and_connect())
        self.root.bind('<Alt-Return>', lambda event: self.disconnect())
        self.root.bind('<Control-s>', lambda event: self.next_server())
    

    def next_server(self):
        current_index = list(dns.keys()).index(self.selected_option.get())
        next_index = (current_index + 1) % len(dns)
        self.selected_option.set(list(dns.keys())[next_index])
        


    def setup_ui(self):
        """
        Set up the user interface for the DNS Changer application.
        """
        frame = tk.Frame(self.root)
        frame.pack(padx=10, pady=10)

        self.connect_button = tk.Button(frame, text="Connect", command=self.connect)
        self.connect_button.pack(side=tk.LEFT, padx=5)
        ToolTip(self.connect_button, "Ctrl + Enter to Connect")

        self.disconnect_button = tk.Button(frame, text="Disconnect", command=self.disconnect)
        self.disconnect_button.pack(side=tk.LEFT, padx=5)
        ToolTip(self.disconnect_button, "Alt + Enter to Disconnect")

        self.selected_option.set(list(dns.keys())[0])
        self.selector = ttk.OptionMenu(frame, self.selected_option, *list(dns.keys()))
        self.selector.pack(side=tk.LEFT, padx=5)

        interfaces = self.get_active_interface_names()
        self.interface_selected_option.set(interfaces[0])
        self.interface_selector = ttk.OptionMenu(frame, self.interface_selected_option, *interfaces)
        self.interface_selector.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(self.root, text="Status: Disconnected", fg="red")
        self.status_label.pack(pady=10)

        self.check_speed_button = tk.Button(frame, text="Check Speed and Connect", command=self.check_speed_and_connect)
        self.check_speed_button.pack(side=tk.LEFT, padx=5)
        ToolTip(self.check_speed_button, "Ctrl + Shift + Enter")


        self.error_text_box = tk.Text(self.root, height=10, width=50)
        self.error_text_box.pack(pady=10)

        self.refresh_options(self.selector, self.selected_option, list(dns.keys()))
        self.refresh_options(self.interface_selector, self.interface_selected_option, interfaces)

        # Bind the on_dns_option_change method to OptionMenu selection change
        self.selector.bind('<Configure>', lambda event: self.on_dns_option_change())

    def disable_buttons(self):
        self.connect_button.config(state=tk.DISABLED)
        self.disconnect_button.config(state=tk.DISABLED)

    def enable_buttons(self):
        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.NORMAL)

    def get_active_interface_names(self):
        """
        Get a list of active network interface names.

        Returns:
            list: List of active network interface names.
        """
        net_if_stats = psutil.net_if_stats()
        active_interfaces = []
        wifi_interface = None

        for interface_name, stats in net_if_stats.items():
            if stats.isup:
                if 'wi-fi' in interface_name.lower():
                    wifi_interface = interface_name
                else:
                    active_interfaces.append(interface_name)

        if wifi_interface:
            active_interfaces.insert(0, wifi_interface)

        return active_interfaces

    def check_speed_and_connect(self):
        self.disable_buttons()
        self.error_text_box.delete("1.0", tk.END)
        self.status_label.config(text="Status: Checking DNS speeds...", fg="blue")
        self.root.update()

        def update_callback(result):
            self.error_text_box.insert(tk.END, result + '\n')
            self.error_text_box.see(tk.END)
            self.root.update_idletasks()

        fastest_dns = find_fastest_dns(dns, update_callback)

        if fastest_dns:
            self.selected_option.set(fastest_dns)
            self.connect()
        else:
            self.status_label.config(text="Status: Failed to determine fastest DNS", fg="red")

        self.enable_buttons()

    def set_dns(self, interface, ip1, ip2):
        """
        Set DNS servers for a given network interface.

        Args:
            interface (str): Name of the network interface.
            ip1 (str): Primary DNS server IP address.
            ip2 (str): Secondary DNS server IP address.

        Returns:
            bool: True if DNS servers were set successfully, False otherwise.
        """
        command1 = f'netsh interface ip set dns name="{interface}" static {ip1}'
        command2 = f'netsh interface ip add dns name="{interface}" {ip2} index=2'
        try:
            subprocess.run(command1, check=True, shell=True)
            subprocess.run(command2, check=True, shell=True)
            print(f'DNS set to {ip1} and {ip2}')
            return True
        except subprocess.CalledProcessError as e:
            self.show_error(f'Failed to set DNS: {e}')
            return False

    def delete_dns(self, interface):
        """
        Delete DNS settings for a given network interface.

        Args:
            interface (str): Name of the network interface.

        Returns:
            bool: True if DNS settings were deleted successfully, False otherwise.
        """
        command = f'netsh interface ipv4 set dns name="{interface}" dhcp'
        try:
            subprocess.run(command, check=True, shell=True)
            print('DNS settings deleted')
            return True
        except subprocess.CalledProcessError as e:
            self.show_error(f'Failed to delete DNS settings: {e}')
            return False

    def connect(self):
        self.disable_buttons()
        if not self.set_dns(self.interface_selected_option.get(), dns[self.selected_option.get()][0], dns[self.selected_option.get()][1]):
            self.enable_buttons()
            return
        self.status_label.config(text=f"Status: Connected to {self.selected_option.get()}", fg="green")
        print("Connected to", self.selected_option.get())
        self.enable_buttons()

    def disconnect(self):
        self.disable_buttons()
        if not self.delete_dns(self.interface_selected_option.get()):
            self.enable_buttons()
            return
        self.status_label.config(text="Status: Disconnected", fg="red")
        print("Disconnected")
        self.enable_buttons()

    def on_dns_option_change(self):
        self.disconnect()

    def refresh_options(self, menu, variable, options):
        """
        Refresh the options in an OptionMenu widget.

        Args:
            menu (ttk.OptionMenu): The OptionMenu widget to refresh.
            variable (tk.StringVar): The StringVar associated with the OptionMenu.
            options (list): List of options to populate in the OptionMenu.
        """
        menu['menu'].delete(0, 'end')
        for option in options:
            menu['menu'].add_command(label=option, command=tk._setit(variable, option))

    def is_user_admin(self):
        """
        Check if the user has administrative privileges.

        Returns:
            bool: True if the user is an administrator, False otherwise.
        """
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except AttributeError:
            return False

    def show_error(self, message):
        """
        Display an error message in the error text box.

        Args:
            message (str): The error message to display.
        """
        self.error_text_box.insert(tk.END, message + '\n')
        self.error_text_box.see(tk.END)

    def on_closing(self):
        """
        Actions to perform when the application window is closed.
        """
        self.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DNSChangerApp(root)
    root.mainloop()
