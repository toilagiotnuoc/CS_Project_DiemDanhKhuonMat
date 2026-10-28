# =====================================================================
# FILE: app.py
# NHIỆM VỤ: Giao diện web của chương trình (Streamlit), gồm 5 trang:
#   1. Tổng quan            : các con số chính + buổi đang điểm danh + ai cần nhắc nhở
#   2. Điểm danh            : check-in / check-out bằng camera (hoặc thủ công)
#   3. Lịch học             : xem lịch, thêm buổi học
#   4. Học viên & khuôn mặt : thêm/xóa học viên, chụp ảnh đăng ký, huấn luyện model
#   5. Thống kê & báo cáo   : bảng, biểu đồ, tải báo cáo Excel
# KIẾN THỨC: Streamlit (sidebar, columns, tabs, form, camera_input, metric,
#            dataframe, download_button, session_state), hàm, dictionary
#
# CÁCH CHẠY:  streamlit run app.py      (KHÔNG chạy bằng python app.py)
#
# Lưu ý về Streamlit: mỗi lần người dùng bấm nút / chọn gì đó,
# Streamlit chạy lại TOÀN BỘ file này từ trên xuống dưới.
#
# File này KHÔNG tự đọc Excel hay tự tính toán, mà gọi các class trong thư mục core/:
#   QuanLyDuLieu (storage.py), QuanLyDiemDanh (attendance.py), NhanDangKhuonMat (face.py)
# =====================================================================

from datetime import datetime, time
from io import BytesIO

import pandas as pd
import streamlit as st

from core import config
from core.attendance import QuanLyDiemDanh
from core.charts import bieu_do_ti_le_theo_buoi, bieu_do_trang_thai, bieu_do_vang_theo_hoc_vien
from core.face import NhanDangKhuonMat
from core.models import BuoiHoc, HocVien
from core.report import TEN_COT, xuat_bao_cao
from core.storage import QuanLyDuLieu

# set_page_config phải là lệnh Streamlit đầu tiên
st.set_page_config(page_title="Điểm danh khuôn mặt", page_icon="📷", layout="wide")


# =====================================================================
# PHẦN 1: KHỞI TẠO CÁC ĐỐI TƯỢNG
# @st.cache_resource: chỉ tạo 1 lần, những lần Streamlit chạy lại thì dùng lại
# (không có dòng này thì mỗi lần bấm nút đều phải tạo lại và nạp lại model khuôn mặt)
# =====================================================================
@st.cache_resource
def khoi_tao():
    du_lieu = QuanLyDuLieu()
    diem_danh = QuanLyDiemDanh(du_lieu)
    khuon_mat = NhanDangKhuonMat()
    return du_lieu, diem_danh, khuon_mat


du_lieu, diem_danh, khuon_mat = khoi_tao()

# session_state: nơi lưu giá trị GIỮA các lần Streamlit chạy lại
# camera_key: đổi số này để xóa ảnh cũ trên camera, sẵn sàng cho người tiếp theo
if "camera_key" not in st.session_state:
    st.session_state.camera_key = 0


# =====================================================================
# PHẦN 2: CÁC HÀM DÙNG CHUNG CHO NHIỀU TRANG
# =====================================================================

# Xóa ảnh trên camera để chụp người tiếp theo
def lam_moi_camera():
    st.session_state.camera_key = st.session_state.camera_key + 1


# Hiển thị bảng với tên cột tiếng Việt có dấu
def hien_bang(df, cau_hinh_cot=None):
    st.dataframe(df.rename(columns=TEN_COT), width="stretch", hide_index=True,
                 column_config=cau_hinh_cot)


# Cấu hình hiển thị cột tỉ lệ thành thanh tiến độ (0% -> 100%)
def thanh_ti_le(ten_cot):
    return {ten_cot: st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)}


