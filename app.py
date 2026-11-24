import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo
import re
import secrets
import json
import io
import hashlib
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

st.set_page_config(page_title="今日午餐點餐系統", page_icon="🍱", layout="centered")
st.title("🍱 今日午餐點餐小幫手")
st.caption(f"點餐日期：{datetime.now(ZoneInfo('Asia/Taipei')):%Y-%m-%d}")

# 使用 Supabase 儲存訂單。資料庫錯誤會直接顯示在畫面。
class StorageError(Exception):
    pass


def database_request(method, endpoint, payload=None, prefer=None):
    try:
        config = st.secrets["supabase"]
        base_url = str(config["url"]).strip().rstrip("/")
        secret_key = str(config["secret_key"]).strip()
    except (KeyError, FileNotFoundError):
        raise StorageError("尚未設定資料庫，請先在 Streamlit Settings → Secrets 填入 Supabase 設定。") from None
    parsed = urlsplit(base_url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.path
            or parsed.query or parsed.fragment or parsed.username or parsed.password):
        raise StorageError("Supabase URL 格式不正確，請填入完整的 https://專案代碼.supabase.co。")
    if not secret_key.startswith("sb_secret_"):
        raise StorageError("請在 Secrets 填入 Supabase 後端專用的 sb_secret_ 金鑰。")
    headers = {"apikey": secret_key, "Content-Type": "application/json", "Accept": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = Request(base_url + "/rest/v1/" + endpoint, data=data, headers=headers, method=method)
    try:
        # 不自動重試寫入：網路中斷時先確認資料，避免重複點餐。
        with urlopen(request, timeout=20) as response:
            body = response.read()
        return json.loads(body) if body else None
    except HTTPError as error:
        if error.code in (401, 403):
            message = "資料庫授權失敗，請檢查 Secrets 的金鑰及資料表權限。"
        elif error.code == 404:
            message = "找不到點餐資料表或函式。新功能需先在 Supabase 執行 setup_lunch_groups.sql。"
        else:
            message = f"資料庫暫時無法完成操作（HTTP {error.code}），請稍後重新整理確認。"
        raise StorageError(message) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise StorageError("無法確認資料庫操作結果。請稍後重新整理檢查，確認後再送出，避免重複。") from None


def load_orders():
    rows = []
    offset = 0
    page_size = 500
    while True:
        page = database_request(
            "GET", "lunch_orders?select=id,restaurant,name,dish,amount,notes"
            f"&order=created_at.asc,id.asc&limit={page_size}&offset={offset}"
        )
        if not isinstance(page, list):
            raise StorageError("訂單資料格式異常，已停止讀寫；請檢查資料庫。")
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    records = [{
        "_order_id": row["id"], "店家": row["restaurant"], "姓名": row["name"],
        "餐點": row["dish"], "金額": float(row["amount"]), "備註": row["notes"]
    } for row in rows]
    return pd.DataFrame(records, columns=["_order_id", "店家", "姓名", "餐點", "金額", "備註"])


def import_legacy_orders(csv_bytes):
    try:
        frame = pd.read_csv(io.BytesIO(csv_bytes), keep_default_na=False)
    except Exception:
        raise ValueError("無法讀取 CSV，請使用原點餐網站下載的報表。") from None
    required = ["店家", "姓名", "餐點", "金額", "備註"]
    if not all(column in frame.columns for column in required):
        raise ValueError("CSV 需包含店家、姓名、餐點、金額、備註五欄。")
    if frame.empty:
        raise ValueError("這份 CSV 沒有訂單。")
    amounts = pd.to_numeric(frame["金額"], errors="coerce")
    if amounts.isna().any() or not amounts.between(0, 99999999.99).all():
        raise ValueError("CSV 的金額欄有無效數字，請先檢查檔案。")
    fingerprint = hashlib.sha256(csv_bytes).hexdigest()
    records = [{
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"lunch-import:{fingerprint}:{index}")),
        "restaurant": str(row["店家"]), "name": str(row["姓名"]),
        "dish": str(row["餐點"]), "amount": float(amounts.iloc[index]), "notes": str(row["備註"])
    } for index, (_, row) in enumerate(frame.iterrows())]
    for offset in range(0, len(records), 500):
        database_request("POST", "lunch_orders?on_conflict=id", records[offset:offset + 500],
                         prefer="resolution=ignore-duplicates,return=minimal")
    return len(records)


def delete_order(order_id):
    safe_id = str(uuid.UUID(str(order_id)))
    database_request("DELETE", "lunch_orders?id=eq." + safe_id, prefer="return=minimal")


# 常用同事名單
MEMBERS = [
    "葉臨恩",
    "陳俊丞",
    "楊承凱", "倪宗安", "王國祐", "呂盈毅", "謝嘉雲", "顏寶容", "章哲勳", "陳威成",
    "謝文玲", "李雨柔", "皮爵赫", "陳柏伸", "黃志成", "陳柏邑", "盧廷謙", "王宗瑜",
    "張瀚允", "陳柏豪", "曾柏豪", "周秀苓", "許皓翔", "胡煥然",
    "陳永河", "秦昇瑜", "張駿謙", "王慧珍", "黃浚宏", "怡君", "fish",
    "劉紹翔", "洪成祥", "柯柏村",
    "陳躍中", "楊乃穎",
    # --- BIM 團隊同仁 ---
    "林詩珊", "謝淳淇", "歐柏鋒", "林慧語", "吳詩田",
    # --- 彈性輸入 ---
    "其他 / 手動輸入"
]

