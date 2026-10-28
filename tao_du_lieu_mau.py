# =====================================================================
# FILE: tao_du_lieu_mau.py
# NHIỆM VỤ: Tạo dữ liệu mẫu để chạy thử 
#   - 20 học viên (HV001 -> HV020)
#   - 20 buổi học vào Thứ 3 và Thứ 5, từ 01/09/2026 (B01 -> B20)
#   - Dữ liệu điểm danh cho các buổi ĐÃ KẾT THÚC tính đến lúc chạy file
# =====================================================================

import os
import random
from datetime import date, datetime, timedelta

import pandas as pd

from core import config
from core.storage import QuanLyDuLieu

# Cố định bộ sinh số ngẫu nhiên -> lần nào chạy cũng ra cùng một bộ tên, cùng người vắng
random.seed(17)

# ---------------------------------------------------------------------
# CÁC THÔNG SỐ CỦA DỮ LIỆU MẪU
# ---------------------------------------------------------------------
LOP = "CSDATA17"
NGAY_BAT_DAU = date(2026, 9, 1) 
SO_BUOI = 20
SO_HOC_VIEN = 20
GIO_BAT_DAU = "19:00"
GIO_KET_THUC = "21:30"

CHU_DE = [
    "Giới thiệu Python, biến, IPO", "If / elif / else, openpyxl", "List, tuple, vòng lặp for",
    "Vòng lặp while, đọc Excel", "Hàm, chia để trị", "Thuật toán tìm kiếm, sắp xếp",
    "Cập nhật Excel, Bubble Sort", "Dictionary, OOP", "Class: Word -> Excel",
    "Streamlit cơ bản", "Streamlit form & layout", "Pandas: đọc, lọc, làm sạch",
    "Pandas: groupby, merge", "Matplotlib", "Seaborn & EDA", "Data pipeline",
    "Google Sheet API", "Gemini / OpenAI API", "RAG chatbot", "Bảo vệ đồ án",
]

HO = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Võ", "Đặng", "Bùi", "Đỗ", "Huỳnh"]
DEM_NAM = ["Văn", "Minh", "Quốc", "Gia", "Đức"]
TEN_NAM = ["An", "Bảo", "Huy", "Khoa", "Long", "Nam", "Phúc", "Tuấn", "Vinh", "Đạt"]
DEM_NU = ["Thị", "Ngọc", "Thanh", "Mai", "Thu"]
TEN_NU = ["Anh", "Chi", "Hà", "Linh", "Mai", "Ngân", "Quỳnh", "Trang", "Vy", "Yến"]


# ---------------------------------------------------------------------
# HÀM 1: Tạo danh sách học viên
# Output: DataFrame 20 dòng
# ---------------------------------------------------------------------
def tao_hoc_vien():
    danh_sach = []           # list chứa các dictionary, mỗi dictionary = 1 học viên
    ten_da_dung = set()      # set để kiểm tra trùng tên (set không chứa phần tử trùng)

    for i in range(1, SO_HOC_VIEN + 1):
        # B1: Ghép ngẫu nhiên Họ + Đệm + Tên, trùng thì ghép lại
        while True:
            la_nam = random.random() < 0.5            # 50% nam, 50% nữ
            if la_nam:
                ho_ten = f"{random.choice(HO)} {random.choice(DEM_NAM)} {random.choice(TEN_NAM)}"
            else:
                ho_ten = f"{random.choice(HO)} {random.choice(DEM_NU)} {random.choice(TEN_NU)}"
            if ho_ten not in ten_da_dung:
                ten_da_dung.add(ho_ten)
                break                                 # tên mới -> dừng vòng while

        # B2: Ngày sinh và số điện thoại ngẫu nhiên
        ngay_sinh = date(random.randint(1990, 2005), random.randint(1, 12), random.randint(1, 28))
        so_dien_thoai = "09"
        for _ in range(8):
            so_dien_thoai = so_dien_thoai + random.choice("0123456789")

        # B3: Thêm học viên vào list
        danh_sach.append({
            "Ma_HV": f"HV{i:03d}",                   # :03d -> đệm số 0 cho đủ 3 chữ số: 1 -> 001
            "Ho_ten": ho_ten,
            "Gioi_tinh": "Nam" if la_nam else "Nữ",
            "Ngay_sinh": ngay_sinh.strftime("%d/%m/%Y"),
            "Email": f"hv{i:03d}@example.com",        # email giả, không phải người thật
            "SDT": so_dien_thoai,
            "Lop": LOP,
        })
    return pd.DataFrame(danh_sach)