# Tạo ô chọn buổi học
# Input : nhãn hiển thị, buổi chọn sẵn, key (Streamlit cần key riêng cho mỗi ô)
# Output: object BuoiHoc được chọn (hoặc None nếu chưa có lịch)
def chon_buoi(nhan, buoi_mac_dinh, key):
    danh_sach = du_lieu.danh_sach_buoi()
    if len(danh_sach) == 0:
        st.warning("Chưa có lịch học. Vào trang Lịch học để thêm buổi.")
        return None

    # Tìm vị trí của buổi mặc định trong danh sách (để chọn sẵn)
    vi_tri = 0
    if buoi_mac_dinh is not None:
        for i in range(len(danh_sach)):
            if danh_sach[i].ma_buoi == buoi_mac_dinh.ma_buoi:
                vi_tri = i

    # format_func: cách hiển thị mỗi lựa chọn (gọi method nhan() của BuoiHoc)
    return st.selectbox(nhan, danh_sach, index=vi_tri, format_func=lambda buoi: buoi.nhan(), key=key)


# Hiển thị "HV001 · Hoàng Thanh Mai" thay vì chỉ "HV001"
def ten_day_du(ma_hv):
    return f"{ma_hv} · {du_lieu.ten_hoc_vien().get(ma_hv, '')}"


# =====================================================================
# PHẦN 3: THANH BÊN (SIDEBAR)
# =====================================================================
st.sidebar.title("📷 Điểm danh khuôn mặt")
trang = st.sidebar.radio(
    "Chức năng",
    ["🏠 Tổng quan", "📷 Điểm danh", "📅 Lịch học", "👥 Học viên & khuôn mặt", "📊 Thống kê & báo cáo"],
)
st.sidebar.divider()
st.sidebar.caption(f"Bây giờ: {datetime.now():%H:%M · %d/%m/%Y}")

# Báo tình trạng OpenCV / model
tinh_trang = khuon_mat.tinh_trang()
if tinh_trang == "OK":
    if khuon_mat.da_huan_luyen():
        st.sidebar.success("Nhận dạng khuôn mặt: sẵn sàng")
    else:
        st.sidebar.success("OpenCV sẵn sàng · chưa huấn luyện model")
else:
    st.sidebar.warning(tinh_trang)

# Hiện quy tắc điểm danh (lấy từ config.py -> sửa config là chữ ở đây tự đổi)
with st.sidebar.expander("Quy tắc điểm danh"):
    st.markdown(
        f"- Check-in mở **{config.MO_CHECK_IN_TRUOC_PHUT} phút** trước giờ học\n"
        f"- Trễ quá **{config.TRE_CHO_PHEP_PHUT} phút** → Đi trễ\n"
        f"- Về sớm quá **{config.VE_SOM_CHO_PHEP_PHUT} phút** → Về sớm\n"
        f"- Học dưới **{config.THOI_LUONG_TOI_THIEU:.0%}** thời lượng → tính vắng\n"
        f"- Vắng quá **{config.GIOI_HAN_VANG} buổi** hoặc chuyên cần dưới "
        f"**{config.TI_LE_CHUYEN_CAN_TOI_THIEU:.0%}** → cảnh báo"
    )