# 多店家完整菜單資料庫
RESTAURANT_MENUS = {
    '好日餐盒': {'家傳滷香菇雞腿': 140,
     '雞翅便當(兩翅)': 120,
     '香煎里肌豬排': 140,
     '軟骨肉飯': 140,
     '雞腿特餐（兩樣菜）': 100,
     '健康菜飯': 90,
     '香菇滷雞腿（單包冷凍／1支）': 65,
     '香菇滷雞腿（單包冷凍／5支）': 300},
    '貳貳來吃＆莊爸爸健康餐': {'酥炸雞腿': 120,
     '香酥雞排': 115,
     '甘梅雞排': 115,
     '照燒雞排': 120,
     '薑汁燒肉': 110,
     '香檸豬排': 100,
     '糖醋小排': 105,
     '魚肉綜合': 105,
     '宮保雞丁': 105,
     '椒鹽雞丁': 100,
     '炸豬排': 100,
     '黑胡椒豬': 95,
     '原味雞胸': 145,
     '川味雞胸': 150,
     '義式香料嫩雞胸': 145,
     '泰式檸檬雞胸': 150,
     '高蛋白塔塔雞胸': 150,
     '香煎豬菲力': 195,
     '水煮虱目魚柳': 140,
     '香煎雞腿排': 195,
     '鹽味鯖魚': 145,
     '彈跳大蝦仁': 195,
     '加購醬料：泰式醬': 15,
     '加購醬料：胡麻醬': 15,
     '加購醬料：塔塔醬': 10,
     '加購醬料：青檸醬': 10,
     '加購醬料：和風芥末醬': 10},
    "吃蔬肥吧": {
        "玫瑰鹽舒肥雞胸": 130, "柚香椒鹽舒肥雞胸": 130, "蒜香胡椒舒肥雞胸": 130, "南洋咖哩舒肥雞胸": 130,
        "台式蔥油舒肥雞胸(限量/不含三星蔥)": 135, "香菜辣味舒肥雞胸(限量/含香菜)": 140,
        "韓式泡菜豬(辣度不可調整)": 140, "檸檬椒鹽豬": 130, "蒜泥豬肉": 135, "加購：豬肉加肉量": 50,
        "鹽漬烤鮭魚": 170, "照燒烤鮭魚": 170,
        "玫瑰鹽雞胸肉(單點)": 60, "柚香椒鹽雞胸肉(單點)": 60, "蒜香胡椒雞胸肉(單點)": 60, "南洋咖哩雞胸肉(單點)": 60,
        "水煮蛋": 15, "藜麥胚芽飯": 15, "照燒/鹽漬烤鮭魚(單點)": 105,
        "今天不吃肉(五辛素)": 70,
        "醬料：和風柚子醬": 0, "醬料：泰式甜辣醬": 0, "醬料：蜂蜜芥末醬": 0, "醬料：日式胡麻醬": 5, "加購單點蔬菜醬料": 5
    },
    "春宅": {
        "朝日大麥(M)": 25, "朝日大麥(L)": 30, "焙火大麥(M)": 25, "焙火大麥(L)": 30,
        "晨露綠茶(M)": 25, "晨露綠茶(L)": 30, "妍果紅茶(M)": 30, "妍果紅茶(L)": 35,
        "四季春茶(M)": 30, "四季春茶(L)": 35, "金萱烏龍(M)": 30, "金萱烏龍(L)": 35, "赤韻烏龍(M)": 30, "赤韻烏龍(L)": 35,
        "冬瓜檸檬(L)": 50, "茶凍檸檬青(M)": 55, "茶凍檸檬青(L)": 60, "堤亞青檸(L)": 60,
        "黃金柳橙綠(M)": 55, "黃金柳橙綠(L)": 65, "桂花紅柚烏龍(L)": 65, "蘋果四季春(L)": 65,
        "葡萄輕茉綠(M)": 65, "葡萄輕茉綠(L)": 70,
        "朝日大麥那堤(M)": 55, "朝日大麥那堤(L)": 65, "紅茶那堤(M)": 55, "紅茶那堤(L)": 65,
        "烏龍那堤(M)": 55, "烏龍那堤(L)": 65, "白玉茶凍烏龍那堤(M)": 65, "白玉茶凍烏龍那堤(L)": 70,
        "春宅奶茶(M)": 45, "春宅奶茶(L)": 50, "白玉珍珠奶茶(M)": 50, "白玉珍珠奶茶(L)": 55,
        "朝日大麥凍奶(M)": 55, "朝日大麥凍奶(L)": 60, "大麥凍金萱奶(M)": 55, "大麥凍金萱奶(L)": 60,
        "芝士朝日大麥(冰量固定L)": 60, "芝士金萱烏龍(冰量固定L)": 60, "芝士妍果紅茶(冰量固定L)": 60, "芝士可可奶霜(冰量固定L)": 65,
        "玉露冬瓜茶(L)": 35, "水里梅子綠(L)": 55, "茶凍桂花蜜烏龍(L)": 60, "茶凍荔枝春茶(L)": 60,
        "加料: 朝日大麥凍": 10, "加料: 烏龍粉粿": 10, "加料: 白玉珍珠": 10, "加料: 翡翠茶凍": 10
    },
    "百禾": {
        "五樣蔬菜飯盒": 85,
        "柳葉魚仔飯盒": 95,
        "現滷排骨飯盒": 100,
        "咔啦腿排飯盒": 100,
        "香酥排骨飯盒": 110,
        "三杯雞米飯盒": 110,
        "糖醋雞丁飯盒": 110,
        "紅麴叉燒飯盒": 110,
        "海陸雙拼飯盒": 120,
        "椒鹽雞排飯盒": 120,
        "特製雞腿飯盒": 130,
        "商業會議餐盒（需提前預約）": 280,
        "加菜：加一道菜": 15,
    },
    "春福家": {
        "爌肉便當": 90, "爌肉(單點)": 50,
        "薑汁燒肉便當": 95, "薑汁燒肉(單點)": 60,
        "家傳排骨便當": 100, "家傳排骨(單點)": 60,
        "日式豬排便當": 100, "日式豬排(單點)": 70,
        "炸紅糟肉便當": 110, "炸紅糟肉(單點)": 70,
        "滷雞腿便當": 95, "滷雞腿(單點)": 65,
        "三杯雞腿肉便當": 100, "三杯雞腿肉(單點)": 70,
        "蜜汁雞腿排便當": 120, "蜜汁雞腿排(單點)": 80,
        "椒鹽雞腿排便當": 120, "椒鹽雞腿排(單點)": 80,
        "酥炸雞腿便當": 125, "酥炸雞腿(單點)": 85,
        "椒麻雞腿排便當": 135, "椒麻雞腿排(單點)": 95,
        "椒鹽魚排便當": 85, "椒鹽魚排(單點)": 50,
        "香煎鮭魚排便當": 110, "香煎鮭魚排(單點)": 70,
        "蔬食便當(6菜方便素)": 80
    },
    "巷仔內豬腳飯": {
        "滷豬腳飯": 120, "日式肉末咖哩飯": 85, "日式唐揚雞咖哩飯": 110, "日式厚切豬排咖哩飯": 135,
        "秘滷牛肉飯": 110, "滷香香雞腿飯": 110, "肉燥飯(小)": 35, "肉燥飯(大)": 50, "肉燥便當": 70,
        "滷豬腳(單點)": 90, "滷牛肉(單點)": 80, "滷筍干": 35, "滷油豆腐": 10,
        "滷蛋": 15, "白飯": 10, "炒青菜": 30,
        "餛飩湯": 40, "虱目魚丸湯": 40, "貢丸湯": 40,
        "麥香紅茶(小)": 10, "麥香紅茶(大)": 20, "冬瓜檸檬(小)": 15, "冬瓜檸檬(大)": 30,
        "古早味冬瓜茶": 20, "鮮奶茶": 20, "蜂蜜檸檬茶": 20
    },
    "超級大盛": {
        "超吉燒肉丼飯": 100, "泡菜燒肉丼飯": 105, "打拋豬肉丼飯": 110, "照燒雞腿丼飯": 115,
        "黃金豬排丼飯": 115, "和風牛肉丼飯": 120, "厚燒排骨丼飯": 125, "蜜汁雞排丼飯": 135,
        "A餐優惠: 現烤香腸 + 精選湯品 (三選一備註)": 35,
        "B餐優惠: 現烤香腸 + 手作好茶 (三選一備註)": 50,
        "日式味噌湯": 30, "鮮採竹筍湯": 30, "大根貢丸湯": 30, "現烤香腸": 15,
        "韓國泡菜": 35, "現煎荷包蛋": 15, "花露冷萃茶": 45, "桂圓冬瓜茶": 45, "山採女兒紅": 45,
    },
    "上宇林": {
        "上宇林青茶": 35, "上宇林紅茶": 35, "三窨花綠茶": 35, "蟲蝕烏龍茶": 35, "東方美人": 35,
        "紅龍茗茶": 35, "綠龍茗茶": 35, "青龍茗茶": 35, "雪浮奶紅茶": 60, "雪浮奶綠茶": 60,
        "雪浮奶青茶": 60, "雪浮奶烏龍茶": 60, "雪浮奶美人": 60, "黃金多多綠": 55, "梅香綠茶": 50,
        "脆梅綠茶(甜度固定)": 55, "冬瓜茶(甜度固定)": 35, "冬瓜綠/青/紅(甜度固定)": 45,
        "冬瓜檸檬(甜度固定)": 60, "檸檬紅/綠/青": 60, "香橙青/綠茶": 60, "葡萄柚青/綠茶": 60,
        "蔓越莓綠/青/紅(甜度固定)": 55, "冰淇淋紅/綠/青/烏/冬瓜": 55, "黑糖Q粿 紅/綠/青/烏/冬瓜": 55,
        "手工粉角紅/綠/青/烏/冬瓜": 45, "仙草凍紅/綠/青/烏/冬瓜": 45, "太極紅/綠/青/烏/冬瓜": 45,
        "椰果紅/綠/青/烏/冬瓜": 45, "珍珠紅/綠/青/烏/冬瓜": 45, "布丁紅/綠茶/青/烏/冬瓜": 50,
        "茉莉綠茶凍綠茶": 45, "甘蔗青/綠/烏/紅茶(甜度固定)": 60, "甘蔗柳橙/檸檬/蔓越莓(甜度固定)": 70,
        "泰式奶茶(甜度固定)": 65, "草莓冰茶(甜冰固定)": 70, "鼎極鮮奶茶": 60, "太極鮮奶茶(粉角+珍珠)": 70,
        "紅龍鮮奶茶": 60, "鐵觀音鮮奶茶": 60, "鮮奶綠茶": 60, "鮮奶青茶": 60, "烏龍鮮奶茶": 60,
        "美人鮮奶茶": 60, "冬瓜鮮奶(甜度固定)": 60, "冬瓜鮮奶茶(甜度固定)": 70, "冰淇淋鮮奶茶": 80,
        "手工粉角鮮奶茶": 70, "仙草凍鮮奶茶": 70, "椰果鮮奶茶": 70, "布丁鮮奶茶": 75, "珍珠鮮奶茶": 70,
        "茉莉綠茶凍鮮奶茶": 70, "黑糖Q粿鮮奶茶": 80, "甘蔗拿鐵(甜度固定)": 80, "草莓牛奶(甜冰固定)": 80,
        "草莓茉莉冰奶(甜冰固定)": 80, "桂圓紅棗茶(甜度固定)": 55, "桂圓紅棗鮮奶茶(甜度固定)": 75,
        "薑軍茶(甜度固定)": 55, "薑軍鮮奶茶(甜度固定)": 75, "加料: 珍珠/手工粉角/QQ/太極": 10,
        "加料: 椰果/仙草凍/茉莉綠茶凍": 10, "加料: 話梅/布丁": 15, "加料: 多多/香草冰淇淋/黑糖Q粿": 20,
    },
    "窖藏飲料": {
        "特級茉香綠(M)": 25, "特級茉香綠(L)": 30, "台灣青(M)": 25, "台灣青(L)": 30,
        "窖藏紅茶(M)": 25, "窖藏紅茶(L)": 30, "厚底烏龍(M)": 25, "厚底烏龍(L)": 30,
        "厚底青(M)": 25, "厚底青(L)": 30, "黑糖冬瓜(M)": 25, "黑糖冬瓜(L)": 30,
        "決明子大麥(M)": 25, "決明子大麥(L)": 30, "東方美人茶": 50, "高山手作茶": 40,
        "阿里山金萱": 45, "翠巒私房茶": 50, "台東紅烏龍": 50, "杉林雲霧茶": 60,
        "頂級福壽山高山茶": 70, "柚香金萱(M)": 50, "柚香金萱(L)": 55, "極品私藏奶": 65,
        "紅烏龍奶茶": 65, "杉檸翠玉(固定)": 65, "多多綠/多多青/多多烏(M)": 45,
        "多多綠/多多青/多多烏(L)": 50, "香橙多多(M)": 60, "香橙多多(L)": 70,
        "紅鑽葡萄柚多多(M)": 55, "紅鑽葡萄柚多多(L)": 65, "鮮檸檬多多/百香多多(M)": 55,
        "鮮檸檬多多/百香多多(L)": 65, "鳳梨多多(M)": 55, "鳳梨多多(L)": 65,
        "愛玉鮮檸檬(M)": 50, "愛玉鮮檸檬(L)": 60, "冰淇淋紅茶(M)": 45, "冰淇淋紅茶(L)": 50,
        "冰淇淋芒果綠/芒果青(M)": 45, "冰淇淋芒果綠/芒果青(L)": 50, "桂花釀 Linux(M)": 35,
        "桂花釀紅/綠/青/烏(M)": 35, "桂花釀紅/綠/青/烏(L)": 40, "脆梅玉露/青茶(M)": 45,
        "脆梅玉露/青茶(L)": 50, "脆梅檸檬(M)": 45, "脆梅檸檬(L)": 50, "新鮮香橙綠(M)": 55,
        "新鮮香橙綠(L)": 60, "紅鑽葡萄柚綠(M)": 50, "紅鑽葡萄柚綠(L)": 55, "鳳梨水果冰茶(M)": 50,
        "鳳梨水果冰茶(L)": 55, "鳳梨青茶(M)": 50, "鳳梨青茶(L)": 55, "鮮甘蔗綠/青(M)": 55,
        "鮮甘蔗綠/青(L)": 60, "甘蔗鮮檸檬(M)": 60, "甘蔗鮮檸檬(L)": 65, "蜂蜜鮮檸檬(M)": 50,
        "蜂蜜鮮檸檬(L)": 55, "翡翠檸檬/紅/青(M)": 45, "翡翠檸檬/紅/青(L)": 50, "鮮百香果綠/青(M)": 40,
        "鮮百香果綠/青(L)": 45, "百香蜜冬瓜(M)": 40, "百香蜜冬瓜(L)": 45, "金桔檸檬汁(M)": 40,
        "金桔檸檬汁(L)": 45, "冬瓜鮮檸檬(M)": 40, "冬瓜鮮檸檬(L)": 45, "芭樂綠(M)": 55,
        "芭樂綠(L)": 60, "芭樂柳丁綠(M)": 60, "芭樂柳丁綠(L)": 65, "芭樂檸檬綠(M)": 60,
        "芭樂檸檬綠(L)": 65, "芭樂多多(M)": 60, "芭樂多多(L)": 65, "黑糖波霸鮮奶(固定)(M)": 60,
        "黑糖波霸鮮奶(固定)(L)": 75, "紅茶/綠茶/青茶那提(M)": 50, "紅茶/綠茶/青茶那提(L)": 55,
        "厚底烏龍那提(M)": 50, "厚底烏龍那提(L)": 55, "冬瓜那提(M)": 50, "冬瓜那提(L)": 55,
        "咖啡那提(M)": 50, "咖啡那提(L)": 75, "甘蔗鮮奶茶(M)": 60, "甘蔗鮮奶茶(L)": 70,
        "黑糖波霸/珍珠鮮奶茶(M)": 65, "黑糖波霸/珍珠鮮奶茶(L)": 70, "可可歐蕾(M)": 55,
        "可可歐蕾(L)": 80, "鮮奶仙草凍": 50, "桂花釀那提(M)": 60, "桂花釀那提(L)": 65,
        "極致奶茶/奶綠/奶青/奶烏(M)": 45, "極致奶茶/奶綠/奶青/奶烏(L)": 50, "陽光麥香奶茶(M)": 45,
        "陽光麥香奶茶(L)": 50, "極品咖啡(M)": 45, "極品咖啡(L)": 55, "黑糖波霸/珍珠奶茶(M)": 60,
        "黑糖波霸/珍珠奶茶(L)": 65, "仙草凍奶茶(M)": 60, "仙草凍奶茶(L)": 65, "桂花釀奶茶(M)": 55,
        "桂花釀奶茶(L)": 60, "有機黑豆茶(M)": 30, "有機黑豆茶(L)": 35, "有機黑豆冬瓜(M)": 35,
        "有機黑豆冬瓜(L)": 40, "有機黑豆奶茶(M)": 50, "有機黑豆奶茶(L)": 55, "有機黑豆那提(M)": 55,
        "有機黑豆那提(L)": 60, "黃金蕎麥茶(M)": 30, "黃金蕎麥茶(L)": 35, "黃金蕎麥冬瓜(M)": 35,
        "黃金蕎麥冬瓜(L)": 40, "黃金蕎麥奶茶(M)": 50, "黃金蕎麥奶茶(L)": 55, "黃金蕎麥那提(M)": 55,
        "黃金蕎麥那提(L)": 60, "日式抹茶初雪": 50, "黑糖抹茶初雪": 55, "關山黑糖那提": 55,
        "黑糖竹薑茶": 45, "黑糖竹薑那提": 50, "蜜香竹薑茶": 40, "加料: 梅子": 5,
        "加料: 桂花釀": 10, "加料: 黑糖波霸/珍珠/QQ": 15, "加料: 愛玉凍/仙草凍/布丁/多多": 15,
        "加料: 冰淇淋/黑糖Q凍/桂花凍/青梅凍": 20, "加料: 牛奶/蜂蜜": 25,
    },
    "龍饌食堂": {
        "土雞肉飯便當": 110, "土雞腿肉飯便當": 150, "客家焢肉飯便當": 110, "冰糖豬腳飯便當": 140,
        "古早味炸排骨飯便當": 110, "酥炸紅糟肉飯便當": 120, "炸大雞腿飯便當": 125,
        "黑胡椒無骨雞腿飯便當": 140, "塔香無骨雞腿飯便當": 140, "辣子無骨雞腿飯便當": 140,
        "照燒無骨雞腿飯便當": 140, "佃煮秋刀魚飯便當": 110, "蒜泥白肉飯便當": 110,
        "雙主菜便當(任選2種備註)": 185, "雞滷飯(外帶)": 70, "滷肉飯(外帶)": 50,
        "肥腸滷肉飯(外帶)": 85, "蝦仁滷肉飯(外帶)": 100, "土雞碎肉飯(外帶)": 65,
        "土雞碎肉飯(外帶加肉)": 85, "白飯(外帶)": 20, "香腸蛋炒飯": 100, "排骨蛋炒飯": 110,
        "蝦仁蛋炒飯": 130, "香腸蝦仁蛋炒飯": 160, "手工水餃(高麗菜10顆)": 70,
        "手工水餃(韭菜10顆)": 70, "古早味排骨(單點)": 80, "紅糟肉(單點)": 90,
        "炸大雞腿(單點)": 90, "炸餛飩(單點)": 50, "炸雞翅": 35, "炸豆腐": 40,
        "鹹水雞翅": 35, "土雞肉切盤(大)": 170, "土雞肉切盤(小)": 120, "焢肉(單點)": 80,
        "豬腳(單點)": 110, "荷包蛋": 15, "滷蛋": 15, "蔥蛋": 40, "炒青菜": 60,
        "紅油炒手": 50, "蝦仁煎蛋": 100, "滷肥腸(單點)": 100, "白切豬腸": 60,
        "豆干(3個)": 20, "油豆腐(2個)": 20, "豬耳絲": 50, "佃煮秋刀魚(單點)": 80,
        "蒜泥白肉(單點)": 80, "蘿蔔湯": 25, "紫菜蛋花湯": 25, "竹筍排骨湯": 45,
        "鮮肉丸湯": 50, "魚丸湯": 40, "下水湯": 40, "餛飩湯": 45, "綜合丸湯": 60,
        "豬腸湯": 60, "蛤蜊湯": 60, "酸辣湯": 40, "酸辣湯餃": 80, "冬粉湯": 45,
        "下水冬粉": 60, "餛飩冬粉": 65, "鮮肉丸子冬粉": 70, "豬腸冬粉": 80,
        "蛤蜊冬粉": 80, "古早味紅茶": 25, "甘泉冬瓜露": 25,
    },
    "甲一飯包": {
        "香腸飯": 95, "原味咔啦雞飯": 95, "辣味咔啦雞飯": 95, "招牌飯": 100,
        "滷棒腿飯": 100, "薄鹽鯖魚飯": 100, "叉燒飯": 105, "養生飯": 105,
        "蒲燒魚飯": 105, "鐵路排骨飯": 105, "炸排骨飯": 105, "爌肉飯": 110,
        "法式豬排飯": 110, "菲力豬排飯": 115, "塔香無骨雞排飯": 115, "香雞排飯": 120,
        "黑胡椒牛柳飯": 120, "和風烤雞飯": 125, "炸雞腿飯": 130, "挪威鯖魚飯": 140,
    },
    "貓丼": {
        "雙蛋丼飯": 110, "豬肉蛋丼飯": 140, "牛肉蛋丼飯": 150, "炸豬排蛋丼飯": 170,
        "唐揚雞蛋丼飯": 170, "炸魚排蛋丼飯": 190, "親子丼飯": 200, "咖哩飯": 100,
        "咖哩烏龍麵 (+30)": 130, "豬肉咖哩飯": 150, "豬肉咖哩烏龍麵 (+30)": 180,
        "牛肉咖哩飯": 160, "牛肉咖哩烏龍麵 (+30)": 190, "炸豬排咖哩飯": 180,
        "炸豬排咖哩烏龍麵 (+30)": 210, "唐揚雞咖哩飯": 180, "唐揚雞咖哩烏龍麵 (+30)": 210,
        "炸魚排咖哩飯": 200, "炸魚排咖哩烏龍麵 (+30)": 230, "白飯": 20,
        "古早味紅茶": 25, "溏心蛋": 30, "波浪薯條": 35, "咖哩可樂餅": 40,
        "QQ球": 55, "炸豆腐": 60, "炸豬排(單點)": 100, "唐揚雞(單點)": 100,
        "日式炸魚排(3隻)": 120, "咖哩醬": 60,
        # 新增菜單：壽司系列
        "稻禾豆皮壽司(6顆)": 60,
        "日式唐揚雞太卷(4顆)": 65,
        "日式炸豬排太卷(4顆)": 65,
        "炸豬排+豆皮(8顆)": 110,
        "唐揚雞+豆皮(8顆)": 110,
        "豬雞雙拼(8顆)": 120,
        # 新增菜單：飯糰系列
        "經典握飯糰": 55,
        "豬排握飯糰": 75,
        "唐揚雞握飯糰": 75,
        "炸魚排握飯糰": 75,
        "咖哩可樂餅握飯糰": 75,
        "原味可樂餅握飯糰": 80,
        # 新增菜單：日式炒飯系列
        "雙蛋炒飯": 60,
        "豬肉炒飯": 80,
        "牛肉炒飯": 90,
        "唐揚雞炒飯": 125,
        "炸豬排炒飯": 125,
        "炸魚排炒飯": 145,
    },
    "崛日初食": {
        "和風番茄豚肉丼 (3樣菜)": 100, "和風番茄豚肉丼 (加肉)": 110,
        "和風番茄豚肉丼 (加菜加肉 5樣菜以上)": 150, "黑醋豬肉炒意麵 (3樣菜)": 100,
        "黑醋豬肉炒意麵 (加肉)": 110, "黑醋豬肉炒意麵 (加菜加肉 5樣菜以上)": 150,
        "日式炒烏龍 (3樣菜)": 100, "日式炒烏龍 (加肉)": 120, "日式炒烏龍 (加菜加肉 5樣菜以上)": 150,
        "檸檬雞柳甜咖哩 (3樣菜)": 100, "檸檬雞柳甜咖哩 (加肉)": 130,
        "檸檬雞柳甜咖哩 (加菜加肉 5樣菜以上)": 150, "去骨雞腿親子丼 (3樣菜)": 100,
        "去骨雞腿親子丼 (加肉)": 130, "去骨雞腿親子丼 (加菜加肉 5樣菜以上)": 150,
        "和風唐揚雞[微辣] (3樣菜)": 100, "和風唐揚雞[微辣] (加肉)": 130,
        "和風唐揚雞[微辣] (加菜加肉 5樣菜以上)": 150, "日式味噌去骨雞腿 (3樣菜)": 120,
        "日式味噌去骨雞腿 (加肉)": 130, "日式味噌去骨雞腿 (加菜加肉 5樣菜以上)": 150,
        "崛日健康餐 (3樣菜)": 150, "崛日健康餐 (加肉)": 180, "崛日健康餐 (加菜加肉 5樣菜以上)": 200,
        "牛肉他人丼 (3樣菜)": 150, "牛肉他人丼 (加肉)": 180, "牛肉他人丼 (加菜加肉 5樣菜以上)": 200,
    },
    "你好，顏值": {
        "蒸煮麵": 25, "王子麵": 15, "鍋燒意麵": 25, "冬粉(寬)": 20, "冬粉(細)": 20,
        "讚岐烏龍麵": 30, "紅茶": 35, "菊花肉": 30, "豬肉片": 30, "豬耳朵": 30,
        "豬頭皮": 30, "大腸頭": 45, "木耳": 25, "水蓮": 30, "洋蔥": 30,
        "青椒": 30, "金針菇": 30, "秀珍菇": 30, "大陸妹": 30, "豆芽菜": 30,
        "青江菜": 30, "高麗菜": 30, "花椰菜": 30, "娃娃菜": 30, "四季豆": 30,
        "玉米筍": 30, "滷蛋": 15, "皮蛋": 20, "滷花生": 15, "豆乾": 20,
        "豆包": 20, "米血": 20, "芋條": 20, "竹輪": 20, "燕餃": 20,
        "蟹肉棒": 20, "鑫鑫腸": 20, "甜不辣": 20, "小黑輪": 20, "大貢丸": 20,
        "水晶餃": 20, "凍豆腐": 20, "龍蝦沙拉": 20, "日本海帶": 20, "黃金魚丸": 20,
        "百頁豆腐": 20,
    },
    "食材有限": {
        "雞絲涼粉（小）": 60,
        "雞絲涼粉（大）": 100,
        "海鮮涼粉（小）": 70,
        "海鮮涼粉（大）": 110,
        "霸氣雞腿涼粉": 120,
        "手撕雞肉飯": 60,
        "肉燥飯": 50,
        "口水雞": 180,
        "¼ 油雞": 150,
        "½ 油雞": 250,
        "海南雞腿便當（午間限定）": 110,
        "油雞腿便當（午間限定）": 110,
        "雞絲便當（午間限定）": 80,
        "肉燥便當（午間限定）": 70,
        "鍋燒意麵（滷味）": 15,
        "蒸煮麵（滷味）": 15,
        "科學麵（滷味）": 15,
        "鑫鑫腸（4條）": 20,
        "鳥蛋（4顆）": 20,
        "甜不辣": 20,
        "米血": 20,
        "海帶": 20,
        "豆乾": 20,
        "雞爪（4隻）": 25,
        "豬耳朵": 30,
        "豬頭皮": 30,
        "豬大腸": 40,
        "豬肉片": 40,
        "花生": 25,
        "木耳": 30,
        "娃娃菜": 30,
        "杏鮑菇": 30,
        "高麗菜": 30,
        "滷味蔬菜兩樣（請備註品項）": 50,
    },
    "痴飯吧": {
        "燒肉飯": 100,
        "豬腳飯": 110,
        "嫩骨飯": 120,
        "玫瑰油雞腿飯": 120,
        "牛腱飯": 160,
        "牛三寶飯": 160,
        "醬滷魚肚飯（無刺虱目魚肚）": 150,
        "素食飯（全素）": 100,
        "素食飯（蛋奶素）": 100,
    },
    "御井燒味": {
        "蜜汁叉燒餐盒": 150,
        "招牌紅槽肉餐盒": 150,
        "翡翠紅油雞餐盒": 150,
        "秘製照燒雞餐盒": 150,
        "豉油雞餐盒": 150,
        "照燒卡拉雞餐盒": 150,
        "鰻魚便當": 250,
        "清蒸鱸魚餐盒": 150,
        "蜜汁叉燒蛋炒飯": 130,
    }
}

