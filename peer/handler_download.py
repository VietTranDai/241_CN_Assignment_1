from io_file_handler import torrent_shared_file_handler
from peer_connection_helper import Peer_connection

from threading import *

class Handle_download():
    def __init__(self, torrent_metadata, peers_data, client_peer_id, torrent_log, data_folder_path):
        # Initialize the torrent metadata
        self.torrent_metadata = torrent_metadata

        # Initialize the torrent log
        self.torrent_log = torrent_log

        # Initialize the client peer id
        self.client_peer_id = client_peer_id

        # Initialize the peers data
        self.peers_list = []
        for peer_ip, peer_port in peers_data:
            self.peers_list.append(Peer_connection(peer_ip, peer_port, client_peer_id, torrent_metadata, torrent_log, data_folder_path))

        # Initialize the data folder path
        self.data_folder_path = data_folder_path

        """
            peer_have_piece[i] = [] # List of peers having the ith piece
        """
        self.peer_have_piece = {i: [] for i in range(torrent_metadata.pieces_count)}

        # Initialize the IO handler
        self.file_handler = torrent_shared_file_handler(self.torrent_metadata, self.data_folder_path)

        # Bitfield for pieces downloaded from peers
        self.bitfield_pieces_downloaded = set([])

        # Array to track how many pieces each peer is handling
        self.num_pieces_peer_handles = [0] * len(self.peers_list)

        # Lock to synchronize updates to shared state
        self.handle_lock = Lock()

        # Flag to indicate whether downloading is complete
        self.download_complete = False

        print("Download handler initialized.")

    def add_shared_file_handler(self):
        # Add the shared file handler to all peer connections
        for peer_conn in self.peers_list:
            peer_conn.add_file_handler(self.file_handler)

    def connect_peer(self, peer_idx):
        """
        Connect to a peer, perform handshake, and receive bitfield.
        """
        # Perform handshake with the peer
        if not self.peers_list[peer_idx].initiate_handshake():
            print(f"Handshake with peer {peer_idx} failed.")
            return False

        # Receive bitfield from the peer
        peer_bitfield = self.peers_list[peer_idx].initialize_bitfield()

        if peer_bitfield is None or len(peer_bitfield) != self.torrent_metadata.pieces_count:
            print(f"Invalid bitfield received from peer {peer_idx}.")
            return False

        # Update the list of peers that have each piece
        with self.handle_lock:
            for i in range(self.torrent_metadata.pieces_count):
                if peer_bitfield[i]:
                    self.peer_have_piece[i].append(peer_idx)

        print(f"Connected to peer {peer_idx}. Bitfield updated.")
        return True

    def download_file(self):
        """
        Initialize connections to peers and start downloading the file.
        """
        # Check if the file handler has been initialized
        if not self.file_handler:
            print("File handler not initialized.")
            return False
        
        # Add the file handler to all peer connections
        self.add_shared_file_handler()

        print("Starting download...")
        # Connect to all peers (perform handshake and receive bitfield)
        connect_threads = []
        for peer_index in range(len(self.peers_list)):
            thread = Thread(target=self.connect_peer, args=(peer_index,))
            connect_threads.append(thread)
            thread.start()

        # Wait for all connection threads to complete
        for thread in connect_threads:
            thread.join()

        print("Starting download using strategies...")
        # Start downloading pieces from peers
        self.download_using_strategies()

        # Close all peer connections after download is complete
        self.close_all_peer_connections()

    def download_using_strategies(self):
        """
        Distribute the list of pieces to download to each peer beforehand, 
        and then each peer downloads its assigned pieces.
        """
        cur_bitfield = self.torrent_log.get_bitfield(self.torrent_metadata.info_hash)
        for idx in range(len(cur_bitfield)):
            if cur_bitfield[idx] == 1:
                self.bitfield_pieces_downloaded.add(idx)

        # List of pieces that still need to be downloaded
        pieces_to_download = set(range(self.torrent_metadata.pieces_count)) - self.bitfield_pieces_downloaded
        print(f"Total pieces to download: {len(pieces_to_download)}")

        # Create a dictionary to assign pieces to each peer
        peer_piece_map = {peer_idx: [] for peer_idx in range(len(self.peers_list))}

        # Assign pieces to peers
        for piece_idx in pieces_to_download:
            # List of peers that can provide this piece
            available_peers = self.peer_have_piece.get(piece_idx, [])
            if not available_peers:
                print(f"No peers available for piece {piece_idx}. Skipping.")
                continue

            # Select the peer with the fewest assigned pieces
            best_peer = min(available_peers, key=lambda peer_idx: len(peer_piece_map[peer_idx]))
            peer_piece_map[best_peer].append(piece_idx)

        print(f"Piece distribution among peers: {peer_piece_map}")

        # Create threads for downloading
        download_threads = []

        for peer_idx, pieces in peer_piece_map.items():
            if pieces:
                # Create a thread for each peer to download its assigned pieces
                thread = Thread(target=self.download_pieces_from_peer, args=(peer_idx, pieces))
                download_threads.append(thread)
                thread.start()

        # Wait for all threads to finish
        for thread in download_threads:
            thread.join()

        # Check if all pieces have been downloaded
        if not (set(range(self.torrent_metadata.pieces_count)) - self.bitfield_pieces_downloaded):
            with self.handle_lock:
                self.download_complete = True
            print("All pieces downloaded successfully!")

    def download_pieces_from_peer(self, peer_idx, pieces):
        """
        Download all assigned pieces from a specific peer.
        """
        peer = self.peers_list[peer_idx]
        print(f"Peer {peer_idx} started downloading pieces: {pieces}")

        for piece_idx in pieces:
            if peer.download_piece(piece_idx):
                print(f"Peer {peer_idx} successfully downloaded piece {piece_idx}.")
                with self.handle_lock:
                    self.bitfield_pieces_downloaded.add(piece_idx)
            else:
                print(f"Peer {peer_idx} failed to download piece {piece_idx}.")



    def close_all_peer_connections(self):
        """
        Close all peer connections after the download process is complete.
        """
        print("Closing all peer connections...")
        for peer_conn in self.peers_list:
            peer_conn.close_peer_connection()
        print("All peer connections closed.")