# =====================================================================
# TRANG 1: TỔNG QUAN
# =====================================================================
def trang_tong_quan():
    st.title("🏠 Tổng quan")
    bay_gio = datetime.now()

    # B1: Lấy dữ liệu
    hoc_vien = du_lieu.doc_hoc_vien()
    lich = du_lieu.danh_sach_buoi()
    chi_tiet = diem_danh.bang_chi_tiet(bay_gio)
    tong_hop = diem_danh.tong_hop_hoc_vien(chi_tiet)

    # B2: 4 ô số liệu chính, xếp thành 4 cột
    so_buoi_da_hoc = 0
    for buoi in lich:
        if buoi.ket_thuc < bay_gio:
            so_buoi_da_hoc = so_buoi_da_hoc + 1

    cot1, cot2, cot3, cot4 = st.columns(4)
    cot1.metric("Học viên", len(hoc_vien))
    cot2.metric("Buổi đã học", f"{so_buoi_da_hoc}/{len(lich)}")
    if tong_hop.empty:
        cot3.metric("Chuyên cần trung bình", "—")
        cot4.metric("Học viên cần nhắc nhở", 0)
    else:
        cot3.metric("Chuyên cần trung bình", f"{tong_hop['Ti_le_chuyen_can'].mean():.0%}")
        cot4.metric("Học viên cần nhắc nhở", int((tong_hop["Canh_bao"] != "").sum()))

    # B3: Buổi đang mở điểm danh (nếu không có thì lấy buổi gần nhất)
    buoi = diem_danh.buoi_dang_mo(bay_gio)
    if buoi is None:
        buoi = diem_danh.buoi_gan_nhat(bay_gio)

    if buoi is not None:
        if buoi.mo_check_in(bay_gio) or buoi.mo_check_out(bay_gio):
            st.subheader("🟢 Đang mở điểm danh: " + buoi.nhan())
        else:
            st.subheader("📌 Buổi gần nhất: " + buoi.nhan())

        if not chi_tiet.empty and buoi.ma_buoi in chi_tiet["Ma_buoi"].values:
            bang_buoi = chi_tiet[chi_tiet["Ma_buoi"] == buoi.ma_buoi]
            da_check_in = bang_buoi[bang_buoi["Check_in"].notna()]
            st.write(f"Đã check-in: **{len(da_check_in)}/{len(bang_buoi)}** học viên")
            hien_bang(bang_buoi[["Ma_HV", "Ho_ten", "Check_in", "Check_out", "Trang_thai"]])
        else:
            st.info("Buổi này chưa bắt đầu.")

    # B4: Danh sách học viên cần nhắc nhở
    if not tong_hop.empty:
        can_nhac = tong_hop[tong_hop["Canh_bao"] != ""]
        if len(can_nhac) > 0:
            st.subheader("⚠️ Học viên cần nhắc nhở")
            hien_bang(can_nhac[["Ma_HV", "Ho_ten", "Vang", "Di_tre", "Ti_le_chuyen_can", "Canh_bao"]],
                      thanh_ti_le("Tỉ lệ chuyên cần"))


# =====================================================================
# TRANG 2: ĐIỂM DANH
# =====================================================================

# Ghi 1 lượt check-in hoặc check-out rồi hiện thông báo
def ghi_diem_danh(thao_tac, ma_hv, buoi, phuong_thuc, khoang_cach, che_do_demo):
    if thao_tac == "Check-in":
        thanh_cong, thong_bao = diem_danh.check_in(
            ma_hv, buoi.ma_buoi, phuong_thuc=phuong_thuc,
            khoang_cach=khoang_cach, bo_qua_gio=che_do_demo)
    else:
        thanh_cong, thong_bao = diem_danh.check_out(
            ma_hv, buoi.ma_buoi, phuong_thuc=phuong_thuc, bo_qua_gio=che_do_demo)

    if thanh_cong:
        st.success(thong_bao)
        st.balloons()
    else:
        st.error(thong_bao)
    return thanh_cong


