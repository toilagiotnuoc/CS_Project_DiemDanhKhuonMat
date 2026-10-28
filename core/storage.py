# =====================================================================
# FILE: core/storage.py
# NHIỆM VỤ: Đọc và ghi 3 file Excel của chương trình
#   - hoc_vien.xlsx  : danh sách học viên
#   - lich_hoc.xlsx  : lịch học
#   - diem_danh.xlsx : mỗi dòng = 1 lượt check-in / check-out
# =====================================================================

import os

import pandas as pd

from core import config
from core.models import tao_buoi_hoc_tu_dong

# Danh sách cột của từng file (đúng thứ tự)
COT_HOC_VIEN = ["Ma_HV", "Ho_ten", "Gioi_tinh", "Ngay_sinh", "Email", "SDT", "Lop"]
COT_LICH_HOC = ["Ma_buoi", "Lop", "Ngay", "Gio_bat_dau", "Gio_ket_thuc", "Chu_de", "Phong"]
COT_DIEM_DANH = ["Ma_buoi", "Ma_HV", "Check_in", "Check_out", "Phuong_thuc_in",
                 "Phuong_thuc_out", "Khoang_cach_nhan_dang", "Ghi_chu"]


class QuanLyDuLieu:
    def __init__(self, thu_muc_data=None):
        # Nếu không truyền thư mục thì dùng thư mục mặc định trong config
        if thu_muc_data is None:
            thu_muc_data = config.THU_MUC_DATA
        self.thu_muc_data = thu_muc_data

        # Tạo thư mục data nếu chưa có
        os.makedirs(self.thu_muc_data, exist_ok=True)

        # Đường dẫn đầy đủ tới 3 file
        self.file_hoc_vien = os.path.join(thu_muc_data, "hoc_vien.xlsx")
        self.file_lich_hoc = os.path.join(thu_muc_data, "lich_hoc.xlsx")
        self.file_diem_danh = os.path.join(thu_muc_data, "diem_danh.xlsx")

    # -----------------------------------------------------------------
    # HÀM DÙNG CHUNG: đọc 1 file Excel
    # Input : đường dẫn file, danh sách cột, kiểu dữ liệu từng cột (nếu cần)
    # Output: DataFrame có đúng các cột yêu cầu
    # -----------------------------------------------------------------
    def doc_file(self, duong_dan, danh_sach_cot, kieu_du_lieu=None):
        # B1: Chưa có file -> trả về bảng rỗng (đúng tên cột), không báo lỗi
        if not os.path.exists(duong_dan):
            return pd.DataFrame(columns=danh_sach_cot)

        # B2: Đọc file Excel
        df = pd.read_excel(duong_dan, dtype=kieu_du_lieu)

        # B3: File thiếu cột nào thì thêm cột đó (để rỗng)
        for cot in danh_sach_cot:
            if cot not in df.columns:
                df[cot] = None

        # B4: Chỉ lấy đúng các cột cần, đúng thứ tự
        return df[danh_sach_cot]

    # -----------------------------------------------------------------
    # HÀM DÙNG CHUNG: ghi DataFrame ra file Excel
    # -----------------------------------------------------------------
    def ghi_file(self, df, duong_dan, ten_sheet):
        df.to_excel(duong_dan, sheet_name=ten_sheet, index=False)   # index=False: không ghi cột 0,1,2...

    # =================================================================
    # PHẦN 1: HỌC VIÊN
    # =================================================================
    def doc_hoc_vien(self):
        # Ma_HV, SDT, Ngay_sinh đọc dạng chuỗi (str) -> SĐT không bị mất số 0 ở đầu
        df = self.doc_file(self.file_hoc_vien, COT_HOC_VIEN,
                           kieu_du_lieu={"Ma_HV": str, "SDT": str, "Ngay_sinh": str})
        return df.fillna("")          # ô trống -> chuỗi rỗng

    def luu_hoc_vien(self, df):
        self.ghi_file(df[COT_HOC_VIEN], self.file_hoc_vien, "Hoc vien")

    # Thêm 1 học viên mới
    # Input : object HocVien | Output: không có (lỗi thì raise ValueError)
    def them_hoc_vien(self, hoc_vien):
        # B1: Đọc danh sách cũ
        df = self.doc_hoc_vien()

        # B2: Kiểm tra mã học viên đã tồn tại chưa
        if hoc_vien.ma_hv in df["Ma_HV"].values:
            raise ValueError(f"Mã học viên {hoc_vien.ma_hv} đã tồn tại")

        # B3: Tạo 1 dòng mới từ dictionary rồi nối vào bảng cũ
        dong_moi = pd.DataFrame([hoc_vien.to_dict()])
        df = pd.concat([df, dong_moi], ignore_index=True)

        # B4: Lưu lại
        self.luu_hoc_vien(df)

    # Xóa học viên theo mã: giữ lại những dòng có mã KHÁC mã cần xóa
    def xoa_hoc_vien(self, ma_hv):
        df = self.doc_hoc_vien()
        df = df[df["Ma_HV"] != ma_hv]
        self.luu_hoc_vien(df)

    # Tạo dictionary tra cứu nhanh: {"HV001": "Hoàng Thanh Mai", ...}
    def ten_hoc_vien(self):
        df = self.doc_hoc_vien()
        # zip ghép 2 cột thành từng cặp (mã, tên) -> dict biến thành dictionary
        return dict(zip(df["Ma_HV"], df["Ho_ten"]))

    # =================================================================
    # PHẦN 2: LỊCH HỌC
    # =================================================================
    def doc_lich_hoc(self):
        df = self.doc_file(self.file_lich_hoc, COT_LICH_HOC,
                           kieu_du_lieu={"Ma_buoi": str, "Gio_bat_dau": str, "Gio_ket_thuc": str})
        if df.empty:
            return df

        # Làm sạch dữ liệu
        df["Lop"] = df["Lop"].fillna("")
        df["Chu_de"] = df["Chu_de"].fillna("")
        df["Phong"] = df["Phong"].fillna("")
        df["Ngay"] = pd.to_datetime(df["Ngay"], errors="coerce")   # ngày sai định dạng -> NaT
        df = df.dropna(subset=["Ngay"])                             # bỏ dòng ngày bị lỗi

        # Sắp xếp theo ngày, rồi theo giờ bắt đầu
        df = df.sort_values(["Ngay", "Gio_bat_dau"])
        return df.reset_index(drop=True)

    def luu_lich_hoc(self, df):
        df = df[COT_LICH_HOC].copy()
        df["Ngay"] = pd.to_datetime(df["Ngay"]).dt.date      # chỉ lưu ngày, bỏ phần giờ 00:00:00
        self.ghi_file(df, self.file_lich_hoc, "Lich hoc")

    # Trả về list các object BuoiHoc (mỗi dòng Excel -> 1 object)
    def danh_sach_buoi(self):
        df = self.doc_lich_hoc()
        # to_dict("records") biến DataFrame thành list các dictionary, mỗi dòng 1 dictionary
        danh_sach_dong = df.to_dict("records")
        return [tao_buoi_hoc_tu_dong(dong) for dong in danh_sach_dong]

    # Tìm 1 buổi theo mã (tìm kiếm tuyến tính: thấy là trả về ngay)
    def tim_buoi(self, ma_buoi):
        for buoi in self.danh_sach_buoi():
            if buoi.ma_buoi == ma_buoi:
                return buoi
        return None             # duyệt hết mà không thấy

    # Thêm 1 buổi học mới
    # Input : object BuoiHoc
    def them_buoi(self, buoi):
        df = self.doc_lich_hoc()
        if buoi.ma_buoi in df["Ma_buoi"].values:
            raise ValueError(f"Mã buổi {buoi.ma_buoi} đã tồn tại")

        dong_moi = {
            "Ma_buoi": buoi.ma_buoi,
            "Lop": buoi.lop,
            "Ngay": pd.Timestamp(buoi.ngay),
            "Gio_bat_dau": buoi.gio_bat_dau.strftime("%H:%M"),
            "Gio_ket_thuc": buoi.gio_ket_thuc.strftime("%H:%M"),
            "Chu_de": buoi.chu_de,
            "Phong": buoi.phong,
        }
        df = pd.concat([df, pd.DataFrame([dong_moi])], ignore_index=True)
        self.luu_lich_hoc(df)

    # =================================================================
    # PHẦN 3: ĐIỂM DANH
    # =================================================================
    def doc_diem_danh(self):
        df = self.doc_file(self.file_diem_danh, COT_DIEM_DANH,
                           kieu_du_lieu={"Ma_buoi": str, "Ma_HV": str})
        # Đổi 2 cột giờ vào/ra sang kiểu ngày giờ để tính toán được
        df["Check_in"] = pd.to_datetime(df["Check_in"], errors="coerce")
        df["Check_out"] = pd.to_datetime(df["Check_out"], errors="coerce")
        return df

    def luu_diem_danh(self, df):
        self.ghi_file(df[COT_DIEM_DANH], self.file_diem_danh, "Diem danh")
