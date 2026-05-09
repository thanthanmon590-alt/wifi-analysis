import streamlit as st
import pandas as pd
import sqlite3
import os

st.set_page_config(page_title="서울시 공공와이파이 분석 대시보드", layout="wide")

st.title("서울시 공공와이파이 설치 현황과 지역별 접근성 분석 대시보드")
st.write("서울시 공공와이파이 서비스 위치 정보를 활용하여 지역별 설치 현황과 설치 유형을 분석한 대시보드입니다.")

csv_path = "wifi.csv"
db_path = "wifi.db"

if not os.path.exists(csv_path):
    st.error("wifi.csv 파일을 찾을 수 없습니다. 같은 폴더에 wifi.csv 파일이 있는지 확인해 주세요.")
    st.stop()

# CSV 파일 읽기: 한글 깨짐 방지를 위해 여러 인코딩을 시도
def read_csv_safely(path):
    encodings = ["cp949", "euc-kr", "utf-8-sig", "utf-8"]
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    st.error("CSV 파일을 읽을 수 없습니다. 파일 형식이나 인코딩을 확인해 주세요.")
    st.stop()

df = read_csv_safely(csv_path)

# 컬럼명 앞뒤 공백 제거
df.columns = df.columns.str.strip()

# 필요한 컬럼이 있는지 확인
st.subheader("데이터 미리보기")
st.dataframe(df.head())

# SQLite DB 만들기
conn = sqlite3.connect(db_path)

# 1번 테이블: 전체 와이파이 정보
df.to_sql("wifi_info", conn, if_exists="replace", index=False)

# 컬럼 이름 자동 확인
columns = df.columns.tolist()

# 자치구 컬럼 찾기
district_col = None
for col in columns:
    if "자치구" in col:
        district_col = col
        break

# 설치유형 컬럼 찾기
type_col = None
for col in columns:
    if col.strip() == "설치유형":
        type_col = col
        break

# 설치년도 컬럼 찾기
year_col = None
for col in columns:
    if "설치년도" in col or "설치연도" in col:
        year_col = col
        break

if district_col is None:
    st.error("자치구 컬럼을 찾을 수 없습니다. CSV 컬럼명을 확인해 주세요.")
    st.stop()

if type_col is None:
    st.warning("설치유형 컬럼을 찾지 못했습니다. 설치유형 분석은 제한될 수 있습니다.")

if year_col is None:
    st.warning("설치년도 컬럼을 찾지 못했습니다. 설치년도 분석은 제한될 수 있습니다.")

# 2번 테이블: 자치구별 설치 수
district_info = df.groupby(district_col).size().reset_index(name="설치수")
district_info.columns = ["자치구", "설치수"]
district_info.to_sql("district_info", conn, if_exists="replace", index=False)

# 3번 테이블: 설치유형별 설치 수
if type_col is not None:
    type_info = df.groupby(type_col).size().reset_index(name="설치수")
    type_info.columns = ["설치유형", "설치수"]
    type_info.to_sql("type_info", conn, if_exists="replace", index=False)

# SQL 실행 함수
def run_sql(query):
    return pd.read_sql(query, conn)

st.divider()

# 차트 1: 자치구별 설치 수
st.header("1. 자치구별 공공와이파이 설치 수")

sql1 = """
SELECT 자치구, 설치수
FROM district_info
ORDER BY 설치수 DESC
"""

chart1 = run_sql(sql1)

col1, col2 = st.columns([2, 1])

with col1:
    st.bar_chart(chart1.set_index("자치구"))

with col2:
    st.write("사용된 SQL")
    st.code(sql1, language="sql")
    st.info("""
    자치구별 설치 수를 비교하면 공공와이파이가 어느 지역에 많이 설치되어 있는지 확인할 수 있다.
    설치 수가 적은 자치구는 상대적으로 공공와이파이 접근성이 낮을 가능성이 있다.
    """)

st.divider()

# 차트 2: 설치유형별 분포
st.header("2. 설치유형별 공공와이파이 분포")

if type_col is not None:
    sql2 = """
    SELECT 설치유형, 설치수
    FROM type_info
    WHERE 설치유형 IS NOT NULL
    ORDER BY 설치수 DESC
    """

    chart2 = run_sql(sql2)

    col3, col4 = st.columns([2, 1])

    with col3:
        st.bar_chart(chart2.set_index("설치유형"))

    with col4:
        st.write("사용된 SQL")
        st.code(sql2, language="sql")
        st.info("""
        설치유형별 분포를 보면 공공와이파이가 어떤 장소에 주로 설치되어 있는지 알 수 있다.
        시민들이 자주 이용하는 공공장소나 유동인구가 많은 장소에 설치가 집중될 가능성이 높다.
        """)
else:
    st.warning("설치유형 컬럼이 없어 이 차트는 표시할 수 없습니다.")

st.divider()

# 차트 3: 설치년도별 설치 추이
st.header("3. 설치년도별 공공와이파이 설치 추이")

if year_col is not None:
    df_year = df.copy()
    df_year[year_col] = pd.to_numeric(df_year[year_col], errors="coerce")
    df_year = df_year.dropna(subset=[year_col])
    df_year[year_col] = df_year[year_col].astype(int)

    df_year.to_sql("year_info", conn, if_exists="replace", index=False)

    sql3 = f"""
    SELECT {year_col} AS 설치년도, COUNT(*) AS 설치수
    FROM year_info
    GROUP BY {year_col}
    ORDER BY {year_col}
    """

    chart3 = run_sql(sql3)

    col5, col6 = st.columns([2, 1])

    with col5:
        st.line_chart(chart3.set_index("설치년도"))

    with col6:
        st.write("사용된 SQL")
        st.code(sql3, language="sql")
        st.info("""
        설치년도별 추이를 보면 공공와이파이 설치가 어느 시기에 증가했는지 확인할 수 있다.
        특정 연도에 설치 수가 크게 증가했다면 공공 인터넷 서비스 확대 정책과 관련이 있을 수 있다.
        """)
else:
    st.warning("설치년도 컬럼이 없어 이 차트는 표시할 수 없습니다.")

conn.close()