# 動態產生零延遲、對稱相撞大爆炸 CSS（50.0% 絕對咬合）
def generate_dynamic_clash_css(table_id, top_idx, btm_idx, row_height=48):
    if top_idx is None or btm_idx is None or top_idx == btm_idx:
        return ""
    diff = abs(btm_idx - top_idx)
    distance_px = int((diff * row_height) / 2)
    
    return f"""
    <style>
    /* 上方選手：0-15% 蓄力 -> 15-50% 全速加速衝刺(ease-in) -> 50% 碰觸最高速 -> 50-65% 震退彈回(ease-out) -> 75-100% 絕對靜止 */
    @keyframes smashDown_{table_id} {{
        0% {{
            transform: translateY(0px) scale(1);
            filter: brightness(1);
            animation-timing-function: ease-out;
        }}
        15% {{
            transform: translateY(-10px) scale(0.95);
            filter: brightness(1.2);
            animation-timing-function: ease-in;
        }}
        50% {{ 
            transform: translateY({distance_px}px) scale(1.35) rotate(-3deg); 
            filter: brightness(2.8) drop-shadow(0 0 25px #ffffff) drop-shadow(0 0 45px #ff3300);
            animation-timing-function: ease-out;
        }}
        65% {{ 
            transform: translateY({int(distance_px * 0.35)}px) scale(1.1) rotate(4deg); 
            filter: brightness(1.3);
            animation-timing-function: ease-in-out;
        }}
        75% {{
            transform: translateY(0px) scale(1);
            filter: brightness(1);
        }}
        100% {{ 
            transform: translateY(0px) scale(1); 
            filter: brightness(1); 
        }}
    }}

    /* 下方選手：0-15% 蓄力 -> 15-50% 全速加速衝刺(ease-in) -> 50% 碰觸最高速 -> 50-65% 震退彈回(ease-out) -> 75-100% 絕對靜止 */
    @keyframes smashUp_{table_id} {{
        0% {{
            transform: translateY(0px) scale(1);
            filter: brightness(1);
            animation-timing-function: ease-out;
        }}
        15% {{
            transform: translateY(10px) scale(0.95);
            filter: brightness(1.2);
            animation-timing-function: ease-in;
        }}
        50% {{ 
            transform: translateY(-{distance_px}px) scale(1.35) rotate(3deg); 
            filter: brightness(2.8) drop-shadow(0 0 25px #ffffff) drop-shadow(0 0 45px #00e5ff);
            animation-timing-function: ease-out;
        }}
        65% {{ 
            transform: translateY(-{int(distance_px * 0.35)}px) scale(1.1) rotate(-4deg); 
            filter: brightness(1.3);
            animation-timing-function: ease-in-out;
        }}
        75% {{
            transform: translateY(0px) scale(1);
            filter: brightness(1);
        }}
        100% {{ 
            transform: translateY(0px) scale(1); 
            filter: brightness(1); 
        }}
    }}

    /* 中心大爆炸：49% 隱形 -> 50% 撞擊瞬間零時差爆發 -> 56% 快速消散 -> 57-100% 絕對隱形 */
    @keyframes explosionSupernova_{table_id} {{
        0%, 49% {{ 
            opacity: 0; 
            transform: translate(-50%, -50%) scale(0.1) rotate(0deg); 
        }}
        50% {{ 
            opacity: 1; 
            transform: translate(-50%, -50%) scale(3.8) rotate(45deg); 
            box-shadow: 0 0 35px #ffffff, 0 0 70px #ffea00, 0 0 100px #ff3300, 0 0 120px #00e5ff;
        }}
        54% {{ 
            opacity: 0.85; 
            transform: translate(-50%, -50%) scale(5.6) rotate(90deg); 
            box-shadow: 0 0 50px rgba(255,255,255,1), 0 0 90px rgba(255,69,0,0.8), 0 0 115px rgba(0,229,255,0.8);
        }}
        56% {{ 
            opacity: 0; 
            transform: translate(-50%, -50%) scale(7.0) rotate(140deg); 
        }}
        100% {{ 
            opacity: 0; 
            transform: translate(-50%, -50%) scale(0.1); 
        }}
    }}

    .smash-top-{table_id} {{
        display: inline-block;
        position: relative;
        font-weight: 900;
        letter-spacing: 2px;
        animation: smashDown_{table_id} 1.8s infinite;
        z-index: 25;
    }}

    .smash-bottom-{table_id} {{
        display: inline-block;
        position: relative;
        font-weight: 900;
        letter-spacing: 2px;
        animation: smashUp_{table_id} 1.8s infinite;
        z-index: 25;
    }}

    .explosion-core-{table_id} {{
        position: absolute;
        top: 50%;
        left: 50%;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        background: radial-gradient(circle, #ffffff 15%, #ffff77 35%, #ff4500 65%, #00e5ff 90%, transparent 100%);
        pointer-events: none;
        animation: explosionSupernova_{table_id} 1.8s infinite;
        z-index: 999;
    }}
    </style>
    """

