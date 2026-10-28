# =====================================================================
# FILE: core/face.py
# NHIỆM VỤ: Nhận dạng khuôn mặt bằng thư viện OpenCV
# KIẾN THỨC: Class, vòng lặp, dictionary, đọc/ghi file, try/except
#            + thư viện mới: OpenCV (cv2), numpy, json
#
# Ý TƯỞNG: Với máy tính, 1 ảnh chỉ là 1 bảng số (numpy array).
#   Ảnh xám 200x200 = 200 hàng x 200 cột, mỗi ô là 1 số từ 0 (đen) đến 255 (trắng).
#
# QUY TRÌNH 3 BƯỚC:
#   1. ĐĂNG KÝ  : chụp >= 3 ảnh mỗi học viên -> cắt khuôn mặt -> lưu data/faces/<Ma_HV>/<số>.jpg
#   2. HUẤN LUYỆN: đọc toàn bộ ảnh đã lưu -> dạy model LBPH -> lưu ra data/face_model.yml
#   3. NHẬN DẠNG : ảnh mới từ camera -> cắt khuôn mặt -> model đoán là ai + "khoảng cách"
#                 khoảng cách càng NHỎ càng GIỐNG; lớn hơn ngưỡng -> "không nhận ra"
#
# Cần cài: python -m pip install opencv-contrib-python
#   (phải là bản "contrib" vì module nhận dạng cv2.face chỉ có trong bản này)
# =====================================================================

import json
import os
import shutil

import numpy as np

from core import config

# Nếu máy chưa cài OpenCV thì chương trình vẫn chạy, chỉ tắt chức năng camera
try:
    import cv2
except ImportError:
    cv2 = None