def trang_diem_danh():
    st.title("📷 Điểm danh")
    bay_gio = datetime.now()
    buoi_mo = diem_danh.buoi_dang_mo(bay_gio)

    # B1: Chọn buổi học và thao tác (Check-in / Check-out)
    cot_trai, cot_phai = st.columns([2, 1])
    with cot_trai:
        if buoi_mo is not None:
            buoi_mac_dinh = buoi_mo
        else:
            buoi_mac_dinh = diem_danh.buoi_gan_nhat(bay_gio)
        buoi = chon_buoi("Buổi học", buoi_mac_dinh, key="buoi_diem_danh")
    with cot_phai:
        # Nếu buổi đang mở đã qua giờ kết thúc -> chọn sẵn Check-out
        chon_san = 0
        if buoi_mo is not None and bay_gio >= buoi_mo.ket_thuc:
            chon_san = 1
        thao_tac = st.radio("Thao tác", ["Check-in", "Check-out"], horizontal=True, index=chon_san)

    if buoi is None:
        return

    # B2: Chế độ demo = bỏ qua khung giờ (để thuyết trình ngoài giờ học)
    che_do_demo = st.toggle("Chế độ demo (bỏ qua giới hạn giờ check-in/check-out)",
                            value=(buoi_mo is None),
                            help="Bật khi thuyết trình ngoài giờ học. Thời điểm ghi nhận vẫn là giờ hiện tại.")
    if buoi_mo is None and not che_do_demo:
        st.info("Hiện không có buổi nào đang mở điểm danh.")

    tab_camera, tab_thu_cong = st.tabs(["📷 Bằng khuôn mặt", "✍️ Thủ công (dự phòng)"])

    # ---------------- TAB 1: ĐIỂM DANH BẰNG CAMERA ----------------
    with tab_camera:
        # B3: Kiểm tra máy đã sẵn sàng chưa
        if not khuon_mat.co_nhan_dang():
            st.error(tinh_trang)
        elif not khuon_mat.da_huan_luyen():
            st.warning("Chưa có model nhận dạng. Vào **Học viên & khuôn mặt** để đăng ký ảnh và huấn luyện.")
        else:
            # B4: Thanh chỉnh ngưỡng (nhỏ hơn = khắt khe hơn, khó nhận nhầm người hơn)
            nguong = st.slider("Ngưỡng nhận dạng (nhỏ hơn = khắt khe hơn)", 40, 100,
                               int(config.NGUONG_NHAN_DANG), key="nguong")
            config.NGUONG_NHAN_DANG = float(nguong)

            # B5: Mở camera và chụp ảnh
            anh = st.camera_input(f"Nhìn thẳng vào camera rồi bấm chụp để {thao_tac.lower()}",
                                  key=f"camera_{st.session_state.camera_key}")

            if anh is not None:
                # B6: Nhận dạng ảnh vừa chụp
                ma_hv, khoang_cach, anh_hien_thi, thong_bao = khuon_mat.nhan_dang(anh.getvalue())

                cot_anh, cot_ket_qua = st.columns(2)
                cot_anh.image(anh_hien_thi, caption=thong_bao, width="stretch")

                with cot_ket_qua:
                    if ma_hv is not None:
                        # B7: Nhận ra -> hiện tên, chờ người dùng xác nhận
                        st.markdown(f"### {du_lieu.ten_hoc_vien().get(ma_hv, '?')}")
                        st.markdown(f"`{ma_hv}` · khoảng cách {khoang_cach:.1f}")
                        if st.button(f"✅ Đúng là tôi — {thao_tac}", type="primary", width="stretch"):
                            ghi_diem_danh(thao_tac, ma_hv, buoi, "camera", khoang_cach, che_do_demo)
                        if st.button("❌ Không phải tôi — chụp lại", width="stretch"):
                            lam_moi_camera()
                            st.rerun()
                    else:
                        # Không nhận ra -> gợi ý cách khắc phục
                        st.warning(thong_bao)
                        st.caption("Thử lại: nhìn thẳng, đủ sáng, bỏ khẩu trang/kính râm. "
                                   "Nếu vẫn không được, dùng tab Thủ công.")

                if st.button("🔄 Người tiếp theo"):
                    lam_moi_camera()
                    st.rerun()

    # ---------------- TAB 2: ĐIỂM DANH THỦ CÔNG ----------------
    with tab_thu_cong:
        hoc_vien = du_lieu.doc_hoc_vien()
        if hoc_vien.empty:
            st.warning("Chưa có học viên.")
        else:
            ma_hv = st.selectbox("Học viên", hoc_vien["Ma_HV"], format_func=ten_day_du, key="hv_thu_cong")
            ly_do = st.text_input("Lý do điểm danh thủ công", placeholder="Ví dụ: camera lỗi")
            if st.button(f"{thao_tac} thủ công", type="primary"):
                thanh_cong = ghi_diem_danh(thao_tac, ma_hv, buoi, "thu_cong", None, che_do_demo)
                # Ghi lý do vào cột Ghi_chu của lượt điểm danh đó
                if thanh_cong and ly_do != "":
                    df = du_lieu.doc_diem_danh()
                    dieu_kien = (df["Ma_buoi"] == buoi.ma_buoi) & (df["Ma_HV"] == ma_hv)
                    df.loc[dieu_kien, "Ghi_chu"] = ly_do
                    du_lieu.luu_diem_danh(df)

    # B8: Danh sách điểm danh của buổi đang chọn
    st.divider()
    st.subheader(f"Danh sách điểm danh {buoi.ma_buoi}")
    chi_tiet = diem_danh.bang_chi_tiet(max(bay_gio, buoi.bat_dau))
    if chi_tiet.empty or buoi.ma_buoi not in chi_tiet["Ma_buoi"].values:
        st.info("Chưa có dữ liệu.")
        return

    bang_buoi = chi_tiet[chi_tiet["Ma_buoi"] == buoi.ma_buoi]
    hien_bang(bang_buoi[["Ma_HV", "Ho_ten", "Check_in", "Check_out", "Phut_hoc", "Trang_thai", "Phuong_thuc_in"]])

    # B9: Xóa lượt bị nhận nhầm
    with st.expander("Xóa lượt điểm danh bị nhận nhầm"):
        da_check_in = bang_buoi[bang_buoi["Check_in"].notna()]
        if da_check_in.empty:
            st.caption("Chưa có lượt nào.")
        else:
            ma_xoa = st.selectbox("Lượt cần xóa", da_check_in["Ma_HV"], format_func=ten_day_du)
            if st.button("Xóa lượt này"):
                diem_danh.xoa_luot(ma_xoa, buoi.ma_buoi)
                st.success("Đã xóa")
                st.rerun()


