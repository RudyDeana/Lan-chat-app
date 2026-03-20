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
        self.root.title("Chat P2P LAN")
        self.root.geometry("540x700")
        self.root.configure(bg="#181a1b")  # dark ma non nero puro

        self.username = None
        self.port = 5555
        self.udp_port = 5556
        self.my_ip = socket.gethostbyname(socket.gethostname())

        self.peers = {}
        self.chat_windows = {}  # 'global' o ('private', username)

        # UDP per discovery
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_sock.bind(('', self.udp_port))

        # TCP per messaggi
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.bind(('', self.port))
        self.tcp_sock.listen(5)

        threading.Thread(target=self.udp_broadcast, daemon=True).start()
        threading.Thread(target=self.udp_listen, daemon=True).start()
        threading.Thread(target=self.tcp_listen, daemon=True).start()
        threading.Thread(target=self.cleanup_thread, daemon=True).start()

        self.ask_username()

    def ask_username(self):
        self.username = simpledialog.askstring("Benvenuto", "Scegli il tuo username:")
        if not self.username or not self.username.strip():
            self.username = f"U{int(time.time()) % 10000}"

        self.root.title(f"Chat LAN • {self.username}")
        self.build_main_ui()
        self.root.mainloop()

    def build_main_ui(self):
        tk.Label(self.root, text=f"Utenti online • {self.username}",
                 font=("Segoe UI", 15, "bold"), bg="#181a1b", fg="#f0f0f0").pack(pady=16)

        frame_list = tk.Frame(self.root, bg="#181a1b")
        frame_list.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        self.users_list = tk.Listbox(frame_list, height=14, font=("Segoe UI", 12),
                                     bg="#222426", fg="#e8e8e8", selectbackground="#3a6ea5",
                                     selectforeground="white", activestyle="none", bd=0)
        self.users_list.pack(fill="both", expand=True)

        self.users_list.bind('<<ListboxSelect>>', self.on_user_select)

        btn_global = tk.Button(self.root, text="Chat di tutti",
                               command=self.open_global_chat,
                               font=("Segoe UI", 13, "bold"),
                               bg="#2e7d32", fg="white",
                               activebackground="#1b5e20",
                               activeforeground="white",
                               relief="flat", bd=0, padx=30, pady=12,
                               cursor="hand2")
        btn_global.pack(pady=16, fill="x", padx=40)

        # hover effect semplice
        btn_global.bind("<Enter>", lambda e: btn_global.config(bg="#388e3c"))
        btn_global.bind("<Leave>", lambda e: btn_global.config(bg="#2e7d32"))

        self.update_users_list()

    def update_users_list(self):
        self.users_list.delete(0, tk.END)
        for uname in sorted(self.peers.keys()):
            self.users_list.insert(tk.END, uname)
        self.root.after(4000, self.update_users_list)

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
                    uname, p = parts[1], int(parts[2])
                    if uname != self.username and addr[0] != self.my_ip:
                        self.peers[uname] = {'ip': addr[0], 'port': p, 'last_seen': time.time()}
            except:
                pass

    def cleanup_thread(self):
        while True:
            time.sleep(25)
            now = time.time()
            expired = [u for u, d in self.peers.items() if now - d['last_seen'] > 75]
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
                if not len_b: break
                length = int.from_bytes(len_b, 'big')
                data = client.recv(length)
                if not data: break
                msg = json.loads(data.decode(errors='ignore'))
                self.process_message(msg)
        except:
            pass
        finally:
            client.close()

    def process_message(self, msg):
        typ = msg.get('type')
        sender = msg.get('from')
        content = msg.get('msg')
        if sender == self.username: return

        ts = datetime.now().strftime("%H:%M")

        tag = "received"

        if typ == 'global':
            if 'global' in self.chat_windows and self.chat_windows['global'].winfo_exists():
                t = self.chat_windows['global']['text']
                t.insert(tk.END, f"[{ts}] {sender}: {content}\n", tag)
                t.see(tk.END)

        elif typ == 'private':
            key = ('private', sender)
            if key in self.chat_windows and self.chat_windows[key].winfo_exists():
                t = self.chat_windows[key]['text']
                t.insert(tk.END, f"[{ts}] {sender}: {content}\n", tag)
                t.see(tk.END)
            else:
                self.open_private_chat(sender, initial=f"[{ts}] {sender}: {content}\n")

    def send_to_peer(self, ip, port, data):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, port))
            payload = json.dumps(data).encode()
            s.send(len(payload).to_bytes(4, 'big') + payload)
            s.close()
        except:
            pass

    def create_chat_window(self, title, is_global=False, target=None, initial=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("540x640")
        win.configure(bg="#181a1b")

        text = scrolledtext.ScrolledText(win, wrap=tk.WORD, font=("Consolas", 11),
                                         bg="#202224", fg="#e8ecef",
                                         insertbackground="#ffffff",
                                         selectbackground="#4a6fa5")
        text.pack(fill="both", expand=True, padx=12, pady=12)
        text.tag_config("sent", foreground="#66bb6a")
        text.tag_config("received", foreground="#81d4fa")

        input_frame = tk.Frame(win, bg="#181a1b")
        input_frame.pack(fill="x", padx=12, pady=(0,12))

        entry = tk.Entry(input_frame, font=("Segoe UI", 12),
                         bg="#2a2c2e", fg="#f0f0f0",
                         insertbackground="#ffffff", relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0,6))

        send_btn = tk.Button(input_frame, text="Invia", font=("Segoe UI", 11, "bold"),
                             bg="#0288d1", fg="white",
                             activebackground="#0277bd", relief="flat", bd=0,
                             padx=16, pady=8, cursor="hand2")
        send_btn.pack(side="right")

        send_btn.bind("<Enter>", lambda e: send_btn.config(bg="#039be5"))
        send_btn.bind("<Leave>", lambda e: send_btn.config(bg="#0288d1"))

        key = 'global' if is_global else ('private', target)
        self.chat_windows[key] = {'window': win, 'text': text, 'entry': entry}

        if initial:
            text.insert(tk.END, initial, "received")
            text.see(tk.END)

        def send_func():
            if is_global:
                self.send_global(entry, text)
            else:
                self.send_private(entry, text, target)

        send_btn.config(command=send_func)
        entry.bind("<Return>", lambda e: send_func())

        win.protocol("WM_DELETE_WINDOW", lambda: self.chat_windows.pop(key, None) or win.destroy())
        entry.focus()

        return win, text, entry

    def open_global_chat(self):
        if 'global' in self.chat_windows and self.chat_windows['global']['window'].winfo_exists():
            self.chat_windows['global']['window'].lift()
            return

        self.create_chat_window("Chat di tutti", is_global=True)

    def send_global(self, entry, text_widget):
        msg = entry.get().strip()
        if not msg: return

        ts = datetime.now().strftime("%H:%M")
        text_widget.insert(tk.END, f"[{ts}] Tu: {msg}\n", "sent")
        text_widget.see(tk.END)
        entry.delete(0, tk.END)

        data = {'type': 'global', 'from': self.username, 'msg': msg}
        for peer in list(self.peers.values()):
            self.send_to_peer(peer['ip'], peer['port'], data)

    def on_user_select(self, event):
        sel = self.users_list.curselection()
        if not sel: return
        uname = self.users_list.get(sel[0])
        self.open_private_chat(uname)

    def open_private_chat(self, target, initial=None):
        key = ('private', target)
        if key in self.chat_windows and self.chat_windows[key]['window'].winfo_exists():
            self.chat_windows[key]['window'].lift()
            if initial:
                self.chat_windows[key]['text'].insert(tk.END, initial, "received")
                self.chat_windows[key]['text'].see(tk.END)
            return

        self.create_chat_window(f"Chat con {target}", is_global=False, target=target, initial=initial)

    def send_private(self, entry, text_widget, target):
        msg = entry.get().strip()
        if not msg: return

        ts = datetime.now().strftime("%H:%M")
        text_widget.insert(tk.END, f"[{ts}] Tu: {msg}\n", "sent")
        text_widget.see(tk.END)
        entry.delete(0, tk.END)

        if target not in self.peers:
            messagebox.showwarning("Offline?", f"{target} non sembra raggiungibile al momento.")
            return

        data = {'type': 'private', 'from': self.username, 'msg': msg}
        peer = self.peers[target]
        self.send_to_peer(peer['ip'], peer['port'], data)


if __name__ == "__main__":
    P2PChat()
