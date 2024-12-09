<a id="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="">
    <img src="hcmut.png" alt="HCMUT Logo" width="160" height="160">
  </a>

  <h3 align="center">Simple Torrent-like Application (STA)</h3>

  <p align="center">
    Dự án hướng đến  xây dựng một ứng dụng chia sẻ tệp dựa trên giao thức TCP/IP, được thiết kế để hỗ trợ truyền dữ liệu đa hướng (MDDT). Ứng dụng này chủ yếu sẽ được xây dựng và hiện thực dựa trên mô hình BitTorrent của mạng ngang hàng P2P. 
    
  </p>
</div>

<!-- ABOUT MEMBER TEAM-->

- Đề tài: Simple Torrent-like Application (STA)

- Danh sách thành viên:

| STT | Tên thành viên    | Vai trò               | Mã số sinh viên |
| --- | ----------------- | --------------------- | --------------- |
| 1   | Trần Đại Việt     | Tìm hiểu và hiện thực | 2213951         |
| 2   | Trần Đình Tưởng   | Tìm hiểu và hiện thực | 2213892         |
| 3   | Nguyễn Phương Duy | Tìm hiểu và hiện thực | 2210526         |
| 4   | Trần Thành Long   | Tìm hiểu và hiện thực | 2153538         |

### Cách chạy ứng dụng Simple Torrent-like Application (STA)

#### **1. Yêu cầu trước khi chạy**

Trước khi bắt đầu, đảm bảo rằng bạn đã cài đặt các công cụ và thư viện cần thiết:

- **Python 3.x**: Ứng dụng được viết bằng Python, yêu cầu phiên bản Python 3.x.
- **Thư viện Python bổ sung**: Sử dụng lệnh sau để cài đặt các thư viện cần thiết:
  ```bash
  pip install <library_name>
  ```
- **Mạng nội bộ hoặc địa chỉ IP hợp lệ**: Đảm bảo các thiết bị chạy ứng dụng có thể giao tiếp qua mạng.

---

#### **2. Cách chạy Tracker**

Tracker là thành phần trung tâm để quản lý danh sách các Peer trong hệ thống. Để chạy Tracker:

1. Mở một terminal và chạy tệp Python `tracker.py`:
   ```bash
   python tracker.py
   ```
2. Khi Tracker bắt đầu, bạn sẽ thấy thông báo hiển thị địa chỉ IP và cổng của nó (mặc định là `22236`):
   ```
   Tracker HTTP Server started at http://<tracker_ip>:22236
   ```
3. Giữ Tracker hoạt động để các Peer có thể kết nối và trao đổi dữ liệu.

---

#### **3. Cách chạy Peer**

Peer là thành phần để tải và chia sẻ dữ liệu với các thiết bị khác. Thực hiện các bước sau:

1. Mở một terminal và chạy tệp Python `peer.py`:
   ```bash
   python peer.py
   ```
2. Nhập thông tin khi được yêu cầu:

   - Nhập **Peer ID**: Một chuỗi tùy ý để nhận diện Peer.
   - Nhập **Tracker URL**: Địa chỉ của Tracker, ví dụ: `http://192.168.1.5:22236`.

3. Sau khi Peer khởi động, bạn sẽ thấy menu CLI với các lệnh sau:
   ```
   Command options:
     stop                                     - Dừng Peer và ngắt kết nối
     announce_have_data <info_hash>           - Thông báo rằng Peer đã có dữ liệu
     download_torrent_by_info_hash <info_hash>- Tải tệp torrent từ Tracker
     get_peers <info_hash>                    - Lấy danh sách Peer từ Tracker
     update_torrent_log                       - Cập nhật log torrent từ thư mục
     generate_torrent_file <data_file_path>   - Tạo tệp torrent
     download_file <info_hash>                - Bắt đầu tải tệp
     get_torrent_info <info_hash>             - Lấy thông tin tệp torrent
     get_torrent_log                          - Xem log torrent
     help                                     - Hiển thị hướng dẫn
     exit                                     - Thoát chương trình
   ```

---

#### **4. Chức năng chính**

- **Tạo tệp torrent**:
  Sử dụng lệnh:

  ```bash
  generate_torrent_file <data_file_path>
  ```

  Đường dẫn `<data_file_path>` là file bạn muốn chia sẻ.

- **Tải tệp torrent từ Tracker**:
  Sử dụng lệnh:

  ```bash
  download_torrent_by_info_hash <info_hash>
  ```

- **Tải dữ liệu từ Peer**:
  Sử dụng lệnh:

  ```bash
  download_file <info_hash>
  ```

- **Thông báo dữ liệu đã có**:
  Sử dụng lệnh:

  ```bash
  announce_have_data <info_hash>
  ```

- **Lấy danh sách Peer**:
  Sử dụng lệnh:

  ```bash
  get_peers <info_hash>
  ```

- **Dừng Peer**:
  Sử dụng lệnh:
  ```bash
  stop
  ```

---

#### **5. Lưu ý**

- **Thư mục dữ liệu và tệp torrent**:

  - Dữ liệu tải về và tệp torrent được lưu trong các thư mục tự động tạo khi Peer khởi động:
    - Dữ liệu: `<peer_folder>-data-folder`
    - Tệp torrent: `<peer_folder>-torrent-folder`

- **Cổng giao tiếp (Port)**:
  Peer giao tiếp qua các cổng từ `6881` đến `6889`. Hãy đảm bảo các cổng này được mở trên tường lửa.

- **Chạy nhiều Peer**:
  Bạn có thể chạy nhiều Peer trên các máy khác nhau hoặc trên cùng một máy (nhưng phải sử dụng cổng khác nhau).

---

Bằng cách làm theo hướng dẫn trên, bạn có thể thiết lập và chạy hệ thống Simple Torrent-like Application (STA) để chia sẻ và tải dữ liệu trong mạng ngang hàng.

#### **Các tài liệu chi tiết liên quan tới việc hiện thực hệ thống**

- **Các Diagram mô tả kiến trúc hệ thống hay các Class Diagram:**  
  [Xem chi tiết tại đây](https://drive.google.com/file/d/1eCU3qB3yYAlcBpjPPsRoev0MNw6BzA1l/view?usp=sharing)

- **Usecase Diagram hay Activity Diagram:**  
  [Xem chi tiết tại đây](https://lucid.app/lucidchart/96a93da6-c995-4f48-a6e4-827dfd6b920a/edit?viewport_loc=-1898%2C-1364%2C6381%2C3401%2C0_0&invitationId=inv_7a6a9ebf-271d-4099-b03c-be08d298b08d)

- **Video Demo hoạt động của ứng dụng:**  
  [Xem tại đây](https://youtu.be/GrsQM_SwOYQ)

- **Báo cáo chi tiết của bài tập lớn:**  
  [Xem chi tiết tại đây](https://lucid.app/lucidchart/96a93da6-c995-4f48-a6e4-827dfd6b920a/edit?viewport_loc=-1898%2C-1364%2C6381%2C3401%2C0_0&invitationId=inv_7a6a9ebf-271d-4099-b03c-be08d298b08d)

- **Tài liệu hiện thực:**  
  Một số tài liệu hiện thực sẽ được cung cấp tại thư mục `\docs`

---
