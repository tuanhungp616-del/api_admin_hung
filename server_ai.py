from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3, requests, uvicorn
from datetime import datetime

app = FastAPI()

# ================= CÂY CẦU CORS =================
# Cho phép file Mặt Tiền (HTML) được phép kết nối vào rút dữ liệu
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= KÉT SẮT TỰ ĐỘNG =================
DB_NAME = "hethong_vip.db"

def khoi_tao_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tạo bảng chứa User
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, balance INTEGER, vip_expire TEXT, is_banned INTEGER)''')
    
    # Tự động tạo tài khoản Trùm (hungadmin11) có VIP đến năm 2099
    c.execute("INSERT OR IGNORE INTO users (username, password, balance, vip_expire, is_banned) VALUES (?, ?, ?, ?, ?)", 
              ('hungadmin11', 'hungki98', 999999999, '2099-12-31 23:59:59', 0))
    # Tạo sẵn 1 tài khoản test cho khách
    c.execute("INSERT OR IGNORE INTO users (username, password, balance, vip_expire, is_banned) VALUES (?, ?, ?, ?, ?)", 
              ('khachvip', '123456', 0, '2026-12-31 23:59:59', 0))
    conn.commit()
    conn.close()

# Chạy đúc Két Sắt ngay khi khởi động
khoi_tao_db()

# ================= THUẬT TOÁN AI SO LÝ LỊCH CẦU =================
def phan_tich_ai(kq_list):
    if len(kq_list) < 5: 
        return {"du_doan": "WAIT", "ti_le": 0}
    
    kq_cuoi = kq_list[-1]
    chuoi = 1
    # Đếm xem cầu đang bệt mấy tay
    for i in range(len(kq_list)-2, -1, -1):
        if kq_list[i] == kq_cuoi: chuoi += 1
        else: break
        
    # Công thức bẻ cầu: Bệt dài thì bẻ ngược lại
    du_doan = "TÀI" if kq_cuoi == "Xỉu" else "XỈU"
    ty_le = min(60 + chuoi * 4, 99) if chuoi >= 3 else 75.0
    return {"du_doan": du_doan, "ti_le": round(ty_le, 1)}

# ================= CỔNG TIẾP NHẬN YÊU CẦU TỪ MẶT TIỀN =================
@app.get("/api/scan")
def scan_game(username: str, tool: str = "lc79"):
    # 1. BẢO VỆ KÉT SẮT: Kiểm tra xem User này có tồn tại không?
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT vip_expire, is_banned FROM users WHERE username = ?", (username,))
    khach = c.fetchone()
    conn.close()
    
    if not khach: 
        return {"status": "error", "msg": "Tài khoản không tồn tại trong hệ thống!"}
    if khach[1] == 1 and username != "hungadmin11": 
        return {"status": "error", "msg": "Tài khoản đã bị Admin khóa mõm!"}
    
    # Kiểm tra hạn VIP
    han_vip = datetime.strptime(khach[0], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > han_vip and username != "hungadmin11": 
        return {"status": "error", "msg": "Gói VIP đã hết hạn! Vui lòng nạp thêm."}

    # 2. ĐIỆN BÁO MÁY CHỦ NHÀ CÁI
    url = "https://wtx.tele68.com/v1/tx/lite-sessions" if tool == "lc79" else "https://wtx.macminim6.online/v1/tx/lite-sessions"
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        if not res.get("list"): 
            return {"status": "error", "msg": "Chờ cầu mới..."}
        
        # Lấy danh sách kết quả (từ cũ đến mới)
        lst = res["list"][::-1]
        kq_game = ["Tài" if "TAI" in str(s.get("resultTruyenThong", "")).upper() else "Xỉu" for s in lst]
        
        # Đưa vào AI phân tích
        data_ai = phan_tich_ai(kq_game)
        
        # Trả số liệu về cho HTML hiển thị
        return {"status": "success", "data": data_ai}
    except Exception as e: 
        return {"status": "error", "msg": "Lỗi đứt cáp API nhà cái!"}

# ================= KÍCH NỔ ĐỘNG CƠ =================
if __name__ == "__main__":
    print("🚀 SIÊU HỆ THỐNG AI ĐÃ KHỞI ĐỘNG TẠI CỔNG 8000...")
    uvicorn.run("server_ai:app", host="0.0.0.0", port=8000, reload=True)
    