# 注入常態、粒子與邊牧特效
st.markdown("""
<style>
/* ================== 1. 陳俊丞：流動烈焰 + 升騰火星 ================== */
@keyframes flameFlow {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
@keyframes sparkRise1 {
    0%   { opacity: 0; transform: translate(0, 0) scale(0.4); }
    30%  { opacity: 1; transform: translate(-8px, -10px) scale(1); }
    70%  { opacity: 0.8; transform: translate(-14px, -24px) scale(0.8); }
    100% { opacity: 0; transform: translate(-18px, -36px) scale(0.2); }
}
@keyframes sparkRise2 {
    0%   { opacity: 0; transform: translate(0, 0) scale(0.4); }
    30%  { opacity: 1; transform: translate(10px, -12px) scale(1.1); }
    70%  { opacity: 0.8; transform: translate(16px, -26px) scale(0.7); }
    100% { opacity: 0; transform: translate(22px, -38px) scale(0.2); }
}

.flame-name-wrapper {
    display: inline-flex;
    align-items: center;
    position: relative;
    font-weight: 900;
    letter-spacing: 2px;
    background: linear-gradient(90deg, #ff0844, #ffb199, #ff7e40, #ff0844);
    background-size: 250% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: flameFlow 2.0s infinite linear;
}
.flame-spark-1 {
    position: absolute;
    top: 50%;
    left: 20%;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: radial-gradient(circle, #ffffff 10%, #ffea00 40%, #ff3300 100%);
    box-shadow: 0 0 8px #ff5500;
    pointer-events: none;
    animation: sparkRise1 1.6s infinite ease-out;
}
.flame-spark-2 {
    position: absolute;
    top: 50%;
    right: 20%;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: radial-gradient(circle, #ffffff 10%, #ffff33 40%, #ff2200 100%);
    box-shadow: 0 0 9px #ff3300;
    pointer-events: none;
    animation: sparkRise2 1.8s infinite ease-out 0.4s;
}

/* ================== 2. 葉臨恩：極光冰晶 + 旋轉碎雪 ================== */
@keyframes iceAuroraFlow {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
@keyframes snowDrift1 {
    0%   { opacity: 0; transform: translate(0, 0) rotate(0deg) scale(0.4); }
    30%  { opacity: 1; transform: translate(-10px, 8px) rotate(90deg) scale(1); }
    70%  { opacity: 0.9; transform: translate(-16px, 18px) rotate(180deg) scale(0.9); }
    100% { opacity: 0; transform: translate(-22px, 28px) rotate(270deg) scale(0.3); }
}
@keyframes snowDrift2 {
    0%   { opacity: 0; transform: translate(0, 0) rotate(0deg) scale(0.4); }
    30%  { opacity: 1; transform: translate(12px, -8px) rotate(-90deg) scale(1.1); }
    70%  { opacity: 0.9; transform: translate(18px, -18px) rotate(-180deg) scale(0.8); }
    100% { opacity: 0; transform: translate(24px, -28px) rotate(-270deg) scale(0.3); }
}

.ice-name-wrapper {
    display: inline-flex;
    align-items: center;
    position: relative;
    font-weight: 900;
    letter-spacing: 2px;
    background: linear-gradient(90deg, #00f2fe, #4facfe, #00c6ff, #ffffff, #00f2fe);
    background-size: 250% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: iceAuroraFlow 2.2s infinite linear;
}
.ice-crystal-1 {
    position: absolute;
    top: 30%;
    left: 15%;
    width: 6px;
    height: 6px;
    clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
    background: #ffffff;
    box-shadow: 0 0 8px #00e5ff;
    pointer-events: none;
    animation: snowDrift1 2.0s infinite ease-in-out;
}
.ice-crystal-2 {
    position: absolute;
    top: 40%;
    right: 15%;
    width: 7px;
    height: 7px;
    clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
    background: #b3e5fc;
    box-shadow: 0 0 10px #80d8ff;
    pointer-events: none;
    animation: snowDrift2 2.3s infinite ease-in-out 0.5s;
}

/* ================== 3. 顏寶容：霓虹極光哈士奇 ================== */
@keyframes huskyAurora {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}
@keyframes huskyHover {
    0%, 100% { transform: translateY(0) rotate(-5deg); }
    50% { transform: translateY(-3px) rotate(5deg); }
}
@keyframes huskyOrbit {
    to { transform: rotate(360deg); }
}
@keyframes huskyEyePulse {
    0%, 100% { opacity: .7; }
    50% { opacity: 1; }
}
@keyframes huskyEnergy {
    0% { opacity: 0; transform: translate(0, 8px) scale(.3) rotate(0deg); }
    35% { opacity: .9; }
    100% { opacity: 0; transform: translate(8px, -20px) scale(1) rotate(120deg); }
}
.husky-name-wrapper {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    position: relative;
    vertical-align: middle;
    isolation: isolate;
    white-space: nowrap;
}
.husky-name-text {
    font-weight: 900;
    letter-spacing: 1.5px;
    background: linear-gradient(100deg, #087da7, #00c8ed, #6844da, #b83bbe, #087da7);
    background-size: 300% auto;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 3px rgba(0, 200, 237, .45));
    animation: huskyAurora 3s ease-in-out infinite;
}
.husky-icon-box {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    position: relative;
    width: 36px;
    height: 36px;
    flex: 0 0 36px;
    line-height: 1;
    animation: huskyHover 2.4s ease-in-out infinite;
}
.husky-icon-box::before {
    content: "";
    position: absolute;
    inset: -1px;
    border-radius: 50%;
    border: 1px solid rgba(0, 220, 255, .4);
    border-top: 2px solid #00cfff;
    border-bottom: 2px solid #b05cff;
    box-shadow: 0 0 6px rgba(0, 207, 255, .45), inset 0 0 5px rgba(176, 92, 255, .2);
    animation: huskyOrbit 3s linear infinite;
    pointer-events: none;
}
.husky-face {
    position: relative;
    width: 32px;
    height: 32px;
    filter: drop-shadow(0 0 3px rgba(0, 207, 255, .6));
}
.husky-eyes {
    animation: huskyEyePulse 2.4s ease-in-out infinite;
}
.husky-energy {
    position: absolute;
    width: 4px;
    height: 4px;
    border-radius: 1px;
    background: #00ceef;
    box-shadow: 0 0 5px #00ceef;
    right: -4px;
    top: 20px;
    animation: huskyEnergy 2.6s ease-out infinite;
    pointer-events: none;
}
.husky-energy-purple {
    background: #ad61ff;
    box-shadow: 0 0 5px #ad61ff;
    right: 6px;
    animation-delay: 1.3s;
}
@media (prefers-reduced-motion: reduce) {
    .husky-name-text, .husky-icon-box, .husky-icon-box::before,
    .husky-eyes, .husky-energy { animation: none; }
    .husky-energy { display: none; }
}

/* ================== 表格整體風格 ================== */
.custom-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
    font-size: 15px;
    position: relative;
}
.custom-table tr {
    height: 48px !important;
    min-height: 48px !important;
    max-height: 48px !important;
    box-sizing: border-box;
}
.custom-table th, .custom-table td {
    padding: 0 12px !important;
    height: 48px !important;
    min-height: 48px !important;
    max-height: 48px !important;
    line-height: 48px !important;
    box-sizing: border-box;
    border: 1px solid rgba(128, 128, 128, 0.2);
    text-align: left;
    vertical-align: middle;
}
.custom-table th {
    background-color: rgba(128, 128, 128, 0.1);
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# 渲染角色名牌（俊丞、臨恩、寶容）
def render_player_flame(name_str, table_id="", is_top=None):
    name_str = escape(str(name_str))
    if is_top is None:
        return f'<span class="flame-name-wrapper">{name_str}<span class="flame-spark-1"></span><span class="flame-spark-2"></span></span>'
    if is_top:
        return f'<span class="smash-top-{table_id}"><span class="flame-name-wrapper">{name_str}<span class="flame-spark-1"></span><span class="flame-spark-2"></span></span><span class="explosion-core-{table_id}"></span></span>'
    return f'<span class="smash-bottom-{table_id}"><span class="flame-name-wrapper">{name_str}<span class="flame-spark-1"></span><span class="flame-spark-2"></span></span></span>'

def render_player_ice(name_str, table_id="", is_top=None):
    name_str = escape(str(name_str))
    if is_top is None:
        return f'<span class="ice-name-wrapper">{name_str}<span class="ice-crystal-1"></span><span class="ice-crystal-2"></span></span>'
    if is_top:
        return f'<span class="smash-top-{table_id}"><span class="ice-name-wrapper">{name_str}<span class="ice-crystal-1"></span><span class="ice-crystal-2"></span></span><span class="explosion-core-{table_id}"></span></span>'
    return f'<span class="smash-bottom-{table_id}"><span class="ice-name-wrapper">{name_str}<span class="ice-crystal-1"></span><span class="ice-crystal-2"></span></span></span>'

def render_player_collie(name_str):
    # 保留原函式名稱，讓所有名冊直接套用新的哈士奇特效。
    husky_svg = (
        '<svg class="husky-face" viewBox="0 0 64 64" width="32" height="32" '
        'fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="霓虹哈士奇">'
        '<path d="M12 28 L9 5 Q20 6 26 18 L38 18 Q44 6 55 5 L52 28 '
        'Q58 42 47 53 Q32 65 17 53 Q6 42 12 28Z" fill="#182d48" stroke="#55dfff" stroke-width="1.5"/>'
        '<path d="M14 22 L13 11 L23 21Z M41 21 L51 11 L50 22Z" fill="#a491cf"/>'
        '<path d="M12 31 Q17 25 25 29 L29 37 L32 20 L35 37 L39 29 Q47 25 52 31 '
        'L49 44 Q45 56 32 58 Q19 56 15 44Z" fill="#edf7ff"/>'
        '<path d="M14 30 Q20 25 27 30 L25 38 L17 38Z '
        'M37 30 Q44 25 50 30 L47 38 L39 38Z" fill="#253c5a"/>'
        '<g class="husky-eyes">'
        '<path d="M17 32 Q21 30 26 32 Q23 37 19 35Z '
        'M38 32 Q43 30 47 32 Q45 36 41 35Z" fill="#00dfff" stroke="#8ff4ff" stroke-width="1"/>'
        '<path d="M22 32 L22 35 M42 32 L42 35" stroke="#112338" stroke-width="1.7"/>'
        '</g>'
        '<path d="M27 42 Q32 39 37 42 L34 46 L30 46Z" fill="#122039"/>'
        '<path d="M32 46 L32 49 M25 49 Q28 53 32 49 Q36 53 39 49" '
        'stroke="#233a53" stroke-width="1.5" stroke-linecap="round"/>'
        '<path d="M17 42 L22 43 M42 43 L47 42" stroke="#97d9ed" stroke-width="1.3"/>'
        '</svg>'
    )
    return (
        '<span class="husky-name-wrapper">'
        f'<span class="husky-name-text">{escape(str(name_str))}</span>'
        f'<span class="husky-icon-box">{husky_svg}'
        '<span class="husky-energy"></span><span class="husky-energy husky-energy-purple"></span>'
        '</span></span>'
    )



def render_order_totals(orders_df):
    has_chen = any("俊丞" in str(name) for name in orders_df["姓名"])
    has_yeh = any("臨恩" in str(name) for name in orders_df["姓名"])
    is_clashing = has_chen and has_yeh

    total_qty = orders_df["份數"].sum()
    total_amount = orders_df["金額"].sum()
    col1, col2 = st.columns(2)
    col1.metric("總訂購件數", f"{total_qty} 份")
    col2.metric("總應收金額", f"${total_amount} 元")

    # 1. 店家點餐彙整
    st.markdown("**【店家點餐彙整】**")
    summary_df = orders_df.groupby(["店家", "餐點"])["份數"].sum().reset_index(name="數量")
    st.table(summary_df)

    # 2. 依人名統計每人應付金額
    st.markdown("**【每人應收金額】**")
    person_df = orders_df.groupby("姓名")["金額"].sum().reset_index(name="應付金額")

    # 計算人名表格中的行距與碰撞
    p_names = person_df["姓名"].tolist()
    p_chen_idx = next((i for i, n in enumerate(p_names) if "俊丞" in str(n)), None)
    p_yeh_idx = next((i for i, n in enumerate(p_names) if "臨恩" in str(n)), None)

    if is_clashing and p_chen_idx is not None and p_yeh_idx is not None:
        top_idx_p = min(p_chen_idx, p_yeh_idx)
        btm_idx_p = max(p_chen_idx, p_yeh_idx)
        st.markdown(generate_dynamic_clash_css("person", top_idx_p, btm_idx_p, row_height=48), unsafe_allow_html=True)

    person_html = '<table class="custom-table"><thead><tr><th>姓名</th><th>應付金額</th></tr></thead><tbody>'
    for idx, row in person_df.iterrows():
        name_str = str(row["姓名"])
        if "俊丞" in name_str:
            if is_clashing and p_chen_idx is not None and p_yeh_idx is not None:
                is_top = (p_chen_idx < p_yeh_idx)
                name_display = render_player_flame(name_str, table_id="person", is_top=is_top)
            else:
                name_display = render_player_flame(name_str)
        elif "臨恩" in name_str:
            if is_clashing and p_chen_idx is not None and p_yeh_idx is not None:
                is_top = (p_yeh_idx < p_chen_idx)
                name_display = render_player_ice(name_str, table_id="person", is_top=is_top)
            else:
                name_display = render_player_ice(name_str)
        elif "顏寶容" in name_str or "寶容" in name_str:
            name_display = render_player_collie(name_str)
        else:
            name_display = escape(name_str)
        
        person_html += f'<tr><td>{name_display}</td><td>${row["應付金額"]} 元</td></tr>'
    person_html += '</tbody></table>'
    st.markdown(person_html, unsafe_allow_html=True)

    # 3. 詳細點餐名冊
    st.markdown("**【詳細點餐名冊】**")
    d_names = orders_df["姓名"].tolist()
    d_chen_idx = next((i for i, n in enumerate(d_names) if "俊丞" in str(n)), None)
    d_yeh_idx = next((i for i, n in enumerate(d_names) if "臨恩" in str(n)), None)

    if is_clashing and d_chen_idx is not None and d_yeh_idx is not None:
        top_idx_d = min(d_chen_idx, d_yeh_idx)
        btm_idx_d = max(d_chen_idx, d_yeh_idx)
        st.markdown(generate_dynamic_clash_css("detail", top_idx_d, btm_idx_d, row_height=48), unsafe_allow_html=True)

    detail_html = '<table class="custom-table"><thead><tr><th>店家</th><th>姓名</th><th>餐點</th><th>份數</th><th>金額</th><th>備註</th></tr></thead><tbody>'
    for idx, row in orders_df.iterrows():
        name_str = str(row["姓名"])
        if is_clashing and d_chen_idx is not None and d_yeh_idx is not None:
            if idx == d_chen_idx:
                is_top = (d_chen_idx < d_yeh_idx)
                name_display = render_player_flame(name_str, table_id="detail", is_top=is_top)
            elif idx == d_yeh_idx:
                is_top = (d_yeh_idx < d_chen_idx)
                name_display = render_player_ice(name_str, table_id="detail", is_top=is_top)
            elif "俊丞" in name_str:
                name_display = render_player_flame(name_str)
            elif "臨恩" in name_str:
                name_display = render_player_ice(name_str)
            elif "顏寶容" in name_str or "寶容" in name_str:
                name_display = render_player_collie(name_str)
            else:
                name_display = escape(name_str)
        else:
            if "俊丞" in name_str:
                name_display = render_player_flame(name_str)
            elif "臨恩" in name_str:
                name_display = render_player_ice(name_str)
            elif "顏寶容" in name_str or "寶容" in name_str:
                name_display = render_player_collie(name_str)
            else:
                name_display = escape(name_str)

        detail_html += f'<tr><td>{escape(str(row["店家"]))}</td><td>{name_display}</td><td>{escape(str(row["餐點"]))}</td><td>{row["份數"]}</td><td>${row["金額"]}</td><td>{escape(str(row["備註"]))}</td></tr>'
    detail_html += '</tbody></table>'
    st.markdown(detail_html, unsafe_allow_html=True)



def render_shop_notes(shop):
    if shop == "食材有限":
        st.caption("涼粉可選酸辣、胡麻、綜合。滷味可選原味、小辣、中辣、大辣，請填在備註。")
        st.caption("木耳、娃娃菜、杏鮑菇、高麗菜任選兩樣 $50，請備註品項。")
        st.caption("滷味滿 $100 才提供盒裝。單份未滿 $50，店家另收 $20 拌炒費，請於結帳時核對。")

    if shop == "痴飯吧":
        st.caption("會議便當 $200～$300，請先向店家確認菜色與價格。")
        st.caption("3 公里內滿 10 個免費外送。大量訂購請提前來電或私訊預訂。訂購電話 0913-026-253。")


TAIPEI = ZoneInfo("Asia/Taipei")
GROUP_FIELDS = "id,restaurant,created_at,closes_at,closed_at"
ORDER_FIELDS = "id,group_id,name,items,revision"
RPC_ERRORS = {
    "already_open": "已有一團正在收單。",
    "closed": "這團已停止收單。請重新整理查看最新狀態。",
    "conflict": "這筆訂單已在另一個頁面更新。請重新開啟專屬連結後再修改。",
    "invalid": "請確認截止時間、餐點份數與備註。",
    "unavailable": "找不到這筆訂單，請確認專屬連結。",
}


def rpc(endpoint, **payload):
    result = database_request("POST", "rpc/" + endpoint, payload)
    if result != "ok":
        raise StorageError(RPC_ERRORS.get(result, "資料庫未確認成功，請重新整理後再試。"))


def read_rows(query, single=False):
    rows = []
    while True:
        page = database_request("GET", query + ("&limit=1" if single else f"&limit=500&offset={len(rows)}"))
        if not isinstance(page, list):
            raise StorageError("資料庫回傳格式有誤。")
        if single:
            return next(iter(page), None)
        rows.extend(page)
        if len(page) < 500:
            return rows


def get_group(group_id):
    return read_rows(f"lunch_groups?select={GROUP_FIELDS},menu&id=eq.{group_id}", single=True)


def cutoff(group):
    return datetime.fromisoformat(group["closes_at"]).astimezone(TAIPEI)


def is_open(group):
    return group is not None and group["closed_at"] is None and datetime.now(TAIPEI) < cutoff(group)


def new_link():
    return f"{uuid.uuid4()}.{secrets.token_urlsafe(32)}"


def link_parts(link):
    order_id, _, token = link.partition(".")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise ValueError
    return str(uuid.UUID(order_id)), hashlib.sha256(token.encode()).hexdigest()


def group_label(group):
    return f'{cutoff(group):%m/%d %H:%M}｜{group["restaurant"]}'


def group_orders(group, rows):
    columns = ["店家", "姓名", "餐點", "份數", "單價", "金額", "備註"]
    return pd.DataFrame([
        {"店家": group["restaurant"], "姓名": order["name"], "餐點": line["dish"],
         "份數": line["qty"], "單價": line["unit_price"], "金額": line["qty"] * line["unit_price"],
         "備註": line["notes"]}
        for order in rows for line in order["items"]
    ], columns=columns)


def admin_panel(group):
    with st.sidebar:
        st.header("揪團管理")
        try:
            password = st.secrets.get("admin_password", "")
        except FileNotFoundError:
            password = ""
        if not password:
            st.caption("請在 Streamlit Secrets 設定 admin_password 後使用管理功能。")
            return False
        if not st.session_state.get("lunch_admin"):
            with st.form("admin_login"):
                entered = st.text_input("管理密碼", type="password")
                if st.form_submit_button("登入管理"):
                    if secrets.compare_digest(str(password).encode(), entered.encode()):
                        st.session_state["lunch_admin"] = True
                        st.rerun()
                    st.error("管理密碼錯誤。")
            return False
        if st.button("登出管理"):
            st.session_state.pop("lunch_admin", None)
            st.rerun()
        if st.session_state.pop("group_admin_saved", False):
            st.success("開團設定已儲存。")
        now = datetime.now(TAIPEI)
        if group and st.session_state.get("group_open_draft") == group["id"]:
            st.session_state.pop("group_open_draft")
        if group and group["closed_at"] is None:
            st.caption(f'最近一團｜{group_label(group)}')
            with st.form("lunch_extend_" + group["id"]):
                default = st.session_state.setdefault(
                    "extend_default_" + group["id"], max(cutoff(group), now) + timedelta(minutes=15)
                )
                day = st.date_input("延長至日期", value=default.date())
                time = st.time_input("延長至時間", value=default.time())
                extend = st.form_submit_button("延長截止時間")
            close = st.button("立即結單")
            if extend or close:
                try:
                    rpc("lunch_change_group", p_id=group["id"], p_close=close,
                        p_deadline=datetime.combine(day, time, TAIPEI).isoformat() if extend else None)
                except StorageError as error:
                    st.error(str(error))
                else:
                    st.session_state.pop("extend_default_" + group["id"], None)
                    st.session_state["group_admin_saved"] = True
                    st.rerun()
        if not is_open(group):
            with st.form("lunch_open_group"):
                shop = st.selectbox("開團店家", list(RESTAURANT_MENUS))
                default = st.session_state.setdefault("open_default", now + timedelta(hours=1))
                day = st.date_input("截止日期", value=default.date())
                time = st.time_input("截止時間", value=default.time())
                if st.form_submit_button("開團", type="primary"):
                    draft_id = st.session_state.setdefault("group_open_draft", str(uuid.uuid4()))
                    try:
                        rpc("lunch_create_group", p_id=draft_id, p_restaurant=shop, p_menu=RESTAURANT_MENUS[shop],
                            p_deadline=datetime.combine(day, time, TAIPEI).isoformat())
                    except StorageError as error:
                        st.error(str(error))
                    else:
                        st.session_state.pop("group_open_draft", None)
                        st.session_state.pop("open_default", None)
                        st.session_state["group_admin_saved"] = True
                        st.rerun()
        return True


def update_order_as_admin(group, order, items):
    if not st.session_state.get("lunch_admin"):
        raise StorageError("請先登入揪團管理。")
    order_id = str(uuid.UUID(order["id"]))
    group_id = str(uuid.UUID(group["id"]))
    revision = int(order["revision"])
    saved_items = [dict(line, unit_price=group["menu"][line["dish"]]) for line in items]
    changed = database_request(
        "PATCH",
        f"lunch_group_orders?id=eq.{order_id}&group_id=eq.{group_id}&revision=eq.{revision}&select=id",
        {"items": saved_items, "revision": revision + 1},
        prefer="return=representation",
    )
    if changed == []:
        raise StorageError(RPC_ERRORS["conflict"])
    if changed != [{"id": order_id}]:
        raise StorageError("資料庫未確認修改成功，請重新整理並核對訂單。")


def order_editor(group, link=None, order=None, *, admin=False):
    if admin:
        order_id = order["id"]
    else:
        order_id, token_hash = link_parts(link)
    revision = order["revision"] if order else 0
    mode = "admin" if admin else "customer"
    prefix = f"order_{mode}_{order_id}_{revision}"
    if order:
        name = order["name"]
    else:
        member = st.selectbox("選擇點餐人員", MEMBERS, index=None, key=prefix + "_member")
        name = st.text_input("姓名／暱稱", max_chars=80, key=prefix + "_name") if member == MEMBERS[-1] else member

    menu = group["menu"]
    preferred = RESTAURANT_MENUS.get(group["restaurant"], {})
    dishes = list(dict.fromkeys([dish for dish in preferred if dish in menu] + list(menu)))
    defaults = order["items"] if order else []
    count_key = prefix + "_count"
    count = st.session_state.setdefault(count_key, max(len(defaults), 1))
    items = []
    for index in range(count):
        saved = defaults[index] if index < len(defaults) else {}
        item_key = f"{prefix}_{index}"
        left, right = st.columns([3, 1])
        dish = left.selectbox(
            f"第 {index + 1} 項餐點", dishes,
            index=dishes.index(saved["dish"]) if saved else None,
            format_func=lambda value: f"{value}（NT$ {menu[value]}）", key=item_key + "_dish",
        )
        qty = right.number_input(f"第 {index + 1} 項份數", min_value=1, max_value=99,
                                 value=saved.get("qty", 1), key=item_key + "_qty")
        note = st.text_input(f"第 {index + 1} 項備註", value=saved.get("notes", ""),
                             max_chars=150, key=item_key + "_note")
        if dish:
            items.append({"dish": dish, "qty": qty, "notes": note.strip()})
    if count < 20 and st.button("＋ 新增一項餐點", key=prefix + "_add"):
        st.session_state[count_key] += 1
        st.rerun()
    st.caption("同款餐點有不同口味時，可以加一項再選一次。清空餐點選擇可移除該項。")
    total = sum(menu[line["dish"]] * line["qty"] for line in items)
    st.write(f"**餐點小計 NT$ {total:,}**")
    if st.button("儲存修改" if order else "送出訂單", type="primary", key=prefix + "_save"):
        if not name or not name.strip() or not items:
            st.error("請填寫姓名並至少選一項餐點。")
            return
        try:
            if admin:
                update_order_as_admin(group, order, items)
            else:
                rpc("lunch_save_group_order", p_group=group["id"], p_order=order_id, p_hash=token_hash,
                    p_name=name.strip(), p_items=items, p_revision=revision)
        except StorageError as error:
            if not order:
                st.session_state["pending_order_link"] = link
            st.error(str(error))
            return
        if admin:
            st.session_state["admin_order_saved"] = group["id"]
            st.rerun()
        st.session_state["order_saved"] = "修改已儲存。" if order else "已收到你的訂單。"
        if not order:
            st.session_state.pop("pending_order_link", None)
            st.session_state.pop("draft_" + group["id"], None)
            st.session_state["last_order_link"] = link
            st.query_params["order"] = link
        st.rerun()


def show_my_order(link):
    st.subheader("我的訂單")
    if st.button("返回今日點餐"):
        del st.query_params["order"]
        st.rerun()
    try:
        order_id, token_hash = link_parts(link)
    except ValueError:
        st.warning("專屬連結格式有誤。")
        return
    order = read_rows(
        f"lunch_group_orders?select={ORDER_FIELDS}&id=eq.{order_id}&edit_hash=eq.{token_hash}", single=True)
    if order is None:
        st.warning("找不到這筆訂單，請確認使用的是完整的專屬連結。")
        return
    group = get_group(order["group_id"])
    if not group:
        st.warning("這筆訂單的開團資料無法讀取。")
        return
    st.session_state["last_order_link"] = link
    if st.session_state.get("pending_order_link") == link:
        st.session_state.pop("pending_order_link")
        st.session_state.pop("draft_" + group["id"], None)
    if message := st.session_state.pop("order_saved", None):
        st.success(message)
    st.write(f'**{order["name"]}｜{group["restaurant"]}**')
    st.caption("請保留目前網址。持有這個專屬連結的人可以查看訂單，並在截止前修改。")
    st.table(pd.DataFrame([
        {"餐點": line["dish"], "份數": line["qty"],
         "金額": line["unit_price"] * line["qty"], "備註": line["notes"]}
        for line in order["items"]
    ]))
    total = sum(line["unit_price"] * line["qty"] for line in order["items"])
    st.write(f"**應付 NT$ {total:,}**")
    if is_open(group):
        with st.expander(f"修改訂單（{cutoff(group):%m/%d %H:%M} 截止）"):
            order_editor(group, link, order)
    else:
        st.info("這團已截止，現在可以查看訂單。")


def render_group_results(group, admin):
    fields = ORDER_FIELDS if admin else "name,items"
    rows = read_rows(
        f'lunch_group_orders?select={fields}&group_id=eq.{group["id"]}&order=created_at.asc,id.asc'
    )
    orders = group_orders(group, rows)
    if orders.empty:
        st.info("這團目前沒有訂單。")
        return
    if admin:
        if st.session_state.get("admin_order_saved") == group["id"]:
            st.session_state.pop("admin_order_saved")
            st.success("訂單修改已儲存。")
        with st.expander("管理員修改訂單"):
            by_id = {order["id"]: order for order in rows}
            labels = {
                order["id"]: (
                    f'{index}. {order["name"]}｜'
                    + "、".join(f'{item["dish"]} × {item["qty"]}' for item in order["items"])
                )
                for index, order in enumerate(rows, 1)
            }
            selected = st.selectbox(
                "選擇要修改的訂單", list(by_id), index=None, format_func=labels.__getitem__,
                key="admin_order_picker_" + group["id"],
            )
            if selected:
                if not is_open(group):
                    st.caption("這團已結單。若已向店家下單，請同步通知店家。")
                group_with_menu = get_group(group["id"])
                if group_with_menu:
                    order_editor(group_with_menu, order=by_id[selected], admin=True)
                else:
                    st.warning("無法讀取本團菜單，請重新整理後再試。")
    render_order_totals(orders)
    st.download_button("下載本團訂單 CSV", orders.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f'午餐訂單_{cutoff(group):%Y%m%d_%H%M}.csv', mime="text/csv")


def render_legacy_orders(admin):
    orders = load_orders()
    if admin:
        with st.expander("匯入舊訂單 CSV"):
            uploaded = st.file_uploader("選擇舊訂單報表", type=["csv"])
            if st.button("匯入舊訂單"):
                if uploaded is None:
                    st.error("請先選擇 CSV 檔案。")
                else:
                    try:
                        import_legacy_orders(uploaded.getvalue())
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        st.session_state["legacy_imported"] = True
                        st.rerun()
    if st.session_state.pop("legacy_imported", False):
        st.success("舊訂單已匯入。")
    if orders.empty:
        st.info("目前沒有舊版訂單。")
        return
    render_order_totals(orders.assign(份數=1))
    st.download_button("下載舊版訂單 CSV", orders.drop(columns=["_order_id"]).to_csv(index=False).encode("utf-8-sig"),
                       file_name="舊版午餐訂單.csv", mime="text/csv")
    if admin:
        with st.expander("刪除指定的舊訂單"):
            labels = {
                row["_order_id"]: f'{index + 1}. {row["姓名"]}｜{row["餐點"]}｜{row["備註"]}'
                for index, row in orders.iterrows()
            }
            selected = st.selectbox("舊訂單", list(labels), index=None, format_func=labels.__getitem__)
            if selected and st.button("刪除這筆舊訂單"):
                delete_order(selected)
                st.rerun()


def main():
    link = st.query_params.get("order")
    if link is not None:
        show_my_order(link)
        return
    group_query = f"lunch_groups?select={GROUP_FIELDS}&order=created_at.desc,id.desc"
    group = read_rows(group_query, single=True)
    admin = admin_panel(group)
    page = st.radio("功能", ["今日點餐", "本團統計", "歷史紀錄"], horizontal=True, label_visibility="collapsed")
    if page == "歷史紀錄":
        groups = {entry["id"]: entry for entry in read_rows(group_query)}
        selection = st.selectbox(
            "選擇開團紀錄", ["legacy", *groups],
            format_func=lambda key: "舊版訂單" if key == "legacy" else group_label(groups[key]),
            index=1 if groups else 0,
        )
        if selection == "legacy":
            render_legacy_orders(admin)
        else:
            render_group_results(groups[selection], admin)
        return

    if pending := st.session_state.get("pending_order_link"):
        if st.button("查詢剛送出的訂單"):
            st.query_params["order"] = pending
            st.rerun()
    if st.session_state.get("last_order_link") and st.button("查看我的上一筆訂單"):
        st.query_params["order"] = st.session_state["last_order_link"]
        st.rerun()
    if group is None:
        st.info("目前尚未開團。")
        return
    st.subheader(group["restaurant"])
    status = "收單中" if is_open(group) else "已截止"
    stop = datetime.fromisoformat(group["closed_at"]).astimezone(TAIPEI) if group["closed_at"] else cutoff(group)
    st.caption(f"{status}｜{stop:%m/%d %H:%M} 截止（台灣時間）")
    if page == "本團統計":
        render_group_results(group, admin)
    elif is_open(group):
        active = get_group(group["id"])
        if not is_open(active):
            st.info("這團剛停止收單，請重新整理查看最新狀態。")
            return
        render_shop_notes(group["restaurant"])
        link = st.session_state.setdefault("draft_" + group["id"], new_link())
        order_editor(active, link)


try:
    main()
except StorageError as error:
    st.error(str(error))
