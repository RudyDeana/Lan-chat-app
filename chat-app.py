import socket
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from datetime import datetime
import json

class P2PChat:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chat P2P Base")
        self.root.geometry("500x600")

        self.username = None
        self.port = 5555
        self.udp_port = 5556
        self.my_ip = socket.gethostbyname(socket.gethostname())

        self.peers = {}               # username → {'ip': str, 'port': int, 'last_seen': float}
        self.chat_windows = {}        # ('private', username) → {'window': Toplevel, 'text': Text}

        # Socket UDP per discovery
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_sock.bind(('', self.udp_port))

        # Socket TCP per ricevere messaggi
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.bind(('', self.port))
        self.tcp_sock.listen(5)

        # Thread di background
        threading.Thread(target=self.udp_broadcast, daemon=True).start()
        threading.Thread(target=self.udp_listen, daemon=True).start()
        threading.Thread(target=self.tcp_listen, daemon=True).start()
        threading.Thread(target=self.cleanup_thread, daemon=True).start()

        self.ask_username()

    def ask_username(self):
        self.username = simpledialog.askstring("Nome", "Come ti chiami?")
        if not self.username or self.username.strip() == "":
            self.username = f"User{int(time.time()) % 10000}"

        self.root.title(f"Chat LAN - {self.username}")
        self.build_ui()
        self.root.mainloop()

    def build_ui(self):
        tk.Label(self.root, text=f"Utenti online ({self.username})", font=("Arial", 14, "bold")).pack(pady=10)

        self.users_list = tk.Listbox(self.root, height=10, font=("Arial", 12))
        self.users_list.pack(fill="both", expand=True, padx=10, pady=5)
        self.users_list.bind('<<ListboxSelect>>', self.on_user_select)

        tk.Button(self.root, text="Chat di tutti", command=self.open_global_chat, bg="#4CAF50", fg="white").pack(pady=10, fill="x", padx=20)

        self.update_users_list()

    def update_users_list(self):
        self.users_list.delete(0, tk.END)
        for uname in sorted(self.peers.keys()):
            self.users_list.insert(tk.END, uname)
        self.root.after(4000, self.update_users_list)  # refresh ogni 4 sec

    def udp_broadcast(self):
        while True:
            try:
                msg = f"DISC|{self.username}|{self.port}".encode()
                self.udp_sock.sendto(msg, ('<broadcast>', self.udp_port))
            except:
                pass
            time.sleep(4)

    def udp_listen(self):
        while True:
            try:
                data, addr = self.udp_sock.recvfrom(512)
                parts = data.decode(errors='ignore').split('|')
                if len(parts) == 3 and parts[0] == "DISC":
                    uname, port_str = parts[1], parts[2]
                    port = int(port_str)
                    if uname != self.username and addr[0] != self.my_ip:
                        self.peers[uname] = {'ip': addr[0], 'port': port, 'last_seen': time.time()}
            except:
                pass

    def cleanup_thread(self):
        while True:
            time.sleep(20)
            now = time.time()
            expired = [u for u, d in self.peers.items() if now - d['last_seen'] > 60]
            for u in expired:
                self.peers.pop(u, None)

    def tcp_listen(self):
        while True:
            try:
                client, _ = self.tcp_sock.accept()
                threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
            except:
                pass

    def handle_client(self, client):
        try:
            while True:
                len_b = client.recv(4)
                if not len_b:
                    break
                length = int.from_bytes(len_b, 'big')
                data = client.recv(length)
                if not data:
                    break
                msg = json.loads(data.decode(errors='ignore'))
                self.process_msg(msg)
        except:
            pass
        finally:
            client.close()

    def process_msg(self, msg):
        typ = msg.get('type')
        sender = msg.get('from')
        content = msg.get('msg')
        if sender == self.username:
            return

        ts = datetime.now().strftime("%H:%M")

        if typ == 'global':
            if hasattr(self, 'global_win') and self.global_win.winfo_exists():
                self.global_text.insert(tk.END, f"[{ts}] {sender}: {content}\n")
                self.global_text.see(tk.END)

        elif typ == 'private':
            key = ('private', sender)
            if key in self.chat_windows and self.chat_windows[key]['window'].winfo_exists():
                text = self.chat_windows[key]['text']
                text.insert(tk.END, f"[{ts}] {sender}: {content}\n")
                text.see(tk.END)
            else:
                self.open_private_chat(sender, initial=f"[{ts}] {sender}: {content}\n")

    def send_to(self, target_ip, target_port, message_dict):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((target_ip, target_port))
            data = json.dumps(message_dict).encode()
            s.send(len(data).to_bytes(4, 'big') + data)
            s.close()
        except:
            pass

    def open_global_chat(self):
        if hasattr(self, 'global_win') and self.global_win.winfo_exists():
            self.global_win.lift()
            return

        win = tk.Toplevel(self.root)
        win.title("Chat di tutti")
        win.geometry("500x500")

        text = scrolledtext.ScrolledText(win, wrap=tk.WORD, font=("Consolas", 11))
        text.pack(fill="both", expand=True, padx=8, pady=8)

        entry = tk.Entry(win, font=("Arial", 12))
        entry.pack(fill="x", padx=8, pady=5)
        entry.bind("<Return>", lambda e: self.send_global(entry, text))

        tk.Button(win, text="Invia", command=lambda: self.send_global(entry, text)).pack(pady=5)

        self.global_win = win
        self.global_text = text
        win.protocol("WM_DELETE_WINDOW", lambda: setattr(self, 'global_win', None) or win.destroy())

    def send_global(self, entry, text_widget):
        msg = entry.get().strip()
        if not msg:
            return
        ts = datetime.now().strftime("%H:%M")
        text_widget.insert(tk.END, f"[{ts}] Tu: {msg}\n")
        text_widget.see(tk.END)
        entry.delete(0, tk.END)

        data = {'type': 'global', 'from': self.username, 'msg': msg}
        for peer in list(self.peers.values()):
            self.send_to(peer['ip'], peer['port'], data)

    def on_user_select(self, event):
        selection = self.users_list.curselection()
        if not selection:
            return
        index = selection[0]
        username = self.users_list.get(index)
        self.open_private_chat(username)

    def open_private_chat(self, target, initial=None):
        key = ('private', target)
        if key in self.chat_windows and self.chat_windows[key]['window'].winfo_exists():
            self.chat_windows[key]['window'].lift()
            if initial:
                self.chat_windows[key]['text'].insert(tk.END, initial)
                self.chat_windows[key]['text'].see(tk.END)
            return

        win = tk.Toplevel(self.root)
        win.title(f"Chat con {target}")
        win.geometry("500x500")

        text = scrolledtext.ScrolledText(win, wrap=tk.WORD, font=("Consolas", 11))
        text.pack(fill="both", expand=True, padx=8, pady=8)

        entry = tk.Entry(win, font=("Arial", 12))
        entry.pack(fill="x", padx=8, pady=5)
        entry.bind("<Return>", lambda e: self.send_private(entry, text, target))

        tk.Button(win, text="Invia", command=lambda: self.send_private(entry, text, target)).pack(pady=5)

        self.chat_windows[key] = {'window': win, 'text': text}

        if initial:
            text.insert(tk.END, initial)
            text.see(tk.END)

        win.protocol("WM_DELETE_WINDOW", lambda: self.chat_windows.pop(key, None) or win.destroy())

    def send_private(self, entry, text_widget, target):
        msg = entry.get().strip()
        if not msg:
            return
        ts = datetime.now().strftime("%H:%M")
        text_widget.insert(tk.END, f"[{ts}] Tu: {msg}\n")
        text_widget.see(tk.END)
        entry.delete(0, tk.END)

        if target not in self.peers:
            messagebox.showwarning("Offline", f"{target} sembra offline al momento.")
            return

        data = {'type': 'private', 'from': self.username, 'msg': msg}
        peer = self.peers[target]
        self.send_to(peer['ip'], peer['port'], data)


if __name__ == "__main__":
    P2PChat()