# =====================================================================
# TRANG 3: LỊCH HỌC
# =====================================================================
def trang_lich_hoc():
    st.title("📅 Lịch học")
    lich = du_lieu.doc_lich_hoc()
    bay_gio = datetime.now()

    # B1: Hiển thị lịch học kèm cột Thứ và Tình trạng
    if not lich.empty:
        bang = lich.copy()
        ngay_chuoi = bang["Ngay"].dt.strftime("%Y-%m-%d")
        bat_dau = pd.to_datetime(ngay_chuoi + " " + bang["Gio_bat_dau"])
        ket_thuc = pd.to_datetime(ngay_chuoi + " " + bang["Gio_ket_thuc"])

        # Tình trạng: mặc định "Sắp tới", rồi sửa lại theo điều kiện bằng .loc
        bang["Tình trạng"] = "Sắp tới"
        bang.loc[ket_thuc < bay_gio, "Tình trạng"] = "Đã học"
        bang.loc[(bat_dau <= bay_gio) & (bay_gio <= ket_thuc), "Tình trạng"] = "Đang học"

        # Thứ trong tuần: dayofweek trả về số 0-6 -> map sang chữ bằng dictionary
        thu = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6", 5: "Thứ 7", 6: "Chủ nhật"}
        bang["Thứ"] = bang["Ngay"].dt.dayofweek.map(thu)
        bang["Ngay"] = bang["Ngay"].dt.strftime("%d/%m/%Y")

        bang = bang.rename(columns={"Gio_bat_dau": "Bắt đầu", "Gio_ket_thuc": "Kết thúc", "Phong": "Phòng"})
        hien_bang(bang[["Ma_buoi", "Thứ", "Ngay", "Bắt đầu", "Kết thúc", "Chu_de", "Phòng", "Tình trạng"]])

    # B2: Form thêm buổi học
    st.subheader("Thêm buổi học")
    with st.form("form_them_buoi", clear_on_submit=True):
        cot1, cot2, cot3 = st.columns(3)
        ma_buoi = cot1.text_input("Mã buổi", value=f"B{len(lich) + 1:02d}")
        ngay = cot2.date_input("Ngày", value=bay_gio.date())
        lop_mac_dinh = lich["Lop"].iloc[0] if not lich.empty else "CSDATA17"
        lop = cot3.text_input("Lớp", value=lop_mac_dinh)

        cot4, cot5, cot6 = st.columns(3)
        gio_bat_dau = cot4.time_input("Giờ bắt đầu", value=time(19, 0))
        gio_ket_thuc = cot5.time_input("Giờ kết thúc", value=time(21, 30))
        phong = cot6.text_input("Phòng", value="P.301")
        chu_de = st.text_input("Chủ đề")

        # Form chỉ gửi khi bấm nút submit
        if st.form_submit_button("Thêm buổi", type="primary"):
            if gio_ket_thuc <= gio_bat_dau:
                st.error("Giờ kết thúc phải sau giờ bắt đầu")
            else:
                buoi_moi = BuoiHoc(ma_buoi.strip().upper(), lop, ngay, gio_bat_dau, gio_ket_thuc, chu_de, phong)
                try:
                    du_lieu.them_buoi(buoi_moi)
                    st.success(f"Đã thêm buổi {ma_buoi}")
                    st.rerun()
                except ValueError as loi:            # bắt lỗi "mã buổi đã tồn tại"
                    st.error(str(loi))


