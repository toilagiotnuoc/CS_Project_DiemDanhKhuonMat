# =====================================================================
# FILE: core/models.py
# NHIỆM VỤ: Định nghĩa 2 ĐỐI TƯỢNG chính của chương trình
#   - HocVien : thông tin của 1 học viên
#   - BuoiHoc : thông tin của 1 buổi học + các quy tắc giờ giấc của buổi đó
# KIẾN THỨC: Class, __init__, self, thuộc tính (attribute), phương thức (method),
#            try/except, vòng lặp for, thư viện datetime
#
# Tư duy OOP (như bài học):
#   1. Đối tượng là gì?   -> Học viên, Buổi học
#   2. Thuộc tính là gì?  -> Học viên: mã, họ tên, email...  | Buổi học: ngày, giờ bắt đầu, giờ kết thúc...
#   3. Hành động là gì?   -> Buổi học: kiểm tra đang mở check-in hay chưa, tạo tên hiển thị
# =====================================================================

from datetime import datetime, timedelta

from core import config


# ---------------------------------------------------------------------
# HÀM PHỤ 1: Đọc giờ
# Input : giờ ở nhiều dạng khác nhau, ví dụ "19:00", "19:00:00"
# Output: đối tượng time của Python (ví dụ time(19, 0))
# Lý do cần hàm này: Excel có lúc trả về "19:00", có lúc "19:00:00", có lúc là kiểu time
# ---------------------------------------------------------------------
def doc_gio(gia_tri):
    # Trường hợp 1: đã là kiểu datetime -> lấy phần giờ
    if isinstance(gia_tri, datetime):
        return gia_tri.time()

    # Trường hợp 2: đã là kiểu time -> dùng luôn (kiểu time có thuộc tính hour)
    if hasattr(gia_tri, "hour") and not isinstance(gia_tri, str):
        return gia_tri

    # Trường hợp 3: là chuỗi -> thử từng định dạng, định dạng nào đúng thì trả về
    chuoi = str(gia_tri).strip()
    for dinh_dang in ["%H:%M", "%H:%M:%S"]:
        try:
            return datetime.strptime(chuoi, dinh_dang).time()
        except ValueError:
            continue          # sai định dạng này -> thử định dạng tiếp theo

    # Thử hết mà không được -> báo lỗi
    raise ValueError(f"Giờ không hợp lệ: {gia_tri}")


# ---------------------------------------------------------------------
# HÀM PHỤ 2: Đọc ngày
# Input : ngày ở nhiều dạng: "2026-09-01", "01/09/2026", kiểu date, kiểu Timestamp của pandas
# Output: đối tượng date của Python
# ---------------------------------------------------------------------
def doc_ngay(gia_tri):
    # Kiểu Timestamp của pandas -> đổi sang datetime trước
    if hasattr(gia_tri, "to_pydatetime"):
        gia_tri = gia_tri.to_pydatetime()

    # Kiểu datetime -> lấy phần ngày
    if isinstance(gia_tri, datetime):
        return gia_tri.date()

    # Kiểu date -> dùng luôn
    if hasattr(gia_tri, "year") and not isinstance(gia_tri, str):
        return gia_tri

    # Kiểu chuỗi -> lấy 10 ký tự đầu (bỏ phần giờ nếu có) rồi thử từng định dạng
    chuoi = str(gia_tri).strip()[:10]
    for dinh_dang in ["%Y-%m-%d", "%d/%m/%Y"]:
        try:
            return datetime.strptime(chuoi, dinh_dang).date()
        except ValueError:
            continue

    raise ValueError(f"Ngày không hợp lệ: {gia_tri}")


# =====================================================================
# CLASS 1: HocVien
# =====================================================================
class HocVien:
    def __init__(self, ma_hv, ho_ten, gioi_tinh="", ngay_sinh="", email="", sdt="", lop=""):
        # self.xxx là nơi object LƯU dữ liệu, xxx là dữ liệu được TRUYỀN VÀO
        self.ma_hv = ma_hv
        self.ho_ten = ho_ten
        self.gioi_tinh = gioi_tinh
        self.ngay_sinh = ngay_sinh
        self.email = email
        self.sdt = sdt          # lưu dạng chuỗi để giữ số 0 ở đầu
        self.lop = lop

    # Method: đổi object thành dictionary (để ghi vào DataFrame / Excel)
    # Key của dictionary = tên cột trong file Excel
    def to_dict(self):
        return {
            "Ma_HV": self.ma_hv,
            "Ho_ten": self.ho_ten,
            "Gioi_tinh": self.gioi_tinh,
            "Ngay_sinh": self.ngay_sinh,
            "Email": self.email,
            "SDT": self.sdt,
            "Lop": self.lop,
        }