class NhanDangKhuonMat:
    def __init__(self, thu_muc_anh=None, file_model=None, file_nhan=None):
        # B1: Lưu đường dẫn (không truyền thì lấy mặc định trong config)
        self.thu_muc_anh = thu_muc_anh or config.THU_MUC_KHUON_MAT
        self.file_model = file_model or config.FILE_MODEL
        self.file_nhan = file_nhan or config.FILE_NHAN_MODEL
        os.makedirs(self.thu_muc_anh, exist_ok=True)

        # B2: Model chưa nạp (sẽ nạp khi cần nhận dạng lần đầu)
        self.model = None
        self.thoi_gian_sua_model = None     # dùng để biết file model có bị thay đổi không
        self.bang_nhan = {}                 # {0: "HV001", 1: "HV005", ...}

        # B3: Nạp bộ PHÁT HIỆN khuôn mặt (Haar Cascade, có sẵn trong OpenCV)
        #     Bộ này chỉ biết "chỗ nào trong ảnh là khuôn mặt", chưa biết là AI
        self.bo_phat_hien = None
        if cv2 is not None:
            file_haar = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
            if os.path.exists(file_haar):
                self.bo_phat_hien = cv2.CascadeClassifier(file_haar)

    # =================================================================
    # PHẦN 1: KIỂM TRA MÁY ĐÃ CÀI ĐỦ CHƯA
    # =================================================================
    def co_opencv(self):
        return cv2 is not None

    def co_nhan_dang(self):
        # Bản opencv-python thường KHÔNG có cv2.face -> không nhận dạng được
        return cv2 is not None and hasattr(cv2, "face")

    def tinh_trang(self):
        if not self.co_opencv():
            return "Chưa cài OpenCV. Chạy: python -m pip install opencv-contrib-python"
        if not self.co_nhan_dang():
            return ("Đang dùng opencv-python (thiếu module cv2.face). Gỡ và cài lại: "
                    "python -m pip uninstall opencv-python -y && python -m pip install opencv-contrib-python")
        if self.bo_phat_hien is None:
            return "Không tìm thấy file Haar Cascade, sẽ dùng phần giữa ảnh làm khuôn mặt (kém chính xác)"
        return "OK"

    # =================================================================
    # PHẦN 2: XỬ LÝ ẢNH
    # =================================================================

    # Đổi dữ liệu ảnh (bytes, lấy từ camera hoặc file upload) thành mảng số của OpenCV
    def doc_anh(self, du_lieu_anh):
        mang_byte = np.frombuffer(du_lieu_anh, np.uint8)
        anh = cv2.imdecode(mang_byte, cv2.IMREAD_COLOR)
        if anh is None:
            raise ValueError("Không đọc được ảnh")
        return anh

    # Tìm khuôn mặt LỚN NHẤT trong ảnh xám
    # Output: (x, y, rộng, cao) của khung khuôn mặt, hoặc None nếu không thấy
    def tim_khuon_mat(self, anh_xam):
        if self.bo_phat_hien is not None:
            danh_sach_mat = self.bo_phat_hien.detectMultiScale(
                anh_xam, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
            if len(danh_sach_mat) == 0:
                return None
            # Có nhiều mặt -> lấy mặt có diện tích (rộng x cao) lớn nhất = người đứng gần nhất
            mat_lon_nhat = danh_sach_mat[0]
            for mat in danh_sach_mat:
                if mat[2] * mat[3] > mat_lon_nhat[2] * mat_lon_nhat[3]:
                    mat_lon_nhat = mat
            return mat_lon_nhat

        # Dự phòng khi thiếu Haar Cascade: lấy hình vuông ở giữa ảnh
        cao, rong = anh_xam.shape
        canh = int(min(cao, rong) * 0.7)
        return ((rong - canh) // 2, (cao - canh) // 2, canh, canh)

    # Cắt khuôn mặt và chuẩn hóa
    # Input : ảnh màu (BGR) | Output: (khuôn mặt xám 200x200 hoặc None, ảnh RGB có vẽ khung để hiển thị)
    def cat_khuon_mat(self, anh):
        # B1: Đổi sang ảnh xám (nhận dạng chỉ cần độ sáng, không cần màu)
        anh_xam = cv2.cvtColor(anh, cv2.COLOR_BGR2GRAY)
        # OpenCV lưu màu theo thứ tự BGR, Streamlit hiển thị RGB -> đổi để màu không bị ngược
        anh_hien_thi = cv2.cvtColor(anh, cv2.COLOR_BGR2RGB)

        # B2: Tìm khuôn mặt
        vi_tri = self.tim_khuon_mat(anh_xam)
        if vi_tri is None:
            return None, anh_hien_thi

        # B3: Cắt đúng vùng khuôn mặt, đổi về cùng kích thước 200x200
        x, y, rong, cao = vi_tri
        mat = anh_xam[y:y + cao, x:x + rong]           # cắt mảng giống cắt list
        mat = cv2.resize(mat, config.KICH_THUOC_MAT)

        # B4: Cân bằng sáng -> ảnh chụp tối hay sáng đều trông giống nhau hơn
        mat = cv2.equalizeHist(mat)

        # B5: Vẽ khung xanh quanh khuôn mặt để người dùng thấy
        cv2.rectangle(anh_hien_thi, (x, y), (x + rong, y + cao), (0, 200, 0), 3)
        return mat, anh_hien_thi

    # =================================================================
    # PHẦN 3: ĐĂNG KÝ KHUÔN MẶT
    # =================================================================
    def thu_muc_hoc_vien(self, ma_hv):
        return os.path.join(self.thu_muc_anh, ma_hv)

    # Đếm số ảnh đã đăng ký của 1 học viên
    def so_anh(self, ma_hv):
        thu_muc = self.thu_muc_hoc_vien(ma_hv)
        if not os.path.exists(thu_muc):
            return 0
        return len([ten for ten in os.listdir(thu_muc) if ten.endswith(".jpg")])

    # Thống kê: {"HV001": 5, "HV002": 3, ...}
    def thong_ke_dang_ky(self):
        ket_qua = {}
        for ten in sorted(os.listdir(self.thu_muc_anh)):
            if os.path.isdir(os.path.join(self.thu_muc_anh, ten)):
                ket_qua[ten] = self.so_anh(ten)
        return ket_qua

    # Lưu 1 ảnh đăng ký
    # Input : mã học viên, dữ liệu ảnh | Output: (thanh_cong, thong_bao, anh_hien_thi)
    def dang_ky(self, ma_hv, du_lieu_anh):
        # B1: Đọc ảnh và cắt khuôn mặt
        anh = self.doc_anh(du_lieu_anh)
        mat, anh_hien_thi = self.cat_khuon_mat(anh)
        if mat is None:
            return False, "Không thấy khuôn mặt. Nhìn thẳng camera, đủ sáng, rồi chụp lại.", anh_hien_thi

        # B2: Tạo thư mục riêng cho học viên (nếu chưa có)
        thu_muc = self.thu_muc_hoc_vien(ma_hv)
        os.makedirs(thu_muc, exist_ok=True)

        # B3: Đặt tên file = số tiếp theo (đã có 1.jpg, 2.jpg -> ảnh mới là 3.jpg)
        so_lon_nhat = 0
        for ten in os.listdir(thu_muc):
            ten_khong_duoi = ten.replace(".jpg", "")
            if ten_khong_duoi.isdigit() and int(ten_khong_duoi) > so_lon_nhat:
                so_lon_nhat = int(ten_khong_duoi)
        so_moi = so_lon_nhat + 1

        # B4: Lưu ảnh khuôn mặt
        cv2.imwrite(os.path.join(thu_muc, f"{so_moi}.jpg"), mat)
        return True, f"Đã lưu ảnh {so_moi} của {ma_hv}", anh_hien_thi

    # Xóa toàn bộ ảnh của 1 học viên
    def xoa_anh(self, ma_hv):
        shutil.rmtree(self.thu_muc_hoc_vien(ma_hv), ignore_errors=True)

    # =================================================================
    # PHẦN 4: HUẤN LUYỆN MODEL
    # Output: (thanh_cong, thong_bao)
    # =================================================================
    def huan_luyen(self):
        if not self.co_nhan_dang():
            return False, self.tinh_trang()

        danh_sach_anh = []      # list ảnh khuôn mặt
        danh_sach_nhan = []     # list nhãn số tương ứng với từng ảnh
        bang_nhan = {}          # {0: "HV001", 1: "HV005"} -> model chỉ hiểu số, nên cần bảng tra

        # B1: Duyệt từng học viên đã đăng ký đủ ảnh
        nhan_so = 0
        for ma_hv, so_anh in self.thong_ke_dang_ky().items():
            if so_anh < config.SO_ANH_TOI_THIEU:
                continue                          # chưa đủ ảnh -> bỏ qua học viên này
            bang_nhan[nhan_so] = ma_hv

            # B2: Đọc từng ảnh của học viên này
            thu_muc = self.thu_muc_hoc_vien(ma_hv)
            for ten_file in sorted(os.listdir(thu_muc)):
                anh = cv2.imread(os.path.join(thu_muc, ten_file), cv2.IMREAD_GRAYSCALE)
                if anh is not None:
                    danh_sach_anh.append(cv2.resize(anh, config.KICH_THUOC_MAT))
                    danh_sach_nhan.append(nhan_so)
            nhan_so = nhan_so + 1

        if len(bang_nhan) == 0:
            return False, f"Chưa có học viên nào đủ {config.SO_ANH_TOI_THIEU} ảnh để huấn luyện"

        # B3: Tạo model LBPH và huấn luyện ("dạy" model ảnh nào thuộc nhãn nào)
        model = cv2.face.LBPHFaceRecognizer_create()
        model.train(danh_sach_anh, np.array(danh_sach_nhan, dtype=np.int32))

        # B4: Lưu model và bảng nhãn ra file để lần sau dùng lại
        model.write(self.file_model)
        with open(self.file_nhan, "w", encoding="utf-8") as f:
            json.dump(bang_nhan, f, ensure_ascii=False)

        self.model = None        # buộc nạp lại model mới ở lần nhận dạng sau
        return True, f"Đã huấn luyện {len(danh_sach_anh)} ảnh của {len(bang_nhan)} học viên"

    def da_huan_luyen(self):
        return os.path.exists(self.file_model) and os.path.exists(self.file_nhan)

    # Nạp model từ file (chỉ nạp lại khi file model bị thay đổi, cho nhanh)
    def nap_model(self):
        if not self.da_huan_luyen():
            return None
        thoi_gian_sua = os.path.getmtime(self.file_model)
        if self.model is None or self.thoi_gian_sua_model != thoi_gian_sua:
            self.model = cv2.face.LBPHFaceRecognizer_create()
            self.model.read(self.file_model)
            self.thoi_gian_sua_model = thoi_gian_sua
            with open(self.file_nhan, encoding="utf-8") as f:
                bang = json.load(f)
            # json lưu key dạng chuỗi "0" -> đổi lại thành số 0
            self.bang_nhan = {int(k): v for k, v in bang.items()}
        return self.model

    # =================================================================
    # PHẦN 5: NHẬN DẠNG
    # Input : dữ liệu ảnh từ camera
    # Output: (ma_hv hoặc None, khoang_cach hoặc None, anh_hien_thi, thong_bao)
    # =================================================================
    def nhan_dang(self, du_lieu_anh):
        # B1: Đọc ảnh, cắt khuôn mặt
        anh = self.doc_anh(du_lieu_anh)
        mat, anh_hien_thi = self.cat_khuon_mat(anh)
        if mat is None:
            return None, None, anh_hien_thi, "Không thấy khuôn mặt trong ảnh"

        # B2: Nạp model
        model = self.nap_model()
        if model is None:
            return None, None, anh_hien_thi, "Chưa huấn luyện model. Vào trang Học viên để đăng ký và huấn luyện."

        # B3: Model dự đoán -> trả về (nhãn số, khoảng cách)
        nhan_so, khoang_cach = model.predict(mat)
        ma_hv = self.bang_nhan.get(int(nhan_so))     # đổi nhãn số -> mã học viên

        # B4: So với ngưỡng. Model LUÔN trả về người giống nhất, kể cả khi là người lạ,
        #     nên phải có ngưỡng để loại người lạ
        if ma_hv is None or khoang_cach > config.NGUONG_NHAN_DANG:
            return None, float(khoang_cach), anh_hien_thi, (
                f"Không nhận ra (khoảng cách {khoang_cach:.1f} > ngưỡng {config.NGUONG_NHAN_DANG})")

        return ma_hv, float(khoang_cach), anh_hien_thi, f"Nhận ra {ma_hv} (khoảng cách {khoang_cach:.1f})"