# =====================================================================
# TRANG 4: HỌC VIÊN & KHUÔN MẶT
# =====================================================================
def trang_hoc_vien():
    st.title("👥 Học viên & khuôn mặt")
    tab_danh_sach, tab_them, tab_khuon_mat = st.tabs(["Danh sách", "Thêm học viên", "Đăng ký khuôn mặt"])
    hoc_vien = du_lieu.doc_hoc_vien()
    so_anh = khuon_mat.thong_ke_dang_ky()        # {"HV001": 5, ...}

    # ---------------- TAB 1: DANH SÁCH ----------------
    with tab_danh_sach:
        if hoc_vien.empty:
            st.info("Chưa có học viên.")
        else:
            bang = hoc_vien.copy()
            bang["Ảnh khuôn mặt"] = bang["Ma_HV"].map(lambda ma: so_anh.get(ma, 0))
            bang = bang.rename(columns={"Gioi_tinh": "Giới tính", "Ngay_sinh": "Ngày sinh",
                                        "SDT": "SĐT", "Lop": "Lớp"})
            hien_bang(bang)

            with st.expander("Xóa học viên"):
                ma_xoa = st.selectbox("Học viên", hoc_vien["Ma_HV"], format_func=ten_day_du, key="xoa_hv")
                if st.button("Xóa học viên và ảnh khuôn mặt"):
                    du_lieu.xoa_hoc_vien(ma_xoa)
                    khuon_mat.xoa_anh(ma_xoa)
                    st.success(f"Đã xóa {ma_xoa}. Nhớ huấn luyện lại model.")
                    st.rerun()

    # ---------------- TAB 2: THÊM HỌC VIÊN ----------------
    with tab_them:
        with st.form("form_them_hoc_vien", clear_on_submit=True):
            cot1, cot2 = st.columns(2)
            ma_hv = cot1.text_input("Mã học viên", value=f"HV{len(hoc_vien) + 1:03d}")
            ho_ten = cot2.text_input("Họ tên")
            cot3, cot4, cot5 = st.columns(3)
            gioi_tinh = cot3.selectbox("Giới tính", ["Nam", "Nữ", "Khác"])
            ngay_sinh = cot4.date_input("Ngày sinh", value=datetime(2000, 1, 1),
                                        min_value=datetime(1950, 1, 1), max_value=datetime.now())
            lop = cot5.text_input("Lớp", value="CSDATA17")
            cot6, cot7 = st.columns(2)
            email = cot6.text_input("Email")
            sdt = cot7.text_input("Số điện thoại")

            if st.form_submit_button("Thêm học viên", type="primary"):
                # B1: Kiểm tra dữ liệu nhập (validate), gom lỗi vào list
                danh_sach_loi = []
                if ho_ten.strip() == "":
                    danh_sach_loi.append("Họ tên không được để trống")
                if email != "" and "@" not in email:
                    danh_sach_loi.append("Email không hợp lệ")
                if sdt != "" and not (sdt.isdigit() and len(sdt) == 10):
                    danh_sach_loi.append("Số điện thoại phải gồm 10 chữ số")

                if len(danh_sach_loi) > 0:
                    for loi in danh_sach_loi:
                        st.error(loi)
                else:
                    # B2: Chuẩn hóa họ tên ("  nguyễn   văn an" -> "Nguyễn Văn An") rồi lưu
                    ho_ten_chuan = " ".join(ho_ten.split()).title()
                    hv_moi = HocVien(ma_hv.strip().upper(), ho_ten_chuan, gioi_tinh,
                                     ngay_sinh.strftime("%d/%m/%Y"), email.strip(), sdt.strip(), lop)
                    try:
                        du_lieu.them_hoc_vien(hv_moi)
                        st.success(f"Đã thêm {ho_ten_chuan}. Sang tab Đăng ký khuôn mặt để chụp ảnh.")
                    except ValueError as loi:
                        st.error(str(loi))

    # ---------------- TAB 3: ĐĂNG KÝ KHUÔN MẶT ----------------
    with tab_khuon_mat:
        if not khuon_mat.co_opencv():
            st.error(tinh_trang)
            return

        st.info(f"Mỗi học viên chụp **ít nhất {config.SO_ANH_TOI_THIEU} ảnh** (nên 5–10 ảnh): "
                "nhìn thẳng, hơi nghiêng trái/phải, có/không đeo kính, ánh sáng khác nhau. "
                "Sau khi đăng ký xong cho mọi người, bấm **Huấn luyện model**.")
        st.caption("🔒 Ảnh khuôn mặt là dữ liệu cá nhân nhạy cảm: chỉ chụp khi học viên đồng ý, "
                   "ảnh chỉ lưu trên máy này (thư mục data/faces).")
        if hoc_vien.empty:
            st.warning("Chưa có học viên.")
            return

        # B1: Chọn học viên cần đăng ký
        ma_hv = st.selectbox("Học viên", hoc_vien["Ma_HV"], key="hv_khuon_mat",
                             format_func=lambda ma: f"{ten_day_du(ma)} ({so_anh.get(ma, 0)} ảnh)")

        # B2: Chọn nguồn ảnh: chụp bằng camera hoặc tải ảnh có sẵn
        nguon = st.radio("Nguồn ảnh", ["Camera", "Tải ảnh lên"], horizontal=True)
        danh_sach_anh = []
        if nguon == "Camera":
            # key có số ảnh hiện tại -> chụp xong 1 ảnh thì camera tự làm mới để chụp ảnh tiếp
            anh = st.camera_input("Chụp ảnh đăng ký", key=f"dang_ky_{ma_hv}_{khuon_mat.so_anh(ma_hv)}")
            if anh is not None:
                danh_sach_anh.append(anh)
        else:
            anh_tai_len = st.file_uploader("Chọn ảnh (jpg/png)", type=["jpg", "jpeg", "png"],
                                           accept_multiple_files=True, key=f"tai_len_{ma_hv}")
            if anh_tai_len and st.button(f"Lưu {len(anh_tai_len)} ảnh"):
                danh_sach_anh = anh_tai_len

        # B3: Lưu từng ảnh
        for anh in danh_sach_anh:
            thanh_cong, thong_bao, anh_hien_thi = khuon_mat.dang_ky(ma_hv, anh.getvalue())
            if thanh_cong:
                st.success(thong_bao)
            else:
                st.warning(thong_bao)
            st.image(anh_hien_thi, width=320)

        # B4: Huấn luyện model / xóa ảnh
        cot1, cot2 = st.columns(2)
        if cot1.button("🧠 Huấn luyện model", type="primary", width="stretch"):
            with st.spinner("Đang huấn luyện..."):
                thanh_cong, thong_bao = khuon_mat.huan_luyen()
            if thanh_cong:
                st.success(thong_bao)
            else:
                st.error(thong_bao)
        if cot2.button(f"🗑️ Xóa ảnh của {ma_hv}", width="stretch"):
            khuon_mat.xoa_anh(ma_hv)
            st.success("Đã xóa. Nhớ huấn luyện lại model.")
            st.rerun()