# ---------------------------------------------------------------------
# HÀM 2: Tạo lịch học
# Output: DataFrame 20 buổi (Thứ 3 và Thứ 5)
# ---------------------------------------------------------------------
def tao_lich_hoc():
    danh_sach = []
    ngay = NGAY_BAT_DAU

    # Tăng từng ngày một, gặp Thứ 3 hoặc Thứ 5 thì thêm 1 buổi, đủ 20 buổi thì dừng
    while len(danh_sach) < SO_BUOI:
        # weekday(): Thứ 2 = 0, Thứ 3 = 1, ..., Chủ nhật = 6
        if ngay.weekday() == 1 or ngay.weekday() == 3:
            so_thu_tu = len(danh_sach) + 1
            danh_sach.append({
                "Ma_buoi": f"B{so_thu_tu:02d}",
                "Lop": LOP,
                "Ngay": pd.Timestamp(ngay),
                "Gio_bat_dau": GIO_BAT_DAU,
                "Gio_ket_thuc": GIO_KET_THUC,
                "Chu_de": CHU_DE[so_thu_tu - 1],
                "Phong": "P.301",
            })
        ngay = ngay + timedelta(days=1)
    return pd.DataFrame(danh_sach)


# ---------------------------------------------------------------------
# HÀM 3: Tạo dữ liệu điểm danh
# Input : bảng học viên, bảng lịch học, thời điểm hiện tại
# Output: DataFrame điểm danh (chỉ cho các buổi đã kết thúc)
# ---------------------------------------------------------------------
def tao_diem_danh(hoc_vien, lich, den_luc):
    # B1: Gán cho mỗi học viên một "kiểu đi học" để số liệu thống kê có ý nghĩa
    kieu = {}
    for ma in hoc_vien["Ma_HV"]:
        kieu[ma] = "chăm"
    for ma in ["HV004", "HV011", "HV017"]:
        kieu[ma] = "hay vắng"
    for ma in ["HV007", "HV014"]:
        kieu[ma] = "hay trễ"
    kieu["HV019"] = "hay về sớm"

    # Xác suất vắng của từng kiểu (0.35 = khoảng 35% số buổi)
    xac_suat_vang = {"chăm": 0.05, "hay vắng": 0.35, "hay trễ": 0.08, "hay về sớm": 0.08}

    danh_sach = []
    # B2: Vòng lặp lồng nhau: mỗi buổi x mỗi học viên
    for buoi in lich.to_dict("records"):
        ngay = buoi["Ngay"].date()
        bat_dau = datetime.combine(ngay, datetime.strptime(buoi["Gio_bat_dau"], "%H:%M").time())
        ket_thuc = datetime.combine(ngay, datetime.strptime(buoi["Gio_ket_thuc"], "%H:%M").time())

        if ket_thuc > den_luc:
            continue                  # buổi chưa học xong -> không tạo điểm danh

        for ma in hoc_vien["Ma_HV"]:
            k = kieu[ma]

            # B3: Vắng thì KHÔNG tạo dòng điểm danh nào
            if random.random() < xac_suat_vang[k]:
                continue

            # B4: Số phút trễ (số âm = đến sớm) và số phút về sớm
            if k == "hay trễ" and random.random() < 0.6:
                phut_tre = random.randint(16, 45)
            else:
                phut_tre = random.randint(-20, 8)

            if k == "hay về sớm" and random.random() < 0.6:
                phut_som = random.randint(20, 60)
            else:
                phut_som = random.randint(-10, 5)

            check_in = bat_dau + timedelta(minutes=phut_tre, seconds=random.randint(0, 59))
            check_out = ket_thuc - timedelta(minutes=phut_som, seconds=random.randint(0, 59))

            # B5: Khoảng 3% số lượt quên check-out, 10% điểm danh thủ công
            quen_check_out = random.random() < 0.03
            if random.random() < 0.9:
                phuong_thuc = "camera"
            else:
                phuong_thuc = "thu_cong"

            danh_sach.append({
                "Ma_buoi": buoi["Ma_buoi"],
                "Ma_HV": ma,
                "Check_in": check_in,
                "Check_out": None if quen_check_out else check_out,
                "Phuong_thuc_in": phuong_thuc,
                "Phuong_thuc_out": None if quen_check_out else phuong_thuc,
                "Khoang_cach_nhan_dang": round(random.uniform(35, 60), 1) if phuong_thuc == "camera" else None,
                "Ghi_chu": "",
            })
    return pd.DataFrame(danh_sach)


