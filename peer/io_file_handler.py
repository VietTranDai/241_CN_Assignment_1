import os
from threading import *
from torrent_log import  *

"""
    General file input and output class, provides read and write data
"""
class file_io():
    def __init__(self, file_path):
        """
        Initializes the file descriptor and lock for thread-safe file operations.
        :param file_path: Path to the file to be managed.
        """
        O_BINARY = getattr(os, 'O_BINARY', 0)  # Default to 0 on platforms like Linux/macOS
        self.file_descriptor = os.open(file_path, os.O_RDWR | os.O_CREAT | O_BINARY)
        os.lseek(self.file_descriptor, 0, os.SEEK_SET)
        self.file_lock = Lock()  # Lock for thread-safe file operations

    def write(self, byte_stream):
        with self.file_lock:
            os.write(self.file_descriptor, byte_stream)

    def read(self, buffer_size):
        with self.file_lock:
            return os.read(self.file_descriptor, buffer_size)

    def write_null_values(self, data_size):
        max_write_buffer = (2 ** 14)
        self.move_descriptor_position(0)
        while data_size > 0:
            with self.file_lock:
                if data_size >= max_write_buffer:
                    data = b'\x00' * max_write_buffer
                    data_size -= max_write_buffer
                else:
                    data = b'\x00' * data_size
                    data_size = 0
                os.write(self.file_descriptor, data)

    def move_descriptor_position(self, index_position):
        with self.file_lock:
            os.lseek(self.file_descriptor, index_position, os.SEEK_SET)

"""
    The peers use this class object to write pieces downloaded into file
"""
class torrent_shared_file_handler():
    def __init__(self, torrent_metadata, download_dir):
        self.torrent_metadata = torrent_metadata
        self.download_dir = download_dir

        self.file_handlers = []
        self.create_file_handlers()

        self.piece_size = torrent_metadata.piece_length
        self.total_size = torrent_metadata.size

    def create_file_handlers(self):
        current_offset = 0

        if len(self.torrent_metadata.files) == 1:
            file_info = self.torrent_metadata.files[0]
            file_path = os.path.join(self.download_dir, self.torrent_metadata.name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            file_handler = {
                'length': file_info['length'],
                'file_io': file_io(file_path),
                'offset': current_offset
            }
            self.file_handlers.append(file_handler)

        else:
            base_folder = os.path.join(self.download_dir, self.torrent_metadata.name)
            os.makedirs(base_folder, exist_ok=True)

            for file_info in self.torrent_metadata.files:
                file_path = os.path.join(base_folder, file_info['path'])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                file_handler = {
                    'length': file_info['length'],
                    'file_io': file_io(file_path),
                    'offset': current_offset
                }
                self.file_handlers.append(file_handler)
                current_offset += file_info['length']

    def write_block(self, piece_message):
        piece_index = piece_message.piece_index
        block_offset = piece_message.block_offset
        data_block = piece_message.block

        global_offset = piece_index * self.piece_size + block_offset
        remaining_data = data_block

        try:
            for file_handler in self.file_handlers:
                file_start = file_handler['offset']
                file_end = file_start + file_handler['length']

                if file_start <= global_offset < file_end:
                    file_io_obj = file_handler['file_io']
                    file_offset = global_offset - file_start

                    bytes_to_write = min(len(remaining_data), file_end - global_offset)

                    file_io_obj.move_descriptor_position(file_offset)
                    file_io_obj.write(remaining_data[:bytes_to_write])

                    remaining_data = remaining_data[bytes_to_write:]
                    global_offset += bytes_to_write

                    if not remaining_data:
                        break

            if remaining_data:
                print(f"Error: Unable to write complete block {piece_index}:{block_offset}. Remaining {len(remaining_data)} bytes.")
        except Exception as e:
            print(f"Error while writing block: {e}")

    def read_block(self, piece_index, block_offset, block_size):
        global_offset = piece_index * self.piece_size + block_offset
        remaining_size = block_size
        data_block = b""

        try:
            for file_handler in self.file_handlers:
                file_start = file_handler['offset']
                file_end = file_start + file_handler['length']

                if file_start <= global_offset < file_end:
                    file_io_obj = file_handler['file_io']
                    file_offset = global_offset - file_start

                    bytes_to_read = min(remaining_size, file_end - global_offset)

                    file_io_obj.move_descriptor_position(file_offset)
                    data_block += file_io_obj.read(bytes_to_read)

                    remaining_size -= bytes_to_read
                    global_offset += bytes_to_read

                    if remaining_size == 0:
                        break

            if remaining_size > 0:
                print(f"Error: Unable to read complete block {piece_index}:{block_offset}. Missing {remaining_size} bytes.")
        except Exception as e:
            print(f"Error while reading block: {e}")

        return data_block

    def initialize_for_download(self):
        for file_handler in self.file_handlers:
            file_io_obj = file_handler['file_io']
            file_length = file_handler['length']

            file_io_obj.write_null_values(file_length)
            print(f"Initialized file with null data: {file_io_obj.file_descriptor}")

    def close_file_handlers(self):
        for file_handler in self.file_handlers:
            os.close(file_handler['file_io'].file_descriptor)
            print(f"Closed file: {file_handler['file_io'].file_descriptor}")