# =====================================================================
# CLASS 2: BuoiHoc
# =====================================================================
class BuoiHoc:
    def __init__(self, ma_buoi, lop, ngay, gio_bat_dau, gio_ket_thuc, chu_de="", phong=""):
        # B1: Lưu các thông tin được truyền vào
        self.ma_buoi = ma_buoi
        self.lop = lop
        self.ngay = ngay                    # kiểu date, ví dụ 2026-09-01
        self.gio_bat_dau = gio_bat_dau      # kiểu time, ví dụ 19:00
        self.gio_ket_thuc = gio_ket_thuc    # kiểu time, ví dụ 21:30
        self.chu_de = chu_de
        self.phong = phong

        # B2: Tính sẵn một số thuộc tính dùng nhiều lần
        # datetime.combine(ngày, giờ) = ghép ngày + giờ thành 1 mốc thời gian đầy đủ
        self.bat_dau = datetime.combine(ngay, gio_bat_dau)     # 2026-09-01 19:00
        self.ket_thuc = datetime.combine(ngay, gio_ket_thuc)   # 2026-09-01 21:30

        # Thời lượng buổi học (phút) = (kết thúc - bắt đầu) đổi ra giây rồi chia 60
        self.thoi_luong_phut = (self.ket_thuc - self.bat_dau).total_seconds() / 60

    # Method: buổi này có đang mở check-in tại thời điểm "luc" không?
    # Quy tắc: từ 30 phút trước giờ học -> đến hết giờ học
    def mo_check_in(self, luc):
        som_nhat = self.bat_dau - timedelta(minutes=config.MO_CHECK_IN_TRUOC_PHUT)
        muon_nhat = self.ket_thuc
        return som_nhat <= luc <= muon_nhat        # True hoặc False

    # Method: buổi này có đang mở check-out tại thời điểm "luc" không?
    # Quy tắc: từ lúc bắt đầu học -> đến 60 phút sau giờ kết thúc
    def mo_check_out(self, luc):
        som_nhat = self.bat_dau
        muon_nhat = self.ket_thuc + timedelta(minutes=config.DONG_CHECK_OUT_SAU_PHUT)
        return som_nhat <= luc <= muon_nhat

    # Method: tạo tên hiển thị trên giao diện
    # Ví dụ: "B05 · 15/09/2026 19:00–21:30 · Hàm, chia để trị"
    def nhan(self):
        ngay = self.ngay.strftime("%d/%m/%Y")
        bat_dau = self.gio_bat_dau.strftime("%H:%M")
        ket_thuc = self.gio_ket_thuc.strftime("%H:%M")
        return f"{self.ma_buoi} · {ngay} {bat_dau}–{ket_thuc} · {self.chu_de}"


# ---------------------------------------------------------------------
# HÀM: Tạo object BuoiHoc từ 1 dòng dữ liệu Excel
# Input : dong = dictionary 1 dòng của file lich_hoc.xlsx
#         ví dụ {"Ma_buoi": "B01", "Ngay": "2026-09-01", "Gio_bat_dau": "19:00", ...}
# Output: object BuoiHoc
# ---------------------------------------------------------------------
def tao_buoi_hoc_tu_dong(dong):
    return BuoiHoc(
        ma_buoi=str(dong["Ma_buoi"]),
        lop=str(dong.get("Lop", "")),
        ngay=doc_ngay(dong["Ngay"]),
        gio_bat_dau=doc_gio(dong["Gio_bat_dau"]),
        gio_ket_thuc=doc_gio(dong["Gio_ket_thuc"]),
        chu_de=str(dong.get("Chu_de", "")),
        phong=str(dong.get("Phong", "")),
    )