# ---------------------------------------------------------------------
# HÀM CHÍNH
# ---------------------------------------------------------------------
def main():
    du_lieu = QuanLyDuLieu()

    # B1: Tạo dữ liệu mẫu
    hoc_vien = tao_hoc_vien()
    lich = tao_lich_hoc()
    diem_danh = tao_diem_danh(hoc_vien, lich, den_luc=datetime.now())

    # B2: Giữ lại dữ liệu tự thêm
    hv_cu = du_lieu.doc_hoc_vien()
    hv_tu_them = hv_cu[~hv_cu["Ma_HV"].isin(hoc_vien["Ma_HV"])]
    lich_cu = du_lieu.doc_lich_hoc()
    lich_tu_them = lich_cu[~lich_cu["Ma_buoi"].isin(lich["Ma_buoi"])] if not lich_cu.empty else lich_cu
    dd_cu = du_lieu.doc_diem_danh()
    dd_tu_them = dd_cu[(~dd_cu["Ma_HV"].isin(hoc_vien["Ma_HV"])) | (dd_cu["Ma_buoi"].isin(lich_tu_them["Ma_buoi"]))]

    if len(hv_tu_them) > 0:
        hoc_vien = pd.concat([hoc_vien, hv_tu_them], ignore_index=True)
    if len(lich_tu_them) > 0:
        lich = pd.concat([lich, lich_tu_them], ignore_index=True)
    if len(dd_tu_them) > 0:
        diem_danh = pd.concat([diem_danh, dd_tu_them], ignore_index=True)

    # B3: Lưu ra 3 file Excel
    du_lieu.luu_hoc_vien(hoc_vien)
    du_lieu.luu_lich_hoc(lich)
    du_lieu.luu_diem_danh(diem_danh)
    os.makedirs(config.THU_MUC_KHUON_MAT, exist_ok=True)

    print(f"Đã tạo {len(hoc_vien)} học viên  -> {du_lieu.file_hoc_vien}")
    print(f"Đã tạo {len(lich)} buổi học      -> {du_lieu.file_lich_hoc}")
    print(f"Đã tạo {len(diem_danh)} lượt điểm danh -> {du_lieu.file_diem_danh}")
    if len(hv_tu_them) > 0 or len(lich_tu_them) > 0:
        print(f"(Đã giữ lại {len(hv_tu_them)} học viên và {len(lich_tu_them)} buổi bạn tự thêm)")


# Chỉ chạy main() khi chạy trực tiếp file này (python tao_du_lieu_mau.py),
# còn khi file khác import thì không tự chạy
if __name__ == "__main__":
    main()
