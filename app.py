import streamlit as st
import pandas as pd
from datetime import date
import os

st.set_page_config(page_title="今日午餐點餐系統", page_icon="🍱", layout="centered")
st.title("🍱 今日午餐點餐小幫手")
st.caption(f"點餐日期：{date.today().strftime('%Y-%m-%d')}")

# 共用資料儲存檔案
DATA_FILE = "orders_data.csv"
ADMIN_PASSWORD = "0000"

# 讀取共用訂單資料
def load_orders():
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE)
        except Exception:
            return pd.DataFrame(columns=["店家", "姓名", "餐點", "金額", "備註"])
    return pd.DataFrame(columns=["店家", "姓名", "餐點", "金額", "備註"])

# 儲存共用訂單資料
def save_orders(df):
    df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')

# 常用同事名單
MEMBERS = [
    "葉臨恩",
    "陳俊丞",
    "楊承凱", "倪宗安", "王國祐", "呂盈毅", "謝嘉雲", "顏寶容", "章哲勳", "陳威成",
    "謝文玲", "李雨柔", "皮爵赫", "陳柏伸", "黃志成", "陳柏邑", "盧廷謙", "王宗瑜",
    "李佳航", "楊書維", "張瀚允", "陳柏豪", "曾柏豪", "周秀苓", "許皓翔", "胡煥然",
    "陳永河", "秦昇瑜", "張駿謙", "王慧珍", "黃浚宏", "怡君", "fish",
    # --- BIM 團隊同仁 ---
    "林詩珊", "謝淳淇", "歐柏鋒", "林慧語", "吳詩田",
    # --- 彈性輸入 ---
    "其他 / 手動輸入"
]