# =====================================================================
# TRANG 5: THỐNG KÊ & BÁO CÁO
# =====================================================================
def trang_thong_ke():
    st.title("📊 Thống kê chuyên cần & báo cáo")

    # B1: Tính 3 bảng
    chi_tiet = diem_danh.bang_chi_tiet(datetime.now())
    if chi_tiet.empty:
        st.info("Chưa có buổi học nào diễn ra.")
        return
    tong_hop_hv = diem_danh.tong_hop_hoc_vien(chi_tiet)
    tong_hop_buoi = diem_danh.tong_hop_buoi(chi_tiet)

    # B2: 4 ô số liệu
    cot1, cot2, cot3, cot4 = st.columns(4)
    cot1.metric("Số buổi đã tính", tong_hop_buoi["Ma_buoi"].nunique())
    cot2.metric("Tỉ lệ có mặt trung bình", f"{tong_hop_buoi['Ti_le_co_mat'].mean():.0%}")
    cot3.metric("Tổng lượt vắng", int(tong_hop_hv["Vang"].sum()))
    cot4.metric("Học viên bị cảnh báo", int((tong_hop_hv["Canh_bao"] != "").sum()))

    # B3: 4 tab
    tab1, tab2, tab3, tab4 = st.tabs(["Theo học viên", "Theo buổi", "Chi tiết", "Biểu đồ"])

    with tab1:
        chi_canh_bao = st.toggle("Chỉ hiện học viên bị cảnh báo")
        bang = tong_hop_hv
        if chi_canh_bao:
            bang = tong_hop_hv[tong_hop_hv["Canh_bao"] != ""]
        hien_bang(bang, thanh_ti_le("Tỉ lệ chuyên cần"))

    with tab2:
        bang = tong_hop_buoi.copy()
        bang["Ngay"] = pd.to_datetime(bang["Ngay"]).dt.strftime("%d/%m/%Y")
        hien_bang(bang, thanh_ti_le("Tỉ lệ có mặt"))

    with tab3:
        # Lọc theo học viên và trạng thái (multiselect trả về list)
        cot_a, cot_b = st.columns(2)
        loc_hv = cot_a.multiselect("Lọc học viên", sorted(chi_tiet["Ma_HV"].unique()), format_func=ten_day_du)
        loc_trang_thai = cot_b.multiselect("Lọc trạng thái", sorted(chi_tiet["Trang_thai"].unique()))
        bang = chi_tiet
        if len(loc_hv) > 0:
            bang = bang[bang["Ma_HV"].isin(loc_hv)]
        if len(loc_trang_thai) > 0:
            bang = bang[bang["Trang_thai"].isin(loc_trang_thai)]
        hien_bang(bang[["Ma_buoi", "Ngay", "Ma_HV", "Ho_ten", "Check_in", "Check_out",
                        "Phut_tre", "Phut_ve_som", "Phut_hoc", "Trang_thai"]])

    with tab4:
        st.pyplot(bieu_do_ti_le_theo_buoi(tong_hop_buoi))
        st.pyplot(bieu_do_vang_theo_hoc_vien(tong_hop_hv))
        st.pyplot(bieu_do_trang_thai(diem_danh.dem_trang_thai(chi_tiet)))

    # B4: Nút tải báo cáo Excel (tạo file trong bộ nhớ bằng BytesIO, không ghi ra ổ cứng)
    st.divider()
    file_excel = xuat_bao_cao(tong_hop_hv, tong_hop_buoi, chi_tiet, BytesIO())
    st.download_button(
        "📥 Tải báo cáo Excel",
        data=file_excel.getvalue(),
        file_name=f"bao_cao_chuyen_can_{datetime.now():%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


# =====================================================================
# PHẦN CUỐI: CHẠY TRANG ĐƯỢC CHỌN
# Dictionary: tên trang -> hàm của trang đó (tên hàm KHÔNG có ngoặc = chưa chạy)
# Lấy hàm theo trang đang chọn, rồi thêm () để chạy
# =====================================================================
cac_trang = {
    "🏠 Tổng quan": trang_tong_quan,
    "📷 Điểm danh": trang_diem_danh,
    "📅 Lịch học": trang_lich_hoc,
    "👥 Học viên & khuôn mặt": trang_hoc_vien,
    "📊 Thống kê & báo cáo": trang_thong_ke,
}
cac_trang[trang]()
