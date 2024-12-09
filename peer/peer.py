import socket
import random
import threading
import os
import requests
import string

from torrent_log import TorrentLog
from tracker_http import Tracker_http
from torrent_helper import generate_torrent_file
from peer_connection_helper import Peer_connection
from peer_wire_messages import *
from handler_download import Handle_download

def generate_peer_id(client_code, version):
    # Ensure the client code and version have a total length of 8 characters
    client_prefix = f"-{client_code}{version}-"
    # Create a random string with the appropriate length so the total is 20 bytes
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=20 - len(client_prefix)))
    # Combine the client code, version, and random part
    peer_id = client_prefix + random_part
    return peer_id

def get_peer_ip_host():
    temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        temp_socket.connect(("10.255.255.255", 1))
        peer_ip = temp_socket.getsockname()[0]
        peer_port = random.randint(6881, 6889)
    except Exception:
        peer_ip = socket.gethostbyname(socket.gethostname())
        peer_port = random.randint(6881, 6889)
    finally:
        temp_socket.close()
    return peer_ip, peer_port

class Peer:
    def __init__(self, id, peer_ip, peer_port, tracker_url):
        self.id = id

        self.peer_id = generate_peer_id("MT", "0001")
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self.tracker_url = tracker_url

        self.is_running = True
        self.thread_lock = threading.Lock()

        self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.peer_socket.bind((self.peer_ip, self.peer_port))

        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        """Set up directories to store data and torrent files."""
        self.data_folder_path = os.path.join(self.base_path, f"MT0001-{self.id}-data-folder")
        self.torrent_folder_path = os.path.join(self.base_path, f"MT0001-{self.id}-torrent-folder")

        # Create directories if they don't exist
        os.makedirs(self.data_folder_path, exist_ok=True)
        os.makedirs(self.torrent_folder_path, exist_ok=True)

        self.torrent_log = TorrentLog(self.torrent_folder_path, self.data_folder_path)

    def stop(self):
        """Stop the Peer and announce 'stopped' event to the tracker."""
        self.is_running = False
        
        request_parameters = {
            'peer_id': self.peer_id,
            'port': self.peer_port,
            'event': 'stopped',
            'tracker_id': "-TK0001-0001"
        }

        tracker_url = self.tracker_url
        requests.get(tracker_url, params=request_parameters, timeout=5)
        print("Peer has been stopped.")

    def start(self):
        print(f"Peer ID: {self.peer_id}")
        print(f"Peer IP: {self.peer_ip}")
        print(f"Peer Port: {self.peer_port}")
        print(f"Tracker URL: {self.tracker_url}")

        print("Starting peer...")
        peer_thread = threading.Thread(target=self.listen_peer)
        peer_thread.start()

    def listen_peer(self):
        self.peer_socket.listen(10)

        while self.is_running:
            try:
                client_socket, client_address = self.peer_socket.accept()
                print(f"Connection from {client_address}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
                client_thread.start()
            except Exception as e:
                print(f"An error occurred: {e}")
                break

    def handle_client(self, client_socket, client_address):
        try:
            # Handle the client connection
            peer_conn = Peer_connection(client_address[0], client_address[1], self.peer_id, None, self.torrent_log, self.data_folder_path, client_socket)

            # Ensure handshake is completed before proceeding
            handshake_successful = False
            while not handshake_successful and self.is_running:
                try:
                    # Receive handshake message
                    handshake_message = peer_conn.recieve(HANDSHAKE_MESSAGE_LENGTH)
                    if not handshake_message:
                        print("Handshake failed: No data received.")
                        break
                    
                    if(peer_conn.recieved_handshake(handshake_message)):
                        handshake_successful = True
                    else:
                        print("Handshake failed: Incorrect handshake message.")
                        break

                except ConnectionResetError:
                    print("Connection was reset by the peer. Exiting loop.")
                    break
                except socket.timeout:
                    print("Socket timeout. Peer is unresponsive.")
                    break
                except Exception as e:
                    print(f"An error occurred while handling a message: {e}")
                    break

            # Handle the peer connection
            print("Waiting for message...")
            while self.is_running:
                try:
                    message = peer_conn.handle_response()
                except Exception as e:
                    print(f"An error occurred while handling a message: {e}")
                    break
        except Exception as e:
            print(f"An error occurred while handling client: {e}")
        finally:
            client_socket.close()

    def download_torrent_by_info_hash(self, info_hash):
        print("Downloading torrent by info hash...")
        tracker_http = Tracker_http(self.torrent_log, self.peer_id, self.peer_ip, self.peer_port, info_hash, self.tracker_url, self.torrent_folder_path)
        if tracker_http.request_torrent_file():
            peer.torrent_log.print_torrent_info()
            return True
        else:
            print("Torrent download failed.")
            return False

    def announce_have_data(self, info_hash):
        print("Announcing to tracker that peer has the data...")
        tracker_http = Tracker_http(self.torrent_log, self.peer_id, self.peer_ip, self.peer_port, info_hash, self.tracker_url, self.torrent_folder_path)
        if tracker_http.announce_started_but_already_completed():
            print(tracker_http.__str__())
            return True
        else:
            print("Announce not successful.")
            return False

    def get_peers(self, info_hash):
        print("Getting peers from tracker...")
        tracker_http = Tracker_http(self.torrent_log, self.peer_id, self.peer_ip, self.peer_port, info_hash, self.tracker_url, self.torrent_folder_path)
        tracker_http.announce_started()
        print(tracker_http.__str__())

    def update_torrent_log(self):
        self.torrent_log.scan_torrent_files()
        self.torrent_log.print_torrent_info()

    def generate_torrent_file(self, data_file_path):
        generate_torrent_file(self.torrent_log, self.tracker_url, self.torrent_folder_path, data_file_path, self.data_folder_path)
        self.torrent_log.print_torrent_info()

    def download_file(self, info_hash):
        """
        Start downloading a file using Handle_download.
        """
        print(f"Starting download for info hash: {info_hash}")
        # Get the list of Peers from Tracker
        if not info_hash in self.torrent_log.torrent_data:
            if not self.download_torrent_by_info_hash(info_hash):
                print("Failed to download torrent file.")
                return

        self.get_peers(info_hash)
        tracker_http = Tracker_http(self.torrent_log, self.peer_id, self.peer_ip, self.peer_port, info_hash, self.tracker_url, self.torrent_folder_path)
        tracker_http.announce_started()

        # Get the list of Peers from Tracker HTTP
        peers_data = tracker_http.peers_list

        if not peers_data:
            print("No peers available for downloading.")
            return

        # Create instance of Handle_download
        handle_download = Handle_download(
            torrent_metadata=self.torrent_log.get_torrent_metadata_by_infohash(info_hash),  # Torrent metadata
            peers_data=peers_data,
            client_peer_id=self.peer_id,
            torrent_log=self.torrent_log,
            data_folder_path=self.data_folder_path
        )

        # Start file download
        handle_download.download_file()
        print("Download initiated.")

# Main CLI handling
if __name__ == "__main__":
    try:
        id = input("Enter the peer id: ")
        peer_ip, peer_port = get_peer_ip_host()
        peer_port = 6884

        tracker_url = input("Enter the tracker URL (e.g., http://192.168.1.5:22236): ")

        peer = Peer(id=id, peer_ip=peer_ip, peer_port=peer_port, tracker_url=tracker_url)
        peer.start()

        print("\nWelcome to Simple Torrent CLI!")
        print(
            "\nCommand options:\n"
            "  stop                                     - Stop the peer and disconnect\n"
            "  announce_have_data <info_hash>           - Announce complete and send torrent file to tracker\n"
            "  download_torrent_by_info_hash <info_hash>- Get torrent by info hash\n"
            "  get_peers <info_hash>                    - List peers for the specified info hash\n"
            "  update_torrent_log                       - Update the torrent log from folder\n"
            "  generate_torrent_file <data_file_path>   - Generate a .torrent file\n"
            "  download_file <info_hash>                - Start downloading a file\n"
            "  get_torrent_info <info_hash>             - Get torrent info\n"
            "  get_torrent_log                          - Get torrent log\n"
            "  help                                     - Show this help message\n"
            "  exit                                     - Exit the program\n"
        )

        while True:
            command = input("> ").strip()
            args = command.split()

            if not args:
                continue

            action = args[0]

            try:
                if action == "stop":
                    peer.stop()
                    break

                elif action == "announce_have_data":
                    if len(args) < 2:
                        print("Usage: announce_have_data <info_hash>")
                    else:
                        peer.announce_have_data(info_hash=args[1])

                elif action == "download_torrent_by_info_hash":
                    if len(args) < 2:
                        print("Usage: download_torrent_by_info_hash <info_hash>")
                    else:
                        print(peer.download_torrent_by_info_hash(info_hash=args[1]))

                elif action == "get_peers":
                    if len(args) < 2:
                        print("Usage: get_peers <info_hash>")
                    else:
                        peer.get_peers(info_hash=args[1])

                elif action == "update_torrent_log":
                    peer.update_torrent_log()

                elif action == "generate_torrent_file":
                    if len(args) < 2:
                        print("Usage: generate_torrent_file <data_file_path>")
                    else:
                        peer.generate_torrent_file(data_file_path=args[1])
                elif action == "download_file":
                    if len(args) < 2:
                        print("Usage: download_file <info_hash>")
                    else:
                        peer.download_file(info_hash=args[1])
                elif action == "get_torrent_info":
                    if len(args) < 2:
                        print("Usage: get_torrent_info <info_hash>")
                    else:
                        peer.torrent_log.get_torrent_data(args[1])
                        print(peer.torrent_log.get_torrent_metadata_by_infohash(args[1]))
                elif action == "get_torrent_log":
                    peer.torrent_log.print_torrent_info()
                elif action == "help":
                    print(
                        "\nCommand options:\n"
                        "  stop                                     - Stop the peer and disconnect\n"
                        "  announce_have_data <info_hash>           - Announce completion to tracker\n"
                        "  download_torrent_by_info_hash <info_hash>- Get torrent by info hash\n"
                        "  get_peers <info_hash>                    - List peers for the specified info hash\n"
                        "  update_torrent_log                       - Update torrent log from folder\n"
                        "  generate_torrent_file <data_file_path>   - Generate a .torrent file\n"
                        "  download_file <info_hash>                - Start downloading a file\n"
                        "  get_torrent_info <info_hash>             - Get torrent info\n"
                        "  get_torrent_log                          - Get torrent log\n"
                        "  help                                     - Show this help message\n"
                        "  exit                                     - Exit the program\n"
                    )

                elif action == "exit":
                    peer.stop()
                    break

                else:
                    print("Unknown command. Type 'help' for available commands.")

            except Exception as e:
                print(f"An error occurred: {e}")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
        os._exit(0)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        os._exit(1)