# 多店家完整菜單資料庫
RESTAURANT_MENUS = {
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
    "熊仔廚房": {
        "蛋炒飯": 60, "肉絲炒飯": 80, "香腸炒飯": 80, "蝦仁炒飯": 80, "綜合炒飯": 90,
        "炸豬排炒飯": 100, "炸雞排炒飯": 100, "椒鹽雞丁炒飯": 100, "炸蝦排炒飯": 100,
        "炸雞腿炒飯": 100, "起司豬排炒飯": 100, "秘製燒肉炒飯": 100, "黃金大腿炒飯": 120,
        "炸豬排飯": 100, "炸雞排飯": 100, "炸蝦排飯": 100, "炸雞腿飯": 100,
        "打拋豬飯": 100, "椒鹽雞丁飯": 100, "泡菜燒肉飯": 100, "香煎鯖魚飯": 100,
        "限量爌肉飯": 100, "秘製燒肉飯": 100, "起司豬排飯": 100, "咖哩豬排飯": 110,
        "咖哩雞排飯": 110, "黃金大腿飯": 120, "韭菜手工大水餃(10顆)": 100,
        "玉米手工大水餃(10顆)": 100, "高麗菜手工大水餃(10顆)": 100,
        "泡菜手工大水餃(10顆)": 120, "剝皮辣椒手工大水餃(10顆)": 120, "荷包蛋": 15,
        "炸豬排(單點)": 50, "炸雞排(單點)": 50, "炸蝦排(單點)": 50, "炸雞腿(單點)": 50,
        "椒鹽雞丁(單點)": 50, "限量爌肉(單點)": 50, "香煎鯖魚(單點)": 50, "秘製燒肉(單點)": 50,
        "起司豬排(單點)": 50, "黃金大腿(單點)": 70, "丸子湯": 30, "味噌湯": 30,
        "青菜蛋花湯": 30, "綜合丸子湯": 50,
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
        "冰淇淋芒果綠/芒果青(M)": 45, "冰淇淋芒果綠/芒果青(L)": 50, "桂花釀紅/綠/青/烏(M)": 35,
        "桂花釀紅/綠/青/烏(L)": 40, "脆梅玉露/青茶(M)": 45, "脆梅玉露/青茶(L)": 50,
        "脆梅檸檬(M)": 45, "脆梅檸檬(L)": 50, "新鮮香橙綠(M)": 55, "新鮮香橙綠(L)": 60,
        "紅鑽葡萄柚綠(M)": 50, "紅鑽葡萄柚綠(L)": 55, "鳳梨水果冰茶(M)": 50, "鳳梨水果冰茶(L)": 55,
        "鳳梨青茶(M)": 50, "鳳梨青茶(L)": 55, "鮮甘蔗綠/青(M)": 55, "鮮甘蔗綠/青(L)": 60,
        "甘蔗鮮檸檬(M)": 60, "甘蔗鮮檸檬(L)": 65, "蜂蜜鮮檸檬(M)": 50, "蜂蜜鮮檸檬(L)": 55,
        "翡翠檸檬/紅/青(M)": 45, "翡翠檸檬/紅/青(L)": 50, "鮮百香果綠/青(M)": 40, "鮮百香果綠/青(L)": 45,
        "百香蜜冬瓜(M)": 40, "百香蜜冬瓜(L)": 45, "金桔檸檬汁(M)": 40, "金桔檸檬汁(L)": 45,
        "冬瓜鮮檸檬(M)": 40, "冬瓜鮮檸檬(L)": 45, "芭樂綠(M)": 55, "芭樂綠(L)": 60,
        "芭樂柳丁綠(M)": 60, "芭樂柳丁綠(L)": 65, "芭樂檸檬綠(M)": 60, "芭樂檸檬綠(L)": 65,
        "芭樂多多(M)": 60, "芭樂多多(L)": 65, "黑糖波霸鮮奶(固定)(M)": 60, "黑糖波霸鮮奶(固定)(L)": 75,
        "紅茶/綠茶/青茶那提(M)": 50, "紅茶/綠茶/青茶那提(L)": 55, "厚底烏龍那提(M)": 50,
        "厚底烏龍那提(L)": 55, "冬瓜那提(M)": 50, "冬瓜那提(L)": 55, "咖啡那提(M)": 50,
        "咖啡那提(L)": 75, "甘蔗鮮奶茶(M)": 60, "甘蔗鮮奶茶(L)": 70,
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
        "香腸飯": 85, "原味咔啦雞飯": 85, "辣味咔啦雞飯": 85, "招牌飯": 90,
        "滷棒腿飯": 90, "薄鹽鯖魚飯": 90, "叉燒飯": 95, "養生飯": 95,
        "蒲燒魚飯": 95, "鐵路排骨飯": 95, "炸排骨飯": 95, "爌肉飯": 100,
        "法式豬排飯": 100, "菲力豬排飯": 105, "塔香無骨雞排飯": 105, "香雞排飯": 110,
        "黑胡椒牛柳飯": 110, "和風烤雞飯": 115, "炸雞腿飯": 120, "挪威鯖魚飯": 110,
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
    },
    "超級大盛": {
        "超吉燒肉丼飯": 99, "泡菜燒肉丼飯": 105, "打拋豬肉丼飯": 110, "照燒雞腿丼飯": 115,
        "黃金豬排丼飯": 115, "和風牛肉丼飯": 120, "厚燒排骨丼飯": 125, "蜜汁雞排丼飯": 135,
        "A餐優惠: 現烤香腸 + 精選湯品 (三選一備註)": 35,
        "B餐優惠: 現烤香腸 + 手作好茶 (三選一備註)": 50,
        "日式味噌湯": 30, "鮮採竹筍湯": 30, "大根貢丸湯": 30, "現烤香腸": 15,
        "韓國泡菜": 35, "現煎荷包蛋": 15, "花露冷萃茶": 45, "桂圓冬瓜茶": 45, "山採女兒紅": 45,
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
    }
}

