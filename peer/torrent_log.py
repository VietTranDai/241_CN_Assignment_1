import os
import json
from threading import Lock
import hashlib
import bencodepy

from beautifultable import BeautifulTable
from torrent_helper import Torrent_file_reader

"""
    * info_hash          : unique identifier (SHA-1 hash) for each torrent
        * piece_size         : number of bytes per piece (integer)
        * piece_count        : total number of pieces in the torrent (integer)
        * torrent_save_path  : the file path where the .torrent file is stored (string)
        * data_save_path     : the directory path where the downloaded data is saved (string)
        * bitfield           : list of integers representing the download status of each piece (0 = not downloaded, 1 = downloaded)
        * list_peers         : list of dictionaries containing information about connected peers
            * ip_address     : IP address of the peer (string)
            * port           : port number the peer is using for communication (integer)
"""
class TorrentLog:
    def __init__(self, torrent_folder_path, data_folder_path, json_path=None):
        self.torrent_folder_path = torrent_folder_path
        self.data_folder_path = data_folder_path

        # Default to 'torrent_log.json' in the current directory
        if json_path is None:
            self.json_path = os.path.join(os.getcwd(), "torrent_log.json")
        else:
            self.json_path = json_path

        self.torrent_data = {}
        self.lock = Lock()  # Create a Lock object
        self.load_data()
        self.scan_torrent_files()

        print("TorrentLog initialized.")

    def load_data(self):
        """Load data from the JSON file if it exists."""
        try:
            if os.path.exists(self.json_path):
                with open(self.json_path, "r") as file:
                    try:
                        self.torrent_data = json.load(file)
                        print(f"Loaded data from {self.json_path}")
                    except json.JSONDecodeError:
                        print("Error decoding JSON file. Initializing with empty data.")
                        self.torrent_data = {}
            else:
                print("JSON file not found. Initializing with empty data.")
                self.torrent_data = {}
        except Exception as e:
            print(f"Error loading data from JSON file: {e}")

    def save_data(self):
        """Save current data to JSON file."""
        print("Attempting to save data to JSON file...")
        try:
            with open(self.json_path, "w") as file:
                json.dump(self.torrent_data, file, indent=4)
            print(f"Data has been saved to {self.json_path}")
        except Exception as e:
            print(f"Error saving data to JSON file: {e}")

    def scan_torrent_files(self):
        """Scan .torrent files in the folder and update the log."""
        if not os.path.isdir(self.torrent_folder_path):
            print(f"Directory {self.torrent_folder_path} does not exist.")
            return

        for filename in os.listdir(self.torrent_folder_path):
            if filename.endswith(".torrent"):
                torrent_path = os.path.join(self.torrent_folder_path, filename)
                try:
                    info_hash = self.get_info_hash_from_file(torrent_path)

                    if not info_hash:
                        print(f"Failed to extract info_hash from file {filename}. Skipping this file.")
                        continue

                    
                    if info_hash in self.torrent_data:
                        print(f"Torrent with info_hash {info_hash} already exists. Skipping file {filename}.")
                        continue

                    print(f"New .torrent file found: {filename}")
                    torrent_reader = Torrent_file_reader(torrent_path)

                    piece_size = torrent_reader.piece_length
                    pieces_count = len(torrent_reader.pieces) // 20
                    torrent_save_path = torrent_path
                    data_save_path = os.path.join(self.data_folder_path, torrent_reader.name)
                    bitfield = [0] * pieces_count

                    self.add_torrent(
                        info_hash,
                        piece_size,
                        pieces_count,
                        torrent_save_path,
                        data_save_path,
                        bitfield
                    )
                except Exception as e:
                    print(f"Error reading .torrent file {filename}: {e}")

    def add_torrent(self, info_hash, piece_size, pieces_count, torrent_save_path, data_save_path, bitfield=None):
        """Add a new torrent to the log."""
        if bitfield is None:
            bitfield = [0] * pieces_count

        with self.lock:
            try:
                self.torrent_data[info_hash] = {
                    "piece_size": piece_size,
                    "piece_count": pieces_count,
                    "torrent_save_path": torrent_save_path,
                    "data_save_path": data_save_path,
                    "bitfield": bitfield,
                    "list_peers": []
                }
                print(f"Added new torrent with info_hash: {info_hash}")
                self.save_data()
            except Exception as e:
                print(f"Error adding torrent: {e}")

    def update_bitfield(self, info_hash, piece_index, status):
        """Update the bitfield status of a piece."""
        with self.lock:
            try:
                if info_hash in self.torrent_data:
                    if 0 <= piece_index < self.torrent_data[info_hash]["piece_count"]:
                        self.torrent_data[info_hash]["bitfield"][piece_index] = status
                        print(f"Updated bitfield for piece {piece_index} of {info_hash}.")
                        self.save_data()
                    else:
                        print(f"Invalid piece index {piece_index}.")
                else:
                    print(f"Torrent with info_hash {info_hash} not found.")
            except Exception as e:
                print(f"Error updating bitfield: {e}")

    def update_peers_list(self, info_hash, peer_list):
        """Update the peer list for a torrent."""
        with self.lock:
            try:
                if info_hash in self.torrent_data:
                    self.torrent_data[info_hash]["list_peers"] = peer_list
                    print(f"Updated peer list for torrent {info_hash}.")
                    self.save_data()
                else:
                    print(f"Torrent with info_hash {info_hash} not found.")
            except Exception as e:
                print(f"Error updating peer list: {e}")

    def get_peers(self, info_hash):
        """Get the list of peers for a torrent."""
        return self.torrent_data.get(info_hash, {}).get("list_peers", [])

    def get_bitfield(self, info_hash):
        """Get the bitfield of a torrent by info_hash."""
        return self.torrent_data.get(info_hash, {}).get("bitfield", [])

    def print_torrent_info(self):
        """Print information about all managed .torrent files."""
        if not self.torrent_data:
            print("No .torrent files are being managed.")
            return

        table = BeautifulTable()
        table.columns.header = ["Info Hash", "Piece Size (KB)", "Pieces Count", "Save Path"]

        for info_hash, data in self.torrent_data.items():
            piece_size_kb = data["piece_size"] // 1024
            pieces_count = data["piece_count"]
            save_path = data["data_save_path"]
            table.rows.append([info_hash, piece_size_kb, pieces_count, save_path])

        print(table)

    def get_info_hash_from_file(self, torrent_path):
        """Get the info_hash from a .torrent file."""
        try:
            with open(torrent_path, 'rb') as f:
                torrent_data = bencodepy.decode(f.read())
            raw_info = torrent_data[b'info']
            sha1_hash = hashlib.sha1(bencodepy.encode(raw_info))
            return sha1_hash.digest().hex()
        except Exception as e:
            print(f"Error reading .torrent file {torrent_path}: {e}")
            return None
        
    def get_torrent_metadata_by_infohash(self, info_hash):
        if info_hash in self.torrent_data:
            torrent_file_path = self.torrent_data[info_hash]["torrent_save_path"]
            return Torrent_file_reader(torrent_file_path)

    def get_torrent_data(self, info_hash):
        if info_hash in self.torrent_data:
            table = BeautifulTable()
            table.columns.header = ["Key", "Value"]
            for key, value in self.torrent_data[info_hash].items():
                table.rows.append([key, value])
            print(table)

    def get_bytes_of_torrent_file(self, info_hash):
        try:
            if info_hash in self.torrent_data:
                torrent_file_path = self.torrent_data[info_hash]["torrent_save_path"]
                with open(torrent_file_path, 'rb') as f:
                    return f.read()
            else:
                print(f"Torrent with info_hash {info_hash} not found.")
                return None
        except Exception as e:
            print(f"Error reading torrent file: {e}")
            return None