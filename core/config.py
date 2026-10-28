# =====================================================================
# FILE: core/config.py
# NHIỆM VỤ: Lưu tất cả HẰNG SỐ của chương trình ở một chỗ
#   - Đường dẫn các file dữ liệu
#   - Quy tắc điểm danh (bao nhiêu phút thì tính trễ, vắng mấy buổi thì cảnh báo...)
#   - Ngưỡng nhận dạng khuôn mặt
#   - Tên các trạng thái điểm danh
# =====================================================================

import os

# ---------------------------------------------------------------------
# PHẦN 1: ĐƯỜNG DẪN
# ---------------------------------------------------------------------
THU_MUC_GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

THU_MUC_DATA = os.path.join(THU_MUC_GOC, "data")              # chứa 3 file Excel
THU_MUC_KHUON_MAT = os.path.join(THU_MUC_DATA, "faces")       # ảnh khuôn mặt: faces/HV001/1.jpg
THU_MUC_BAO_CAO = os.path.join(THU_MUC_GOC, "bao_cao")        # báo cáo Excel xuất ra

FILE_HOC_VIEN = os.path.join(THU_MUC_DATA, "hoc_vien.xlsx")
FILE_LICH_HOC = os.path.join(THU_MUC_DATA, "lich_hoc.xlsx")
FILE_DIEM_DANH = os.path.join(THU_MUC_DATA, "diem_danh.xlsx")
FILE_MODEL = os.path.join(THU_MUC_DATA, "face_model.yml")        # model nhận dạng đã huấn luyện
FILE_NHAN_MODEL = os.path.join(THU_MUC_DATA, "face_labels.json") # bảng tra: nhãn số -> mã học viên

# ---------------------------------------------------------------------
# PHẦN 2: QUY TẮC ĐIỂM DANH
# ---------------------------------------------------------------------
MO_CHECK_IN_TRUOC_PHUT = 30        # được check-in sớm nhất 30 phút trước giờ học
DONG_CHECK_OUT_SAU_PHUT = 60       # được check-out muộn nhất 60 phút sau giờ kết thúc
TRE_CHO_PHEP_PHUT = 15             # vào sau giờ bắt đầu quá 15 phút -> Đi trễ
VE_SOM_CHO_PHEP_PHUT = 15          # ra trước giờ kết thúc quá 15 phút -> Về sớm
THOI_LUONG_TOI_THIEU = 0.8         # phải ngồi học ít nhất 80% thời lượng buổi, nếu không tính vắng
GIOI_HAN_VANG = 3                  # vắng QUÁ 3 buổi -> cảnh báo
TI_LE_CHUYEN_CAN_TOI_THIEU = 0.8   # tỉ lệ chuyên cần dưới 80% -> cảnh báo
GIOI_HAN_DI_TRE = 3                # đi trễ từ 3 lần trở lên -> cảnh báo

# ---------------------------------------------------------------------
# PHẦN 3: NHẬN DẠNG KHUÔN MẶT
# ---------------------------------------------------------------------
KICH_THUOC_MAT = (200, 200)        # mọi ảnh khuôn mặt được đưa về cùng cỡ 200 x 200
SO_ANH_TOI_THIEU = 3               # mỗi học viên cần ít nhất 3 ảnh mới được huấn luyện
NGUONG_NHAN_DANG = 70.0            # khoảng cách > 70 -> coi là "không nhận ra"
                                   # (khoảng cách càng NHỎ thì càng GIỐNG)

# ---------------------------------------------------------------------
# PHẦN 4: TÊN CÁC TRẠNG THÁI ĐIỂM DANH
# (viết thành hằng số để các file dùng chung, tránh gõ sai chính tả)
# ---------------------------------------------------------------------
CO_MAT = "Có mặt"
DI_TRE = "Đi trễ"
VE_SOM = "Về sớm"
TRE_VA_VE_SOM = "Đi trễ & về sớm"
THIEU_CHECK_OUT = "Thiếu check-out"          # có vào nhưng quên check-out
KHONG_DU_THOI_LUONG = "Không đủ thời lượng"  # học dưới 80% -> tính là vắng
VANG = "Vắng"
DANG_HOC = "Đang học"                        # buổi đang diễn ra, đã check-in
CHUA_CHECK_IN = "Chưa check-in"              # buổi đang diễn ra, chưa tới (chưa kết luận vắng)
CHUA_DIEN_RA = "Chưa diễn ra"

# List các trạng thái được tính là "CÓ ĐI HỌC"
TRANG_THAI_CO_DI_HOC = [CO_MAT, DI_TRE, VE_SOM, TRE_VA_VE_SOM, THIEU_CHECK_OUT, DANG_HOC]

# List các trạng thái được tính là "VẮNG"
TRANG_THAI_VANG = [VANG, KHONG_DU_THOI_LUONG]

# List các trạng thái CHƯA THỂ KẾT LUẬN -> bỏ qua khi thống kê
TRANG_THAI_CHUA_TINH = [CHUA_CHECK_IN, CHUA_DIEN_RA]
