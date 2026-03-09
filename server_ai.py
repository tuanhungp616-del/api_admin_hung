from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, uvicorn, sqlite3, os
from datetime import datetime, timedelta

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
DB_FILE = "hethong_vip.db"

def khoi_tao_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keys (apikey TEXT PRIMARY KEY, expire_date DATETIME)''')
    c.execute("INSERT OR IGNORE INTO keys (apikey, expire_date) VALUES (?, ?)", ('hungadmin', '2099-12-31 23:59:59'))
    conn.commit()
    conn.close()

khoi_tao_db()

def phan_tich_ai(kq_list):
    tong_tai = kq_list.count("Tài")
    tong_xiu = kq_list.count("Xỉu")
    
    if len(kq_list) < 5: 
        return {"du_doan": "WAIT", "ti_le": 0, "loi_khuyen": "Đang nạp Data...", "trend": "...", "kieu_cau": "SCANNING", "tong_tai": tong_tai, "tong_xiu": tong_xiu}
    
    kq_cuoi = kq_list[-1]
    chuoi = 1
    for i in range(len(kq_list)-2, -1, -1):
        if kq_list[i] == kq_cuoi: chuoi += 1
        else: break
    
    du_doan = "TÀI" if kq_cuoi == "Xỉu" else "XỈU"
    ty_le = 50.0
    kieu_cau = "PHÂN TÍCH MARKOV PRO"
    last_4 = ",".join(kq_list[-4:])
    last_5 = ",".join(kq_list[-5:])

    if chuoi >= 6: du_doan, ty_le, kieu_cau = ("XỈU" if kq_cuoi == "Tài" else "TÀI", 75.0, f"🚨 CẢNH BÁO BẺ ({chuoi} TAY)")
    elif chuoi >= 4: du_doan, ty_le, kieu_cau = (kq_cuoi.upper(), min(80 + chuoi * 2.5, 99.9), f"🔥 ĐANG BỆT {chuoi} TAY")
    elif last_4 in ["Tài,Xỉu,Tài,Xỉu", "Xỉu,Tài,Xỉu,Tài"]: du_doan, ty_le, kieu_cau = ("TÀI" if kq_cuoi == "Xỉu" else "XỈU", 88.0, "⚡ CẦU 1-1 (PING-PONG)")
    elif last_4 in ["Tài,Tài,Xỉu,Xỉu", "Xỉu,Xỉu,Tài,Tài"]: du_doan, ty_le, kieu_cau = (kq_cuoi.upper(), 85.0, "⚖️ CẦU 2-2 NHỊP ĐỀU")
    elif last_5 in ["Tài,Tài,Tài,Xỉu,Tài", "Xỉu,Xỉu,Xỉu,Tài,Xỉu"]: du_doan, ty_le, kieu_cau = (kq_cuoi.upper(), 82.0, "🎯 CẦU 3-1-3 CHUẨN")
    else:
        t = {"Tài_Tài": 0, "Tài_Xỉu": 0, "Xỉu_Xỉu": 0, "Xỉu_Tài": 0}
        for i in range(len(kq_list) - 1): t[f"{kq_list[i]}_{kq_list[i+1]}"] += 1
        tong = max(1, (t["Tài_Tài"] + t["Tài_Xỉu"]) if kq_cuoi == "Tài" else (t["Xỉu_Tài"] + t["Xỉu_Xỉu"]))
        tl_tai = (t["Tài_Tài"]/tong)*100 if kq_cuoi == "Tài" else (t["Xỉu_Tài"]/tong)*100
        tl_xiu = (t["Tài_Xỉu"]/tong)*100 if kq_cuoi == "Tài" else (t["Xỉu_Xỉu"]/tong)*100
        du_doan = "TÀI" if tl_tai > tl_xiu else "XỈU"
        ty_le = round(max(tl_tai, tl_xiu), 1)

    kelly = max(1, round(((2 * (ty_le/100) - 1) * 100) / 3))
    if chuoi >= 6: loi_khuyen = f"🛑 GẤP THẾP BẺ CẦU {kelly}% VỐN"
    elif ty_le >= 80: loi_khuyen = f"🚀 CẦU ĐẸP -> VÀO {kelly}% VỐN"
    elif ty_le >= 60: loi_khuyen = f"💰 ĐÁNH ĐỀU {kelly}% VỐN"
    else: loi_khuyen = f"⚠️ CẦU LOẠN -> DÒ ĐƯỜNG 1%"

    radar = "".join(["🔴" if x == "Tài" else "🔵" for x in kq_list[-12:]])
    return {"du_doan": du_doan, "ti_le": ty_le, "loi_khuyen": loi_khuyen, "trend": radar, "kieu_cau": kieu_cau, "tong_tai": tong_tai, "tong_xiu": tong_xiu}

@app.get("/api/scan")
async def scan_game(tool: str, apikey: str):
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("SELECT expire_date FROM keys WHERE apikey = ?", (apikey,)); row = c.fetchone()
    conn.close()
    if not row: return {"status": "error", "msg": "Key không tồn tại!"}
    if datetime.now() > datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S"): return {"status": "error", "msg": "Key hết hạn!"}

    if tool == "lc79":
        api_url = "https://wtx.tele68.com/v1/tx/lite-sessions"
    elif tool == "vip":
        api_url = "https://wtx.macminim6.online/v1/tx/lite-sessions"
    elif tool == "md5vip":
        api_url = "https://wtxmd52.macminim6.online/v1/tx/lite-sessions"
    else: return {"status": "error", "msg": "Mã Tool không hợp lệ!"}

    try:
        res = requests.get(api_url, headers={"User-Agent": "Chrome/120.0"}, timeout=5).json()
        if not res.get("list"): return {"status": "error", "msg": "Đang chờ cầu mới..."}
        lst = res["list"][::-1]
        kq = ["Tài" if "TAI" in str(s.get("resultTruyenThong", "")).upper() else "Xỉu" for s in lst]
        data = phan_tich_ai(kq); data["phien"] = str(int(lst[-1]["id"]) + 1)
        return {"status": "success", "data": data}
    except Exception as e: return {"status": "error", "msg": "Bảo trì hoặc Sai Link MD5"}

class MD5Req(BaseModel):
    md5_str: str
    ai_du_doan: str
    ai_ti_le: float

@app.post("/api/analyze_md5")
async def analyze_md5_logic(req: MD5Req):
    md5_str = req.md5_str.strip()
    if len(md5_str) < 10: return {"status": "error", "msg": "Chuỗi MD5 không hợp lệ!"}
    ascii_sum = sum(ord(c) for c in md5_str)
    is_md5_tai = (ascii_sum % 2 == 0)
    is_ai_tai = (req.ai_du_doan == "TÀI")
    
    if is_md5_tai == is_ai_tai:
        final_result = req.ai_du_doan
        final_rate = min(99.0, req.ai_ti_le + 12.5)
        final_advice = "🚀 CỘNG HƯỞNG MD5 -> VÀO MẠNH TAY"
    else:
        final_result = "TÀI" if is_md5_tai else "XỈU"
        final_rate = max(55.0, req.ai_ti_le - 15.2)
        final_advice = "⚠️ XUNG ĐỘT MD5 -> DÒ ĐƯỜNG NHẸ"
        
    return {
        "status": "success",
        "data": { "du_doan": final_result, "ti_le": round(final_rate, 1), "loi_khuyen": final_advice }
    }

class KeyReq(BaseModel): admin_key: str; new_key: str; duration: str
class DelReq(BaseModel): admin_key: str; target_key: str

@app.post("/api/admin/create")
async def create_new_key(req: KeyReq):
    if req.admin_key != "hungadmin": return {"status": "error", "msg": "Không có quyền!"}
    now = datetime.now()
    if req.duration == "1H": exp = now + timedelta(hours=1)
    elif req.duration == "1D": exp = now + timedelta(days=1)
    elif req.duration == "3D": exp = now + timedelta(days=3)
    elif req.duration == "1M": exp = now + timedelta(days=30)
    else: return {"status": "error"}
    try:
        conn = sqlite3.connect(DB_FILE); c = conn.cursor()
        c.execute("INSERT INTO keys VALUES (?, ?)", (req.new_key, exp.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
        return {"status": "success"}
    except: return {"status": "error", "msg": "Key đã tồn tại!"}

@app.get("/api/admin/list")
async def list_keys(apikey: str):
    if apikey != "hungadmin": return {"status": "error"}
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("SELECT apikey, expire_date FROM keys ORDER BY expire_date DESC"); keys = c.fetchall(); conn.close()
    return {"status": "success", "data": [{"key": k[0], "exp": k[1]} for k in keys]}

@app.post("/api/admin/delete")
async def delete_key(req: DelReq):
    if req.admin_key != "hungadmin" or req.target_key == "hungadmin": return {"status": "error"}
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("DELETE FROM keys WHERE apikey = ?", (req.target_key,)); conn.commit(); conn.close()
    return {"status": "success"}

# ==========================================
# KHỐI HTML NÉN TRỰC TIẾP VÀO TRONG PYTHON
# ==========================================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>CYBER DORAEMON - HƯNG ADMIN</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #00a6f0; --secondary: #ff0000; --accent: #ffeb3b; --dark-bg: #071526; }
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        body { font-family: 'Rajdhani', sans-serif; background: var(--dark-bg); color: #fff; overflow-x: hidden; min-height: 100vh; }
        #quantum-network { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -1; opacity: 0.6; }
        header { padding: 15px 20px; background: rgba(0,0,0,0.8); border-bottom: 2px solid var(--primary); display: flex; justify-content: space-between; align-items: center; z-index: 10; position: relative; box-shadow: 0 0 15px var(--primary);}
        .logo { display: flex; align-items: center; gap: 10px; font-family: 'Orbitron', sans-serif; font-size: 20px; font-weight: 900; color: var(--primary); text-shadow: 0 0 10px var(--primary); }
        .status-badge { background: rgba(0, 166, 240, 0.2); border: 1px solid var(--primary); padding: 5px 10px; border-radius: 20px; font-size: 12px; animation: pulse 2s infinite; font-weight: bold;}
        #login-wrapper { position: fixed; top: 0; left: 0; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; z-index: 50; backdrop-filter: blur(8px); background: rgba(7, 21, 38, 0.85); }
        .login-box { background: rgba(0, 166, 240, 0.05); border: 2px solid var(--primary); border-radius: 15px; padding: 30px; width: 90%; max-width: 400px; text-align: center; box-shadow: 0 0 30px rgba(0,166,240,0.3); backdrop-filter: blur(10px); }
        #main-dashboard { display: none; grid-template-columns: 1fr 2fr 1fr; gap: 20px; padding: 20px; z-index: 1; position: relative; }
        @media (max-width: 900px) { #main-dashboard { grid-template-columns: 1fr; } }
        .panel { background: rgba(0,0,0,0.6); border: 1px solid rgba(0, 166, 240, 0.3); border-radius: 15px; padding: 20px; position: relative; box-shadow: inset 0 0 20px rgba(0,0,0,0.8); display: flex; flex-direction: column; }
        .panel-title { font-family: 'Orbitron', sans-serif; font-size: 16px; color: var(--accent); margin-bottom: 15px; border-bottom: 1px dashed rgba(255,255,255,0.2); padding-bottom: 10px; display: flex; align-items: center; justify-content: center; gap: 10px; text-shadow: 0 0 5px var(--accent);}
        .cyber-btn { background: rgba(0,0,0,0.5); border: 2px solid var(--primary); color: var(--primary); padding: 12px; font-family: 'Orbitron', sans-serif; font-size: 14px; cursor: pointer; transition: 0.3s; border-radius: 8px; font-weight: bold; width: 100%; outline: none; margin-bottom: 10px; text-transform: uppercase;}
        .cyber-btn:hover { background: var(--primary); color: #000; box-shadow: 0 0 15px var(--primary); }
        .cyber-btn:active { transform: scale(0.95); }
        .input-box { width: 100%; padding: 12px; background: rgba(0,0,0,0.8); border: 2px solid var(--primary); color: #fff; border-radius: 8px; font-family: monospace; font-size: 16px; text-align: center; margin-bottom: 15px; outline: none; }
        .input-box:focus { box-shadow: 0 0 15px var(--primary); }
        .radar-container { flex-grow: 1; display: flex; justify-content: center; align-items: center; position: relative; min-height: 220px; margin: 20px 0; }
        .radar { width: 200px; height: 200px; border-radius: 50%; border: 3px solid rgba(0, 166, 240, 0.3); position: absolute; box-shadow: 0 0 30px rgba(0, 166, 240, 0.2); transition: 0.3s; }
        .radar.spin::before { content: ''; position: absolute; top: 50%; left: 50%; width: 100%; height: 100%; border-radius: 50%; border-top: 3px solid var(--primary); transform-origin: top left; animation: spin 2s linear infinite; background: conic-gradient(from 0deg, rgba(0,166,240,0.5) 0deg, transparent 60deg); }
        .core-text { position: absolute; z-index: 5; font-family: 'Orbitron'; font-size: 45px; font-weight: 900; color: #fff; text-shadow: 0 0 20px var(--primary); letter-spacing: 2px; }
        .txt-tai { color: var(--secondary); text-shadow: 0 0 30px var(--secondary); }
        .txt-xiu { color: var(--primary); text-shadow: 0 0 30px var(--primary); }
        .data-row { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 5px;}
        .data-value { color: var(--primary); font-family: monospace; font-size: 18px; font-weight: bold; }
        .terminal { background: rgba(0,0,0,0.8); border-radius: 8px; padding: 15px; min-height: 150px; font-family: monospace; font-size: 12px; color: var(--primary); display: flex; flex-direction: column; justify-content: flex-end; border: 1px solid #333; overflow: hidden;}
        .log-line { margin-bottom: 4px; animation: fadeIn 0.3s forwards; }
        .log-error { color: var(--secondary); } .log-warn { color: var(--accent); }
        .admin-modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); display: none; justify-content: center; align-items: center; z-index: 999; }
        .admin-box { background: var(--dark-bg); border: 2px solid var(--accent); width: 90%; max-width: 450px; padding: 25px; border-radius: 15px; position: relative; }
        .close-btn { position: absolute; top: 5px; right: 15px; color: var(--secondary); font-size: 30px; cursor: pointer; font-weight: bold; }
        .key-list { margin-top: 15px; max-height: 200px; overflow-y: auto; border-top: 1px dashed #555; padding-top: 10px; }
        .key-item { display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.05); padding: 10px; border-radius: 5px; margin-bottom: 5px; border: 1px solid #333;}
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(0, 166, 240, 0.5); } 70% { box-shadow: 0 0 0 10px rgba(0, 166, 240, 0); } 100% { box-shadow: 0 0 0 0 rgba(0, 166, 240, 0); } }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px);} to { opacity: 1; transform: translateY(0);} }
    </style>
</head>
<body>
    <canvas id="quantum-network"></canvas>
    <header>
        <div class="logo">
            <img src="https://i.postimg.cc/WbVPf3MB/1773017145274.png" style="height: 45px; border-radius: 8px; box-shadow: 0 0 15px var(--primary);">
            DORAEMON SYSTEM
        </div>
        <div class="status-badge" id="header-status"><i class="fas fa-lock"></i> SYSTEM LOCKED</div>
    </header>

    <div id="login-wrapper">
        <div class="login-box">
            <div class="panel-title" style="border: none; font-size: 22px; color: var(--primary);"><i class="fas fa-fingerprint"></i> XÁC THỰC QUYỀN</div>
            <input type="text" id="key-input" class="input-box" placeholder="Nhập Key Kích Hoạt..." autocomplete="off">
            <button class="cyber-btn" style="background: rgba(0,166,240,0.2);" onclick="login()">KÍCH HOẠT BẢO BỐI</button>
            <div id="login-err" style="color: var(--secondary); margin-top: 15px; font-weight:bold; display:none; text-shadow: 0 0 10px var(--secondary);">❌</div>
        </div>
    </div>

    <div class="admin-modal" id="admin-modal">
        <div class="admin-box">
            <div class="close-btn" onclick="closeAdmin()">×</div>
            <div class="panel-title" style="color: var(--accent); font-size: 20px;"><i class="fas fa-crown"></i> QUYỀN LỰC ÔNG TRÙM</div>
            <div style="display: flex; gap: 10px; margin-top: 15px;">
                <input type="text" id="new-key-name" class="input-box" style="flex: 2; margin-bottom: 0;" placeholder="Tên Key Khách...">
                <select id="new-key-time" class="input-box" style="flex: 1; margin-bottom: 0; background: #111;">
                    <option value="1H">1 Giờ</option><option value="1D">1 Ngày</option>
                    <option value="3D">3 Ngày</option><option value="1M">1 Tháng</option>
                </select>
            </div>
            <button class="cyber-btn" style="border-color: var(--accent); color: var(--accent); margin-top: 15px;" onclick="createKey()">TẠO KEY MỚI</button>
            <div id="admin-msg" style="text-align: center; margin-top: 10px; font-weight: bold;"></div>
            <div class="key-list" id="key-list"></div>
        </div>
    </div>

    <div id="main-dashboard">
        <div class="panel">
            <div class="panel-title"><i class="fas fa-server"></i> TỌA ĐỘ SERVER</div>
            <button class="cyber-btn" onclick="openTool('lc79')">📡 LC79.BET</button>
            <button class="cyber-btn" style="border-color: var(--accent); color: var(--accent);" onclick="openTool('md5vip')">🔮 MD5 ALL GAME</button>
            <button class="cyber-btn" style="border-color: #00ffaa; color: #00ffaa;" onclick="openTool('vip')">👑 BET VIP</button>
            <button id="btn-admin" class="cyber-btn" style="display: none; margin-top: 10px; border-color: var(--secondary); color: var(--secondary); background: rgba(255,0,0,0.1);" onclick="openAdmin()"><i class="fas fa-user-shield"></i> QUẢN LÝ KEY KHÁCH</button>
            <div style="margin-top: 15px;">
                <div class="data-row"><span class="data-label">PHIÊN KẾ TẾP</span><span class="data-value" id="t-phien" style="color:#fff;">...</span></div>
                <div class="data-row"><span class="data-label">TỔNG TÀI</span><span class="data-value" style="color:var(--secondary)" id="stat-tai">0</span></div>
                <div class="data-row"><span class="data-label">TỔNG XỈU</span><span class="data-value" id="stat-xiu">0</span></div>
            </div>
            <button class="cyber-btn" style="margin-top: 15px; border-color: #555; color: #aaa;" onclick="logout()"><i class="fas fa-power-off"></i> ĐĂNG XUẤT</button>
        </div>

        <div class="panel" style="text-align: center;">
            <div class="panel-title"><i class="fas fa-microchip"></i> LÕI AI PHÂN TÍCH</div>
            <div style="background: rgba(0,0,0,0.4); padding: 15px; border-radius: 10px; border: 1px dashed var(--accent);">
                <div style="font-size: 12px; color: var(--accent); margin-bottom: 8px; font-weight:bold;">GIẢI MÃ CHUỖI MD5</div>
                <input type="text" id="md5-input" class="input-box" style="border-color: var(--accent); color: var(--accent);" placeholder="Dán mã MD5 vào đây...">
                <button class="cyber-btn" style="border-color: var(--accent); color: var(--accent); margin-bottom: 0;" onclick="analyzeMD5()"><i class="fas fa-fingerprint"></i> PHÂN TÍCH KẾT HỢP</button>
            </div>
            <div class="radar-container">
                <div class="radar" id="radar-ring"></div>
                <div class="core-text" id="t-kq">WAIT</div>
            </div>
            <div style="color:var(--primary); font-size: 20px; font-weight: 900; font-family:'Orbitron';" id="t-tyle-text">TỶ LỆ WIN: 0%</div>
            <div id="t-loikhuyen" style="color: var(--accent); font-size: 16px; font-weight: bold; margin-top: 8px; text-shadow: 0 0 10px rgba(255, 235, 59, 0.5);">Chỉ thị: Vui lòng chọn Server...</div>
            <div style="font-size: 12px; color: #8892b0; margin-top: 15px; letter-spacing: 2px;">RADAR 12 TAY GẦN NHẤT</div>
            <div id="t-radar" style="font-size: 18px; letter-spacing: 5px; margin-top: 5px; background: rgba(0,0,0,0.5); padding: 5px; border-radius: 5px;">...</div>
        </div>

        <div class="panel">
            <div class="panel-title"><i class="fas fa-terminal"></i> NHẬT KÝ HỆ THỐNG</div>
            <div class="terminal" id="terminal-box"></div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('quantum-network'); const ctx = canvas.getContext('2d');
        let width = canvas.width = window.innerWidth; let height = canvas.height = window.innerHeight;
        const particles = []; const props = { particleColor: 'rgba(0, 166, 240, 1)', particleCount: 60, maxVel: 0.8, lineLen: 150 };
        class Particle {
            constructor() { this.x = Math.random() * width; this.y = Math.random() * height; this.vx = (Math.random() * props.maxVel * 2) - props.maxVel; this.vy = (Math.random() * props.maxVel * 2) - props.maxVel; }
            update() { this.x += this.vx; this.y += this.vy; if(this.x > width || this.x < 0) this.vx *= -1; if(this.y
