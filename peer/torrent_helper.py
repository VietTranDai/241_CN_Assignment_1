"""
    Helper functions or class to read or handle torrent file
"""
import hashlib
import bencodepy
from beautifultable import BeautifulTable
import os
import shutil

PIECE_LENGTH = 512 * (2 ** 10)  # 512 KB
BLOCK_SIZE = 16 * (2 ** 10) # 16 KB

"""
    Torrent metadata
"""
# The class contains important information about the torrent file
class torrent_metada():
    # Useful metadata from the torrent file
    def __init__(self, trackers_url, name, size, piece_length, pieces, info_hash, files):
        self.trackers_url  = trackers_url                   # string : URL of the tracker
        self.name           = name                          # string : the name of the directory in which to store all the files. This is purely advisory.
        self.size           = size                          # int    : size in bytes
        self.piece_length   = piece_length                  # int    : piece length in bytes
        self.pieces         = pieces                        # bytes  : sha1 hash concatenation of the file
        self.info_hash      = info_hash                     # sha1 hash of the info metadata
        self.files          = files                         # list   : [length, path] (multifile torrent)
        self.block_length   = BLOCK_SIZE                    # 16 KB
        self.pieces_count   = int(len(self.pieces) / 20)    # Number of pieces in the torrent


    def __str__(self):
        try:
            """Returns full information about the torrent file."""
            table = BeautifulTable()
            table.columns.header = ["TORRENT FILE DATA", "DATA VALUE"]

            # Add tracker URL information
            table.rows.append(["Tracker URL", self.trackers_url])

            # Add file/torrent name information
            table.rows.append(["Name", self.name])

            # Add file/torrent size information
            table.rows.append(["Size", f"{self.size} bytes"])

            # Add piece length information
            table.rows.append(["Piece Length", f"{self.piece_length} bytes"])

            # Add SHA1 hash information
            table.rows.append(["Info Hash", self.info_hash])

            # Display file list
            files_info = "\n".join([f"{file['length']} bytes - {file['path']}" for file in self.files])
            table.rows.append(["Files", files_info if files_info else "No files"])

            return str(table)
        except Exception as e:
            print(f"Error while converting torrent metadata to string: {e}")
            return ""

"""
    Torrent file reader reads the bencoded file with a torrent extension and 
    member functions of the class help in extracting data of the bytes class
    The torrent files contain metadata in the given format:

    * announce          : the URL of the tracker
    * info              : ordered dictionary containing key and values 
        * files         : list of directories each containing files (in case of multiple files)
            * length    : length of file in bytes
            * path      : contains path of each file
        * name          : name of the directory in which to store all the files or name of the file
        * piece length  : number of bytes per piece
        * pieces        : list of SHA1 hash of the given files
"""

# The class contains functions to read the torrent file and extract metadata
class Torrent_file_reader(torrent_metada):
    def __init__(self, torrent_file_path):
        self.torrent_file_path = torrent_file_path

        # Read and decode the torrent file with UTF-8 encoding
        self.torrent_data = self.decode_torrent_file()

        # Extract metadata from the torrent file
        announce = self.torrent_data[b'announce'].decode('utf-8')

        # Extract info from the torrent file
        self.info = self.torrent_data[b'info']

        # Extract name from the torrent file
        name = self.info[b'name'].decode('utf-8')

        # Extract info_hash from the torrent file
        piece_length = self.info[b'piece length']

        # Extract pieces from the torrent file
        pieces = self.info[b'pieces']

        # Extract files from the torrent file
        files = self.get_files_info()

        # Extract size from the torrent file
        size = 0
        for file in files:
            size += file['length']

        # Generate info_hash from the torrent file
        info_hash = self.generate_info_hash()

        # Call the parent class constructor
        super().__init__(announce, name, size, piece_length, pieces, info_hash, files)
        # (self, trackers_url, name, size, piece_length, pieces, info_hash, files):

        print("Torrent file read successfully")
        print(self.__str__())

    def decode_torrent_file(self):
        try:
            with open(self.torrent_file_path, 'rb') as f:
                torrent_data = bencodepy.decode(f.read())
            print("Torrent file decoded successfully")
            return torrent_data
        except Exception as e:
            print(f"Error while decoding torrent file: {e}")
            raise
    
    def get_files_info(self):
        files = []
        if b'files' in self.info:
            for file in self.info[b'files']:
                length = file[b'length']
                path = file[b'path'].decode('utf-8')
                files.append({'length': length, 'path': path})
        return files

    # Generate info_hash from the torrent file
    def generate_info_hash(self):
        sha1_hash = hashlib.sha1()
        # Get the raw info value
        raw_info = self.torrent_data[b'info']
        # Update the sha1 hash value
        sha1_hash.update(bencodepy.encode(raw_info))
        return sha1_hash.digest().hex()
    
    # Get the piece length of the given piece index
    def get_piece_length(self, piece_index):
        if piece_index == self.pieces_count - 1:
            return self.size % self.piece_length
        return self.piece_length
    
    def validate_piece_length(self, piece_index, block_offset, block_length):
        piece_length = self.get_piece_length(piece_index)
        return block_offset + block_length <= piece_length
     

