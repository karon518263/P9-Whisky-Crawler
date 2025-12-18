import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. 網頁基礎設定 ---
st.set_page_config(
    page_title="P9 威士忌行情戰情室",
    page_icon="🥃",
    layout="wide"
)

# --- 2. 連線資料庫函數 ---
def load_data():
    conn = sqlite3.connect("p9_whisky.db")
    query = "SELECT post_date, title, author, product_name, price, link FROM market_prices ORDER BY id DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # 🔥 關鍵修正：將「日期字串」轉為「日期物件」，這樣才能用日曆篩選
    # errors='coerce' 代表如果遇到怪怪的日期格式就跳過，不報錯
    df['post_date_dt'] = pd.to_datetime(df['post_date'], format='%Y/%m/%d', errors='coerce').dt.date
    
    return df

# --- 3. 網頁主程式 ---
st.title("🥃 P9 威士忌行情監控系統")
st.markdown("---")

try:
    df = load_data()

    # === 側邊欄：進階篩選區 ===
    st.sidebar.header("🔍 綜合篩選條件")
    
    # 1. [原有] 關鍵字搜尋 (搜酒名/標題)
    keyword = st.sidebar.text_input("🥃 關鍵字搜尋 (酒名/標題)", "", placeholder="例如: 麥卡倫, 12年...")
    
    # 2. [新增] 賣家搜尋
    author_keyword = st.sidebar.text_input("👤 賣家帳號搜尋", "", placeholder="輸入賣家 ID")

    # 3. [新增] 日期範圍篩選
    if not df.empty and df['post_date_dt'].notnull().any():
        # 自動抓資料庫裡的最早與最晚日期
        min_date = df['post_date_dt'].min()
        max_date = df['post_date_dt'].max()
        
        # 顯示日曆選擇器
        date_range = st.sidebar.date_input(
            "📅 發文日期範圍",
            value=(min_date, max_date), # 預設全選
            min_value=min_date,
            max_value=max_date
        )
    else:
        date_range = []

    # 4. [原有] 價格區間滑桿
    if not df.empty:
        db_max_price = int(df['price'].max())
        slider_max = min(db_max_price, 100000) 
        price_range = st.sidebar.slider(
            "💰 價格區間", 
            min_value=0, 
            max_value=slider_max, 
            value=(0, slider_max), 
            step=100
        )
    else:
        price_range = (0, 0)

    # === 執行篩選邏輯 ===
    filtered_df = df.copy()
    
    # A. 關鍵字篩選 (標題 或 酒名)
    if keyword:
        mask_keyword = (
            filtered_df['product_name'].str.contains(keyword, case=False) | 
            filtered_df['title'].str.contains(keyword, case=False)
        )
        filtered_df = filtered_df[mask_keyword]
    
    # B. [新增] 賣家篩選
    if author_keyword:
        filtered_df = filtered_df[filtered_df['author'].str.contains(author_keyword, case=False)]

    # C. [新增] 日期篩選
    # 只有當使用者選了完整的「開始」與「結束」日期才執行
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df['post_date_dt'] >= start_date) & 
            (filtered_df['post_date_dt'] <= end_date)
        ]
        
    # D. 價格篩選
    if not df.empty:
        filtered_df = filtered_df[(filtered_df['price'] >= price_range[0]) & (filtered_df['price'] <= price_range[1])]

    # === 顯示關鍵指標 (KPI) ===
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 資料庫總筆數", f"{len(df)} 筆")
    col2.metric("🔍 搜尋結果", f"{len(filtered_df)} 筆")
    
    if not filtered_df.empty:
        avg_price = int(filtered_df['price'].mean())
        col3.metric("💰 平均行情", f"${avg_price:,}")
    else:
        col3.metric("💰 平均行情", "$0")

    # === 顯示主要表格 ===
    # 標題動態顯示目前的篩選狀態
    table_title = "📋 最新報價清單"
    if keyword: table_title += f" | 關鍵字: {keyword}"
    if author_keyword: table_title += f" | 賣家: {author_keyword}"
    
    st.subheader(table_title)

    if not filtered_df.empty:
        st.dataframe(
            filtered_df,
            column_config={
                "post_date": "發文日期",
                "title": "完整貼文標題",
                "product_name": "AI識別酒名",
                "author": "賣家帳號",
                "price": st.column_config.NumberColumn("預估價格", format="$%d"),
                "link": st.column_config.LinkColumn("原始連結", display_text="前往查看")
            },
            # 隱藏輔助用的 datetime 欄位，不讓它顯示在表格上
            column_order=("post_date", "title", "product_name", "author", "price", "link"),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("⚠️ 查無資料！請嘗試放寬篩選條件（例如擴大日期範圍或清空關鍵字）。")

except Exception as e:
    st.error(f"系統錯誤，請確認資料庫狀態。錯誤訊息: {e}")

# --- 頁尾 ---
st.markdown("---")
st.caption("資料來源：P9 品酒網 | 本系統由 Python 自動化爬蟲生成")