from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3, requests, uvicorn
from datetime import datetime
import os

app = FastAPI()

# ================= CÂY CẦU CORS =================
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
    # Bảng chứa thông tin User
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, balance INTEGER, vip_expire TEXT, is_banned INTEGER)''')
    
    # Tài khoản Admin Boss (VIP vĩnh viễn)
    c.execute("INSERT OR IGNORE INTO users (username, password, balance, vip_expire, is_banned) VALUES (?, ?, ?, ?, ?)", 
              ('hungadmin11', 'hungki98', 999999999, '2099-12-31 23:59:59', 0))
    # Tài khoản Khách test
    c.execute("INSERT OR IGNORE INTO users (username, password, balance, vip_expire, is_banned) VALUES (?, ?, ?, ?, ?)", 
              ('khachvip', '123456', 0, '2026-12-31 23:59:59', 0))
    conn.commit()
    conn.close()

khoi_tao_db()

# ================= THUẬT TOÁN AI BẺ CẦU =================
def phan_tich_ai(kq_list):
    if len(kq_list) < 5: 
        return {"du_doan": "WAIT", "ti_le": 0}
    
    kq_cuoi = kq_list[-1]
    chuoi = 1
    for i in range(len(kq_list)-2, -1, -1):
        if kq_list[i] == kq_cuoi: chuoi += 1
        else: break
        
    du_doan = "TÀI" if kq_cuoi == "Xỉu" else "XỈU"
    ty_le = min(60 + chuoi * 4, 99) if chuoi >= 3 else 75.0
    return {"du_doan": du_doan, "ti_le": round(ty_le, 1)}

# ================= CỔNG NHẬN LỆNH TỪ MẶT TIỀN HTML =================
@app.get("/api/scan")
def scan_game(username: str, tool: str = "lc79"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT vip_expire, is_banned FROM users WHERE username = ?", (username,))
    khach = c.fetchone()
    conn.close()
    
    if not khach: 
        return {"status": "error", "msg": "Tài khoản không tồn tại!"}
    if khach[1] == 1 and username != "hungadmin11": 
        return {"status": "error", "msg": "Tài khoản đã bị khóa mõm!"}
    
    han_vip = datetime.strptime(khach[0], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > han_vip and username != "hungadmin11": 
        return {"status": "error", "msg": "Gói VIP hết hạn! Vui lòng nạp thêm."}

    url = "https://wtx.tele68.com/v1/tx/lite-sessions" if tool == "lc79" else "https://wtx.macminim6.online/v1/tx/lite-sessions"
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        if not res.get("list"): 
            return {"status": "error", "msg": "Chờ cầu mới..."}
        
        lst = res["list"][::-1]
        kq_game = ["Tài" if "TAI" in str(s.get("resultTruyenThong", "")).upper() else "Xỉu" for s in lst]
        data_ai = phan_tich_ai(kq_game)
        
        return {"status": "success", "data": data_ai}
    except Exception as e: 
        return {"status": "error", "msg": "Đứt cáp API nhà cái!"}

# ================= KÍCH NỔ ĐỘNG CƠ (BÍ QUYẾT TRỊ RAILWAY) =================
if __name__ == "__main__":
    # Lấy cổng tự động do Railway cấp phát, không ép cứng 8000 nữa
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 SIÊU HỆ THỐNG AI ĐANG CHẠY TẠI CỔNG {port}...")
    uvicorn.run("server_ai:app", host="0.0.0.0", port=port)
    
