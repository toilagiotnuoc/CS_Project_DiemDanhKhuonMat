# =====================================================================
# FILE: core/attendance.py
# NHIỆM VỤ: Xử lý nghiệp vụ điểm danh
#   1. Check-in / check-out (có kiểm tra lỗi)
#   2. Xác định trạng thái từng lượt: Có mặt / Đi trễ / Về sớm / Vắng...
#   3. Thống kê chuyên cần theo học viên và theo buổi, tìm người cần cảnh báo
# KIẾN THỨC: Class, if/elif/else, toán tử so sánh, and/or,
#            pandas: merge, apply, groupby, isin, loc
#
# Mô hình IPO của cả file:
#   Input  : lịch học + danh sách học viên + dữ liệu điểm danh
#   Process: ghép 3 bảng -> tính phút trễ, phút về sớm -> xác định trạng thái -> đếm
#   Output : bảng chi tiết, bảng tổng hợp theo học viên, bảng tổng hợp theo buổi
# =====================================================================

from datetime import datetime

import pandas as pd

from core import config


# ---------------------------------------------------------------------
# HÀM: Xác định trạng thái của 1 lượt (1 học viên trong 1 buổi)
# Input : dong = 1 dòng của bảng chi tiết (có Bat_dau, Ket_thuc, Check_in, Check_out,
#         Phut_tre, Phut_ve_som, Ti_le_thoi_luong); luc = thời điểm đang xét
# Output: chuỗi trạng thái, ví dụ "Có mặt"
# Lưu ý: thứ tự các câu if rất quan trọng, điều kiện nào xét trước thì ưu tiên trước
# ---------------------------------------------------------------------
def xac_dinh_trang_thai(dong, luc):
    # B1: Buổi học chưa bắt đầu
    if dong["Bat_dau"] > luc:
        return config.CHUA_DIEN_RA

    buoi_dang_dien_ra = luc <= dong["Ket_thuc"]

    # B2: Không có giờ check-in (pd.isna = ô trống)
    if pd.isna(dong["Check_in"]):
        if buoi_dang_dien_ra:
            return config.CHUA_CHECK_IN     # buổi chưa hết -> chưa kết luận vắng
        else:
            return config.VANG

    # B3: Có check-in nhưng chưa có check-out
    if pd.isna(dong["Check_out"]):
        if buoi_dang_dien_ra:
            return config.DANG_HOC
        else:
            return config.THIEU_CHECK_OUT

    # B4: Có đủ vào/ra nhưng ngồi học dưới 80% thời lượng -> tính như vắng
    if dong["Ti_le_thoi_luong"] < config.THOI_LUONG_TOI_THIEU:
        return config.KHONG_DU_THOI_LUONG

    # B5: Xét đi trễ và về sớm
    tre = dong["Phut_tre"] > config.TRE_CHO_PHEP_PHUT
    ve_som = dong["Phut_ve_som"] > config.VE_SOM_CHO_PHEP_PHUT

    if tre and ve_som:
        return config.TRE_VA_VE_SOM
    elif tre:
        return config.DI_TRE
    elif ve_som:
        return config.VE_SOM
    else:
        return config.CO_MAT


# ---------------------------------------------------------------------
# HÀM: Ghi lý do cảnh báo cho 1 học viên
# Input : dong = 1 dòng bảng tổng hợp học viên
# Output: chuỗi lý do, rỗng "" nếu không cần cảnh báo
# ---------------------------------------------------------------------
def tao_canh_bao(dong):
    ly_do = []      # list lưu các lý do
    if dong["Vang"] > config.GIOI_HAN_VANG:
        ly_do.append(f"Vắng {dong['Vang']} buổi (quá {config.GIOI_HAN_VANG})")
    if dong["Ti_le_chuyen_can"] < config.TI_LE_CHUYEN_CAN_TOI_THIEU:
        ly_do.append(f"Chuyên cần {dong['Ti_le_chuyen_can']:.0%}")
    if dong["Di_tre"] >= config.GIOI_HAN_DI_TRE:
        ly_do.append(f"Đi trễ {dong['Di_tre']} lần")
    return "; ".join(ly_do)    # nối các lý do bằng dấu ;