# 注入名牌左右對撞動畫 CSS
st.markdown("""
<style>
/* 常態烈焰字體（僅俊丞一人時） */
@keyframes flameSolo {
    0% { color: #ff3b00; text-shadow: 0 0 5px #ffaa00, 0 0 10px #ff2200; }
    50% { color: #ff8800; text-shadow: 0 0 10px #ffff00, 0 0 18px #ff4400; }
    100% { color: #ff3b00; text-shadow: 0 0 5px #ffaa00, 0 0 10px #ff2200; }
}
.flame-solo {
    display: inline-block;
    font-weight: 900;
    letter-spacing: 2px;
    animation: flameSolo 1.2s infinite alternate ease-in-out;
}

/* 常態極冰字體（僅臨恩一人時） */
@keyframes iceSolo {
    0% { color: #0091ea; text-shadow: 0 0 5px #80d8ff, 0 0 10px #00e5ff; }
    50% { color: #00e5ff; text-shadow: 0 0 10px #ffffff, 0 0 18px #00b0ff; }
    100% { color: #0091ea; text-shadow: 0 0 5px #80d8ff, 0 0 10px #00e5ff; }
}
.ice-solo {
    display: inline-block;
    font-weight: 900;
    letter-spacing: 2px;
    animation: iceSolo 1.4s infinite alternate ease-in-out;
}

/* 俊丞（烈焰衝撞）：從左側蓄力 ➔ 猛烈向右衝擊 ➔ 撞擊震退 */
@keyframes chargeRight {
    0% {
        transform: translateX(0px) scale(1);
        text-shadow: 0 0 5px #ff4500;
    }
    35% {
        /* 蓄力後撤 */
        transform: translateX(-15px) scale(0.95);
        text-shadow: 0 0 12px #ff2200, 0 0 20px #ffaa00;
    }
    50% {
        /* 猛烈衝向右方中央碰撞！ */
        transform: translateX(45px) scale(1.18);
        text-shadow: 0 0 25px #ffff00, 0 0 40px #ff0000;
    }
    60% {
        /* 碰撞彈回受力震動 */
        transform: translateX(5px) scale(1.05);
        text-shadow: 0 0 15px #ff5500;
    }
    100% {
        transform: translateX(0px) scale(1);
        text-shadow: 0 0 5px #ff4500;
    }
}

.charge-chen {
    display: inline-block;
    font-weight: 900;
    color: #ff3b00;
    letter-spacing: 2px;
    animation: chargeRight 1.5s infinite cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

/* 臨恩（極冰衝撞）：從右側蓄力 ➔ 猛烈向左衝擊 ➔ 撞擊震退 */
@keyframes chargeLeft {
    0% {
        transform: translateX(0px) scale(1);
        text-shadow: 0 0 5px #00b0ff;
    }
    35% {
        /* 蓄力後撤 */
        transform: translateX(15px) scale(0.95);
        text-shadow: 0 0 12px #0070f3, 0 0 20px #80d8ff;
    }
    50% {
        /* 猛烈衝向左方中央碰撞！ */
        transform: translateX(-45px) scale(1.18);
        text-shadow: 0 0 25px #ffffff, 0 0 40px #00e5ff;
    }
    60% {
        /* 碰撞彈回受力震動 */
        transform: translateX(-5px) scale(1.05);
        text-shadow: 0 0 15px #0091ea;
    }
    100% {
        transform: translateX(0px) scale(1);
        text-shadow: 0 0 5px #00b0ff;
    }
}

.charge-yeh {
    display: inline-block;
    font-weight: 900;
    color: #00b0ff;
    letter-spacing: 2px;
    animation: chargeLeft 1.5s infinite cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.custom-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
    font-size: 15px;
}
.custom-table th, .custom-table td {
    padding: 14px 10px;
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

# --- 點餐區 ---
st.subheader("📝 我要點餐")

selected_restaurant = st.selectbox("選擇今日訂購店家", list(RESTAURANT_MENUS.keys()))
current_menu = RESTAURANT_MENUS[selected_restaurant]

# 名字選擇
selected_member = st.selectbox("選擇點餐人員", MEMBERS)

with st.form(key="order_form", clear_on_submit=True):
    custom_name = ""
    if selected_member == "其他 / 手動輸入":
        custom_name = st.text_input("請輸入你的名字 / 暱稱", placeholder="例如：新同仁")
    
    selected_items = st.multiselect(
        "選擇餐點品項（可多選）", 
        list(current_menu.keys()),
        format_func=lambda x: f"{x} (${current_menu[x]} 元)"
    )
    
    notes = st.text_input("備註（可留空）", placeholder="例如：微糖微冰、熱飲、飯少、炒飯加辣等")
    submit_button = st.form_submit_button(label="🚀 送出訂單")

    if submit_button:
        final_name = custom_name.strip() if selected_member == "其他 / 手動輸入" else selected_member
        
        if not final_name:
            st.error("請填寫名字後再送出！")
        elif not selected_items:
            st.error("請至少選擇一項餐點！")
        else:
            current_df = load_orders()
            
            new_rows = []
            for item in selected_items:
                price = current_menu[item]
                new_rows.append({
                    "店家": selected_restaurant,
                    "姓名": final_name,
                    "餐點": item,
                    "金額": price,
                    "備註": notes.strip() if notes.strip() else "無"
                })
            
            updated_df = pd.concat([current_df, pd.DataFrame(new_rows)], ignore_index=True)
            save_orders(updated_df)
            
            user_total = sum(current_menu[item] for item in selected_items)
            st.success(f"已記錄 {final_name} 的訂單！共 {len(selected_items)} 樣，個人小計：${user_total} 元")
            st.rerun()

# --- 統計與明細區 ---
st.divider()
st.subheader("📊 目前點餐狀況與統計")

orders_df = load_orders()

if not orders_df.empty:
    has_chen = any("俊丞" in str(name) for name in orders_df["姓名"])
    has_yeh = any("臨恩" in str(name) for name in orders_df["姓名"])
    is_clashing = has_chen and has_yeh

    total_qty = len(orders_df)
    total_amount = orders_df["金額"].sum()
    col1, col2 = st.columns(2)
    col1.metric("總訂購件數", f"{total_qty} 份")
    col2.metric("總應收金額", f"${total_amount} 元")

    # 1. 店家點餐彙整
    st.markdown("**【店家點餐彙整】**")
    summary_df = orders_df.groupby(["店家", "餐點"]).size().reset_index(name="數量")
    st.table(summary_df)

    # 2. 依人名統計每人應付金額
    st.markdown("**【每人應收金額】**")
    person_df = orders_df.groupby("姓名")["金額"].sum().reset_index(name="應付金額")

    person_html = '<table class="custom-table"><thead><tr><th>姓名</th><th>應付金額</th></tr></thead><tbody>'
    for idx, row in person_df.iterrows():
        name_str = str(row["姓名"])
        if "俊丞" in name_str:
            if is_clashing:
                name_display = f'<span class="charge-chen">{name_str}</span>'
            else:
                name_display = f'<span class="flame-solo">{name_str}</span>'
        elif "臨恩" in name_str:
            if is_clashing:
                name_display = f'<span class="charge-yeh">{name_str}</span>'
            else:
                name_display = f'<span class="ice-solo">{name_str}</span>'
        else:
            name_display = name_str
        
        person_html += f'<tr><td>{name_display}</td><td>${row["應付金額"]} 元</td></tr>'
    person_html += '</tbody></table>'
    st.markdown(person_html, unsafe_allow_html=True)

    # 3. 詳細點餐名冊
    st.markdown("**【詳細點餐名冊】**")
    detail_html = '<table class="custom-table"><thead><tr><th>店家</th><th>姓名</th><th>餐點</th><th>金額</th><th>備註</th></tr></thead><tbody>'
    for idx, row in orders_df.iterrows():
        name_str = str(row["姓名"])
        if "俊丞" in name_str:
            if is_clashing:
                name_display = f'<span class="charge-chen">{name_str}</span>'
            else:
                name_display = f'<span class="flame-solo">{name_str}</span>'
        elif "臨恩" in name_str:
            if is_clashing:
                name_display = f'<span class="charge-yeh">{name_str}</span>'
            else:
                name_display = f'<span class="ice-solo">{name_str}</span>'
        else:
            name_display = name_str

        detail_html += f'<tr><td>{row["店家"]}</td><td>{name_display}</td><td>{row["餐點"]}</td><td>${row["金額"]}</td><td>{row["備註"]}</td></tr>'
    detail_html += '</tbody></table>'
    st.markdown(detail_html, unsafe_allow_html=True)

    # --- 刪除特定訂單功能（含密碼保護） ---
    with st.expander("🛠️ 訂單修改 / 刪除管理（需管理密碼）"):
        st.write("若點錯餐點，可在此選取並單筆刪除：")
        
        order_options = [
            f"編號 {idx + 1}: 【{row['姓名']}】 {row['餐點']} (${row['金額']}元) - 備註: {row['備註']}"
            for idx, row in orders_df.iterrows()
        ]
        
        selected_order_to_delete = st.selectbox("選擇要刪除的訂單項目", order_options)
        del_pwd = st.text_input("輸入管理密碼以確認刪除", type="password", placeholder="請輸入4位數密碼")
        
        if st.button("❌ 確認刪除此筆餐點"):
            if del_pwd == ADMIN_PASSWORD:
                selected_idx = order_options.index(selected_order_to_delete)
                updated_df = orders_df.drop(index=selected_idx).reset_index(drop=True)
                save_orders(updated_df)
                st.success("該筆訂單已成功刪除！")
                st.rerun()
            else:
                st.error("密碼錯誤，無法刪除！")

    st.write("")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        csv_data = orders_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下載今日訂單報表 (CSV)",
            data=csv_data,
            file_name=f"午餐訂單_{date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    with col_btn2:
        with st.popover("🗑️ 清空所有訂單（重新開團）"):
            st.write("⚠️ 此動作會清空今日所有點餐資料！")
            clear_pwd = st.text_input("請輸入管理密碼確認清空", type="password", key="clear_all_pwd")
            if st.button("確認全數清空"):
                if clear_pwd == ADMIN_PASSWORD:
                    if os.path.exists(DATA_FILE):
                        os.remove(DATA_FILE)
                    st.success("已清空所有訂單！")
                    st.rerun()
                else:
                    st.error("密碼錯誤！")
else:
    st.info("目前還沒有任何人點餐，快當第一個！")
