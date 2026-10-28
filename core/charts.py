# =====================================================================
# FILE: core/charts.py
# NHIỆM VỤ: Vẽ 3 biểu đồ cho trang Thống kê và cho báo cáo Excel
#   1. Đường : tỉ lệ có mặt theo từng buổi         -> chuyên cần cả lớp tăng hay giảm?
#   2. Thanh ngang: số buổi vắng theo học viên     -> ai vắng nhiều nhất?
#   3. Cột   : số lượt theo từng trạng thái        -> có mặt / trễ / vắng chiếm bao nhiêu?
# KIẾN THỨC: Matplotlib (plot, barh, bar), list comprehension, if/else
#
# Mỗi hàm nhận 1 DataFrame và TRẢ VỀ hình vẽ (fig):
#   - app.py hiển thị bằng st.pyplot(fig)
#   - report.py lưu fig thành ảnh để chèn vào Excel
# =====================================================================

import matplotlib

matplotlib.use("Agg")      # vẽ vào bộ nhớ, không mở cửa sổ (bắt buộc khi dùng với Streamlit)
import matplotlib.pyplot as plt

from core import config

# Màu cho từng trạng thái (dictionary: trạng thái -> mã màu)
MAU_TRANG_THAI = {
    config.CO_MAT: "#2e7d32",               # xanh lá
    config.DI_TRE: "#f9a825",               # vàng
    config.VE_SOM: "#ef6c00",               # cam
    config.TRE_VA_VE_SOM: "#d84315",
    config.THIEU_CHECK_OUT: "#8d6e63",
    config.KHONG_DU_THOI_LUONG: "#ad1457",
    config.VANG: "#c62828",                 # đỏ
    config.DANG_HOC: "#1565c0",
}


# ---------------------------------------------------------------------
# BIỂU ĐỒ 1: Đường - tỉ lệ có mặt theo buổi
# Input : bảng tổng hợp theo buổi (cột Ma_buoi, Ti_le_co_mat)
# ---------------------------------------------------------------------
def bieu_do_ti_le_theo_buoi(tong_hop_buoi):
    # fig = cả khung hình, ax = vùng vẽ bên trong
    fig, ax = plt.subplots(figsize=(9, 3.6))

    if tong_hop_buoi.empty:
        ax.text(0.5, 0.5, "Chưa có dữ liệu", ha="center", va="center")
        return fig

    # B1: Vẽ đường (trục x = mã buổi, trục y = tỉ lệ %)
    x = tong_hop_buoi["Ma_buoi"]
    y = tong_hop_buoi["Ti_le_co_mat"] * 100
    ax.plot(x, y, marker="o", color="#1565c0", linewidth=2)

    # B2: Vẽ vạch mục tiêu 80% bằng đường ngang nét đứt
    muc_tieu = config.TI_LE_CHUYEN_CAN_TOI_THIEU * 100
    ax.axhline(muc_tieu, color="#c62828", linestyle="--", linewidth=1)
    ax.text(len(x) - 0.5, muc_tieu + 1, "mục tiêu 80%", color="#c62828", ha="right", fontsize=9)

    # B3: Tiêu đề, nhãn trục
    ax.set_ylim(0, 105)
    ax.set_ylabel("Tỉ lệ có mặt (%)")
    ax.set_title("Tỉ lệ có mặt theo buổi học")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------
# BIỂU ĐỒ 2: Thanh ngang - học viên vắng nhiều nhất
# Input : bảng tổng hợp theo học viên (cột Ma_HV, Ho_ten, Vang)
# ---------------------------------------------------------------------
def bieu_do_vang_theo_hoc_vien(tong_hop_hv, so_luong=10):
    fig, ax = plt.subplots(figsize=(9, 4.2))

    if tong_hop_hv.empty:
        ax.text(0.5, 0.5, "Chưa có dữ liệu", ha="center", va="center")
        return fig

    # B1: Lọc người có vắng -> lấy top 10 vắng nhiều nhất -> sắp tăng dần
    #     (barh vẽ dòng đầu ở DƯỚI, nên sắp tăng dần thì người vắng nhiều nhất nằm TRÊN cùng)
    df = tong_hop_hv[tong_hop_hv["Vang"] > 0]
    df = df.nlargest(so_luong, "Vang").sort_values("Vang")
    if df.empty:
        ax.text(0.5, 0.5, "Không có học viên nào vắng", ha="center", va="center")
        return fig

    # B2: Chọn màu: vắng quá giới hạn -> đỏ, còn lại -> xám
    mau = []
    for so_vang in df["Vang"]:
        if so_vang > config.GIOI_HAN_VANG:
            mau.append("#c62828")
        else:
            mau.append("#90a4ae")

    # B3: Vẽ thanh ngang, nhãn = "HV007 · Trần Gia An"
    nhan = df["Ma_HV"] + " · " + df["Ho_ten"]
    ax.barh(nhan, df["Vang"], color=mau)

    # B4: Vạch giới hạn vắng + ghi số ở cuối mỗi thanh
    ax.axvline(config.GIOI_HAN_VANG, color="#c62828", linestyle="--", linewidth=1)
    vi_tri = 0
    for so_vang in df["Vang"]:
        ax.text(so_vang + 0.1, vi_tri, str(int(so_vang)), va="center", fontsize=9)
        vi_tri = vi_tri + 1

    ax.set_xlabel("Số buổi vắng")
    ax.set_title(f"Học viên vắng nhiều nhất (đỏ = vắng quá {config.GIOI_HAN_VANG} buổi)")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------
# BIỂU ĐỒ 3: Cột - số lượt theo từng trạng thái
# Input : Series đếm trạng thái, ví dụ {"Có mặt": 265, "Vắng": 22, ...}
# ---------------------------------------------------------------------
def bieu_do_trang_thai(dem):
    fig, ax = plt.subplots(figsize=(9, 3.6))

    if dem.empty:
        ax.text(0.5, 0.5, "Chưa có dữ liệu", ha="center", va="center")
        return fig

    # B1: Sắp giảm dần, chọn màu theo dictionary MAU_TRANG_THAI
    dem = dem.sort_values(ascending=False)
    mau = [MAU_TRANG_THAI.get(trang_thai, "#607d8b") for trang_thai in dem.index]

    # B2: Vẽ cột + ghi số trên đầu mỗi cột
    ax.bar(dem.index, dem.values, color=mau)
    for i in range(len(dem)):
        ax.text(i, dem.values[i], str(int(dem.values[i])), ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("Số lượt")
    ax.set_title("Số lượt điểm danh theo trạng thái")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")    # xoay chữ trục x cho khỏi đè nhau
    fig.tight_layout()
    return fig