class QuanLyDiemDanh:
    def __init__(self, du_lieu):
        # du_lieu là object QuanLyDuLieu (file storage.py) dùng để đọc/ghi Excel
        self.du_lieu = du_lieu

    # =================================================================
    # PHẦN 1: TÌM BUỔI HỌC
    # =================================================================

    # Tìm buổi đang mở check-in hoặc check-out tại thời điểm "luc"
    def buoi_dang_mo(self, luc):
        for buoi in self.du_lieu.danh_sach_buoi():
            if buoi.mo_check_in(luc) or buoi.mo_check_out(luc):
                return buoi
        return None

    # Tìm buổi sắp tới gần nhất (nếu đã học hết thì lấy buổi cuối cùng)
    def buoi_gan_nhat(self, luc):
        danh_sach = self.du_lieu.danh_sach_buoi()
        if len(danh_sach) == 0:
            return None
        for buoi in danh_sach:                 # lịch đã sắp xếp theo ngày
            if buoi.ket_thuc >= luc:
                return buoi
        return danh_sach[-1]                   # index -1 = phần tử cuối

    # =================================================================
    # PHẦN 2: CHECK-IN / CHECK-OUT
    # Cả 2 hàm trả về 2 giá trị: (thanh_cong, thong_bao)
    #   thanh_cong = True / False, thong_bao = câu hiển thị cho người dùng
    # =================================================================

    # Input : mã học viên, mã buổi, thời điểm, cách check-in (camera/thu_cong),
    #         khoảng cách nhận dạng, bo_qua_gio (chế độ demo: không kiểm tra khung giờ)
    def check_in(self, ma_hv, ma_buoi, luc=None, phuong_thuc="camera",
                 khoang_cach=None, bo_qua_gio=False):
        # Không truyền thời điểm -> lấy giờ hiện tại (bỏ phần lẻ micro giây)
        if luc is None:
            luc = datetime.now()
        luc = luc.replace(microsecond=0)

        # B1: Kiểm tra học viên có tồn tại không
        ten = self.du_lieu.ten_hoc_vien()
        if ma_hv not in ten:
            return False, f"Không tìm thấy học viên {ma_hv}"

        # B2: Kiểm tra buổi học có tồn tại không
        buoi = self.du_lieu.tim_buoi(ma_buoi)
        if buoi is None:
            return False, f"Không tìm thấy buổi {ma_buoi}"

        # B3: Kiểm tra có đang trong giờ check-in không
        if not bo_qua_gio and not buoi.mo_check_in(luc):
            return False, (f"Ngoài giờ check-in của buổi {ma_buoi} "
                           f"(mở từ {config.MO_CHECK_IN_TRUOC_PHUT} phút trước giờ học đến hết buổi)")

        # B4: Kiểm tra đã check-in buổi này chưa (tránh check-in 2 lần)
        df = self.du_lieu.doc_diem_danh()
        da_co = df[(df["Ma_buoi"] == ma_buoi) & (df["Ma_HV"] == ma_hv)]
        if len(da_co) > 0:
            gio_cu = da_co.iloc[0]["Check_in"].strftime("%H:%M:%S")
            return False, f"{ten[ma_hv]} đã check-in buổi {ma_buoi} lúc {gio_cu}"

        # B5: Thêm 1 dòng điểm danh mới rồi lưu
        dong_moi = {
            "Ma_buoi": ma_buoi,
            "Ma_HV": ma_hv,
            "Check_in": luc,
            "Check_out": pd.NaT,                 # NaT = chưa có giờ
            "Phuong_thuc_in": phuong_thuc,
            "Phuong_thuc_out": None,
            "Khoang_cach_nhan_dang": khoang_cach,
            "Ghi_chu": "",
        }
        df = pd.concat([df, pd.DataFrame([dong_moi])], ignore_index=True)
        self.du_lieu.luu_diem_danh(df)

        # B6: Tạo câu thông báo (kèm số phút trễ nếu có)
        phut_tre = (luc - buoi.bat_dau).total_seconds() / 60
        thong_bao = f"Check-in thành công: {ten[ma_hv]} lúc {luc.strftime('%H:%M:%S')}"
        if phut_tre > config.TRE_CHO_PHEP_PHUT:
            thong_bao = thong_bao + f" — trễ {phut_tre:.0f} phút"
        return True, thong_bao

    def check_out(self, ma_hv, ma_buoi, luc=None, phuong_thuc="camera", bo_qua_gio=False):
        if luc is None:
            luc = datetime.now()
        luc = luc.replace(microsecond=0)

        # B1, B2: Kiểm tra học viên và buổi học (giống check-in)
        ten = self.du_lieu.ten_hoc_vien()
        if ma_hv not in ten:
            return False, f"Không tìm thấy học viên {ma_hv}"
        buoi = self.du_lieu.tim_buoi(ma_buoi)
        if buoi is None:
            return False, f"Không tìm thấy buổi {ma_buoi}"

        # B3: Kiểm tra khung giờ check-out
        if not bo_qua_gio and not buoi.mo_check_out(luc):
            return False, f"Ngoài giờ check-out của buổi {ma_buoi}"

        # B4: Phải có check-in rồi mới check-out được
        df = self.du_lieu.doc_diem_danh()
        dieu_kien = (df["Ma_buoi"] == ma_buoi) & (df["Ma_HV"] == ma_hv)
        if not dieu_kien.any():
            return False, f"{ten[ma_hv]} chưa check-in buổi {ma_buoi}, không thể check-out"

        vi_tri = df[dieu_kien].index[0]          # vị trí dòng điểm danh của học viên này

        # B5: Đã check-out rồi thì không check-out lại
        if pd.notna(df.loc[vi_tri, "Check_out"]):
            gio_cu = df.loc[vi_tri, "Check_out"].strftime("%H:%M:%S")
            return False, f"{ten[ma_hv]} đã check-out lúc {gio_cu}"

        # B6: Giờ ra phải sau giờ vào
        gio_vao = df.loc[vi_tri, "Check_in"]
        if luc <= gio_vao:
            return False, "Giờ check-out phải sau giờ check-in"

        # B7: Ghi giờ ra vào đúng dòng đó rồi lưu
        df.loc[vi_tri, "Check_out"] = luc
        df.loc[vi_tri, "Phuong_thuc_out"] = phuong_thuc
        self.du_lieu.luu_diem_danh(df)

        # B8: Tính số phút đã học để báo cho học viên
        # (chỉ tính phần nằm TRONG giờ học: vào sớm hay ra muộn không được cộng thêm)
        vao_tinh = max(gio_vao, buoi.bat_dau)
        ra_tinh = min(luc, buoi.ket_thuc)
        phut_hoc = max((ra_tinh - vao_tinh).total_seconds() / 60, 0)
        return True, (f"Check-out thành công: {ten[ma_hv]} lúc {luc.strftime('%H:%M:%S')} "
                      f"— đã học {phut_hoc:.0f}/{buoi.thoi_luong_phut:.0f} phút")

    # Xóa 1 lượt điểm danh (dùng khi camera nhận nhầm người)
    def xoa_luot(self, ma_hv, ma_buoi):
        df = self.du_lieu.doc_diem_danh()
        giu_lai = ~((df["Ma_buoi"] == ma_buoi) & (df["Ma_HV"] == ma_hv))   # ~ = NOT
        self.du_lieu.luu_diem_danh(df[giu_lai])

    # =================================================================
    # PHẦN 3: BẢNG CHI TIẾT (mỗi dòng = 1 học viên x 1 buổi)
    #
    # Vấn đề: file điểm danh chỉ có người ĐÃ ĐẾN. Muốn biết ai VẮNG phải:
    #   lấy danh sách "ai PHẢI đến" (mọi buổi x mọi học viên)
    #   rồi so với danh sách "ai ĐÃ đến" (file điểm danh)
    # =================================================================
    def bang_chi_tiet(self, luc=None):
        if luc is None:
            luc = datetime.now()

        # B1: Đọc 3 bảng
        lich = self.du_lieu.doc_lich_hoc()
        hoc_vien = self.du_lieu.doc_hoc_vien()[["Ma_HV", "Ho_ten"]]
        diem_danh = self.du_lieu.doc_diem_danh()
        if lich.empty or hoc_vien.empty:
            return pd.DataFrame()

        # B2: Tạo cột giờ bắt đầu / kết thúc đầy đủ (ngày + giờ) cho từng buổi
        lich = lich.copy()
        ngay_chuoi = lich["Ngay"].dt.strftime("%Y-%m-%d")
        lich["Bat_dau"] = pd.to_datetime(ngay_chuoi + " " + lich["Gio_bat_dau"])
        lich["Ket_thuc"] = pd.to_datetime(ngay_chuoi + " " + lich["Gio_ket_thuc"])

        # B3: Chỉ giữ các buổi đã bắt đầu (buổi tương lai chưa xét)
        lich = lich[lich["Bat_dau"] <= luc]
        if lich.empty:
            return pd.DataFrame()

        # B4: Ghép mọi buổi x mọi học viên (how="cross")
        #     Ví dụ 16 buổi x 20 học viên = 320 dòng = 320 lượt PHẢI đi học
        bang = lich[["Ma_buoi", "Ngay", "Chu_de", "Bat_dau", "Ket_thuc"]].merge(hoc_vien, how="cross")

        # B5: Ghép với bảng điểm danh (how="left": giữ hết dòng bên trái)
        #     Ai không có dòng điểm danh -> Check_in để trống (NaT) -> sau này thành "Vắng"
        bang = bang.merge(
            diem_danh[["Ma_buoi", "Ma_HV", "Check_in", "Check_out", "Phuong_thuc_in"]],
            on=["Ma_buoi", "Ma_HV"],
            how="left",
        )

        # B6: Tính số phút (tính cả cột một lúc, không cần vòng lặp)
        thoi_luong_buoi = (bang["Ket_thuc"] - bang["Bat_dau"]).dt.total_seconds() / 60

        #   Phút trễ = giờ vào - giờ bắt đầu (đến sớm thì số âm -> clip về 0)
        bang["Phut_tre"] = (bang["Check_in"] - bang["Bat_dau"]).dt.total_seconds() / 60
        bang["Phut_tre"] = bang["Phut_tre"].clip(lower=0).round(0)

        #   Phút về sớm = giờ kết thúc - giờ ra
        bang["Phut_ve_som"] = (bang["Ket_thuc"] - bang["Check_out"]).dt.total_seconds() / 60
        bang["Phut_ve_som"] = bang["Phut_ve_som"].clip(lower=0).round(0)

        #   Phút học thực tế: chỉ tính phần nằm trong giờ học
        vao_tinh = bang[["Check_in", "Bat_dau"]].max(axis=1)     # lấy giờ MUỘN hơn
        ra_tinh = bang[["Check_out", "Ket_thuc"]].min(axis=1)    # lấy giờ SỚM hơn
        phut_hoc = ((ra_tinh - vao_tinh).dt.total_seconds() / 60).clip(lower=0)
        co_du_vao_ra = bang["Check_in"].notna() & bang["Check_out"].notna()
        bang["Phut_hoc"] = phut_hoc.where(co_du_vao_ra).round(0)    # thiếu vào/ra -> để trống
        bang["Ti_le_thoi_luong"] = (bang["Phut_hoc"] / thoi_luong_buoi).round(3)

        # B7: Xác định trạng thái từng dòng bằng apply (axis=1: chạy theo từng dòng)
        bang["Trang_thai"] = bang.apply(xac_dinh_trang_thai, axis=1, luc=luc)

        # B8: Sắp xếp theo buổi rồi theo mã học viên
        return bang.sort_values(["Bat_dau", "Ma_HV"]).reset_index(drop=True)

    # =================================================================
    # PHẦN 4: THỐNG KÊ
    # =================================================================

    # Bỏ các lượt chưa thể kết luận (buổi đang học mà học viên chưa tới)
    def loc_luot_da_tinh(self, chi_tiet):
        return chi_tiet[~chi_tiet["Trang_thai"].isin(config.TRANG_THAI_CHUA_TINH)].copy()

    # -----------------------------------------------------------------
    # Tổng hợp theo HỌC VIÊN
    # Input : bảng chi tiết | Output: mỗi học viên 1 dòng
    # -----------------------------------------------------------------
    def tong_hop_hoc_vien(self, chi_tiet):
        if chi_tiet.empty:
            return pd.DataFrame()

        # B1: Bỏ các lượt chưa kết luận
        df = self.loc_luot_da_tinh(chi_tiet)

        # B2: Tạo các cột True/False cho từng loại (isin = có nằm trong list không)
        df["co_mat"] = df["Trang_thai"].isin(config.TRANG_THAI_CO_DI_HOC)
        df["vang"] = df["Trang_thai"].isin(config.TRANG_THAI_VANG)
        df["tre"] = df["Trang_thai"].isin([config.DI_TRE, config.TRE_VA_VE_SOM])
        df["som"] = df["Trang_thai"].isin([config.VE_SOM, config.TRE_VA_VE_SOM])
        df["thieu_out"] = df["Trang_thai"] == config.THIEU_CHECK_OUT

        # B3: Gom nhóm theo học viên rồi tính
        #     Cú pháp: Ten_cot_moi=("cot_goc", "phep_tinh")
        #     sum của cột True/False = đếm số lần True (True = 1, False = 0)
        kq = df.groupby(["Ma_HV", "Ho_ten"]).agg(
            So_buoi=("Ma_buoi", "count"),
            Co_mat=("co_mat", "sum"),
            Vang=("vang", "sum"),
            Di_tre=("tre", "sum"),
            Ve_som=("som", "sum"),
            Thieu_check_out=("thieu_out", "sum"),
            Tong_phut_hoc=("Phut_hoc", "sum"),
        ).reset_index()

        # B4: Tính thêm các cột phụ
        kq["Tong_gio_hoc"] = (kq["Tong_phut_hoc"] / 60).round(1)
        kq["Ti_le_chuyen_can"] = (kq["Co_mat"] / kq["So_buoi"]).round(3)
        kq = kq.drop(columns=["Tong_phut_hoc"])

        # B5: Ghi cảnh báo cho từng học viên
        kq["Canh_bao"] = kq.apply(tao_canh_bao, axis=1)

        # B6: Ai vắng nhiều nhất lên đầu
        kq = kq.sort_values(["Vang", "Di_tre"], ascending=False)
        return kq.reset_index(drop=True)

    # -----------------------------------------------------------------
    # Tổng hợp theo BUỔI HỌC
    # Input : bảng chi tiết | Output: mỗi buổi 1 dòng
    # -----------------------------------------------------------------
    def tong_hop_buoi(self, chi_tiet):
        if chi_tiet.empty:
            return pd.DataFrame()

        df = self.loc_luot_da_tinh(chi_tiet)
        df["co_mat"] = df["Trang_thai"].isin(config.TRANG_THAI_CO_DI_HOC)
        df["vang"] = df["Trang_thai"].isin(config.TRANG_THAI_VANG)
        df["tre"] = df["Trang_thai"].isin([config.DI_TRE, config.TRE_VA_VE_SOM])

        kq = df.groupby(["Ma_buoi", "Ngay", "Chu_de"]).agg(
            Si_so=("Ma_HV", "count"),
            Co_mat=("co_mat", "sum"),
            Vang=("vang", "sum"),
            Di_tre=("tre", "sum"),
        ).reset_index()
        kq["Ti_le_co_mat"] = (kq["Co_mat"] / kq["Si_so"]).round(3)
        return kq.sort_values("Ngay").reset_index(drop=True)

    # Đếm số lượt theo từng trạng thái (dùng để vẽ biểu đồ cột)
    def dem_trang_thai(self, chi_tiet):
        if chi_tiet.empty:
            return pd.Series(dtype="int64")
        return self.loc_luot_da_tinh(chi_tiet)["Trang_thai"].value_counts()
