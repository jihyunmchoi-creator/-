import streamlit as st
import pandas as pd
import calendar
import random
from datetime import datetime
import io

# 페이지 설정
st.set_page_config(page_title="간호사 스케줄러", layout="wide")

# --- 1. 기본 데이터 및 로직 ---
WEEKS_KR = ["월", "화", "수", "목", "금", "토", "일"]
LEVELS = ["수간호사", "데스크", "상", "중", "하"]

def get_holidays(year):
    hols = [(1, 1), (3, 1), (5, 5), (6, 6), (8, 15), (10, 3), (10, 9), (12, 25)]
    if year == 2026:
        hols += [(2, 16), (2, 17), (2, 18), (5, 24), (9, 24), (9, 25), (9, 26)]
    return hols

# --- 2. 사이드바 설정 ---
st.sidebar.header("⚙️ 근무 설정")
year = st.sidebar.selectbox("연도", [2026, 2027, 2028])
month = st.sidebar.selectbox("월", list(range(1, 13)), index=datetime.now().month - 1)

st.sidebar.subheader("🏥 일일 필요 인원")
col_d, col_e, col_n = st.sidebar.columns(3)
req_d = col_d.number_input("Day", 1, 50, 2)
req_e = col_e.number_input("Eve", 1, 50, 2)
req_n = col_n.number_input("Night", 1, 50, 2)

num_nurses = st.sidebar.number_input("총 간호사 수", 1, 100, 8)

total_req = req_d + req_e + req_n
util_rate = (total_req / num_nurses) * 100
st.sidebar.metric("인원 가동률", f"{util_rate:.1f}%")

# --- 3. 메인 화면 ---
st.title("📅 간호사 3교대 스케줄러")
st.write(f"### {year}년 {month}월 근무 생성")

nurses_data = []
with st.expander("👤 간호사 명단 및 숙련도 설정", expanded=True):
    for i in range(num_nurses):
        c1, c2, c3 = st.columns([2, 2, 3])
        name = c1.text_input(f"성함", f"간호사 {i+1}", key=f"nm_{i}")
        level = c2.selectbox(f"숙련도", LEVELS, index=2, key=f"lv_{i}")
        exclude = c3.multiselect(f"제외 듀티", ["D", "E", "N"], key=f"ex_{i}")
        nurses_data.append({"name": name, "level": level, "ex": exclude})

# --- 4. 근무 생성 엔진 ---
if st.button("🚀 근무표 생성하기", use_container_width=True):
    _, days = calendar.monthrange(year, month)
    res = {n['name']: ["OFF"] * days for n in nurses_data}
    last = {n['name']: "OFF" for n in nurses_data}
    consec = {n['name']: 0 for n in nurses_data}
    off_c = {n['name']: 0 for n in nurses_data}

    for d in range(days):
        wd = calendar.weekday(year, month, d+1)
        avail = [n for n in nurses_data]
        cur_req = {"D": req_d, "E": req_e, "N": req_n}

        # 수간호사 규칙
        for n in avail[:]:
            if n['level'] == "수간호사":
                nm = n['name']
                if wd >= 5:
                    res[nm][d], last[nm], consec[nm] = "OFF", "OFF", 0
                    off_c[nm] += 1
                else:
                    res[nm][d], last[nm], consec[nm] = "D", "D", consec[nm]+1
                    if cur_req["D"] > 0: cur_req["D"] -= 1
                avail.remove(n)

        random.shuffle(avail)
        avail.sort(key=lambda x: off_c[x['name']])

        for duty in ["N", "E", "D"]:
            assigned = 0
            for n in [x for x in avail if x['level'] == "데스크"]:
                nm = n['name']
                if (duty=="D" and last[nm]=="N") or consec[nm]>=5 or duty in n['ex']: continue
                res[nm][d], last[nm], consec[nm] = duty, duty, consec[nm]+1
                avail.remove(n); assigned += 1; break
            
            for n in avail[:]:
                if assigned >= cur_req[duty]: break
                nm = n['name']
                if (duty=="D" and last[nm]=="N") or consec[nm]>=5 or duty in n['ex']: continue
                res[nm][d], last[nm], consec[nm] = duty, duty, consec[nm]+1
                avail.remove(n); assigned += 1

        for n in avail:
            nm = n['name']
            res[nm][d], last[nm], consec[nm] = "OFF", "OFF", 0
            off_c[nm] += 1

    st.divider()
    df_res = pd.DataFrame(res).T
    df_res.columns = [f"{i+1}일" for i in range(days)]
    
    def style_shifts(val):
        color = 'black'
        bg = 'white'
        if val == 'D': bg = '#E3F2FD'
        elif val == 'E': bg = '#F3E5F5'
        elif val == 'N': bg = '#FFEBEE'
        elif val == 'OFF': color = 'red'
        return f'background-color: {bg}; color: {color}; font-weight: bold'

    st.write("### 📊 생성된 전체 근무표")
    # 최신 버전에 맞게 applymap을 map으로 수정
    st.dataframe(df_res.style.map(style_shifts), use_container_width=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_res.to_excel(writer, sheet_name='근무표')
    st.download_button(label="📥 엑셀 다운로드", data=output.getvalue(), 
                       file_name=f"Schedule_{year}_{month}.xlsx", 
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True)