def process_torrent_bytes_to_folder(torrent_bytes, torrent_data_folder):
    """
    Decode the torrent byte data, write files into the torrent_data_folder.
    """
    try:
        # Decode torrent byte data
        torrent_data = bencodepy.decode(torrent_bytes)
        print("Torrent data decoded successfully.")

        # Extract file name from metadata
        name = torrent_data[b'info'][b'name'].decode('utf-8')

        # Create folder if it doesn't exist
        os.makedirs(torrent_data_folder, exist_ok=True)

        # Full path of the .torrent file
        torrent_file_path = os.path.join(torrent_data_folder, f"{name}.torrent")

        # Write the torrent file into the folder
        with open(torrent_file_path, 'wb') as torrent_file:
            torrent_file.write(torrent_bytes)
        print(f"Torrent file saved at: {torrent_file_path}")

        return torrent_file_path
    except Exception as e:
        print(f"Error while processing torrent bytes: {e}")
        return None
    

# The function generates pieces from the given file paths
def generate_pieces(file_paths, piece_length):
    pieces = b""
    buffer = b""

    for file_path in file_paths:
        if not os.path.isfile(file_path):
            print(f"File does not exist: {file_path}")
            continue

        # Read the content of each file and append to the buffer
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(piece_length - len(buffer))
                if not data:
                    break

                buffer += data

                # If the buffer is full for a piece, generate the SHA1 hash and append it to the pieces list
                while len(buffer) >= piece_length:
                    piece = buffer[:piece_length]
                    pieces += hashlib.sha1(piece).digest()
                    buffer = buffer[piece_length:]

    # If there is any remaining data in the buffer, generate the SHA1 hash for the leftover part
    if buffer:
        pieces += hashlib.sha1(buffer).digest()

    return pieces

def generate_torrent_file(torrent_manager, tracker_url, torrent_folder_path, input_path, data_folder_path):
    piece_length = PIECE_LENGTH
    files = []
    total_size = 0

    # Define the name for the data
    name = os.path.basename(input_path)

    new_file_paths = []

    data_save_path = os.path.join(data_folder_path, name)

    # **Case 1: Input is a single file**
    if os.path.isfile(input_path):
        # Copy the file directly to data_folder_path
        new_path = os.path.join(data_folder_path, name)
        shutil.copy2(input_path, new_path)
        new_file_paths.append(new_path)
        print(f"File copied: {new_path}")

    # **Case 2: Input is a directory**
    elif os.path.isdir(input_path):
        # Create a new directory inside data_folder_path
        data_copy_path = os.path.join(data_folder_path, name)
        os.makedirs(data_copy_path, exist_ok=True)
        print(f"Directory created: {data_copy_path}")

        for filename in os.listdir(input_path):
            file_path = os.path.join(input_path, filename)
            if os.path.isfile(file_path):
                new_path = os.path.join(data_copy_path, filename)
                shutil.copy2(file_path, new_path)
                new_file_paths.append(new_path)
                print(f"File copied: {new_path}")
            else:
                print(f"Skipped invalid file: {file_path}")

    else:
        print(f"Invalid path: {input_path}")
        return

    # Generate pieces
    pieces = generate_pieces(new_file_paths, piece_length)

    # Generate metadata for each file
    for file_path in new_file_paths:
        file_size = os.path.getsize(file_path)
        total_size += file_size
        path_part = os.path.basename(file_path)
        files.append((file_size, path_part))

    dict_files = [{'length': file_size, 'path': path_part} for file_size, path_part in files]

    # Create metadata for the 'info' section
    info = {
        b'piece length': piece_length,
        b'pieces': pieces,
        b'name': name.encode('utf-8'),
        b'files': [{'length': file_size, 'path': path_part.encode('utf-8')} for file_size, path_part in files]
    }

    # Encode information and generate info_hash
    encoded_info = bencodepy.encode(info)
    info_hash = hashlib.sha1(encoded_info).digest().hex()

    # .torrent data
    torrent_data = {
        b'announce': tracker_url.encode('utf-8'),
        b'info': info
    }

    # Create the folder to save .torrent files
    os.makedirs(torrent_folder_path, exist_ok=True)

    # Define the .torrent file name
    base_name = name
    ext = ".torrent"
    output_path = os.path.join(torrent_folder_path, f"{base_name}{ext}")

    try:
        # Write the .torrent file
        with open(output_path, 'wb') as f:
            f.write(bencodepy.encode(torrent_data))
        print(f".torrent file created successfully: {output_path}")
    except Exception as e:
        print(f"Error while saving .torrent file: {e}")
        return

    # Calculate the number of pieces
    pieces_count = len(pieces) // 20  # Each piece has a SHA-1 hash (20 bytes)

    # Update into torrent_log.json through torrent_manager and set a complete bitfield
    bitfield = [1] * pieces_count  # This peer has all the data, so the bitfield is all 1s
    torrent_manager.add_torrent(
        info_hash,
        piece_size=piece_length,
        pieces_count=pieces_count,
        torrent_save_path=output_path,
        data_save_path=data_save_path,
        bitfield=bitfield
    )

    print(f"Updated information into torrent_log.json for torrent: {info_hash}")

    # Display metadata information
    metadata = torrent_metada(tracker_url, name, total_size, piece_length, pieces, info_hash, dict_files)
    print(metadata)
