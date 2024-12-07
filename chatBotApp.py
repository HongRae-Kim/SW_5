import streamlit as st
import ollama
import re
import requests
import random
from streamlit_option_menu import option_menu
from urllib.parse import quote
from datetime import datetime, timedelta

# 모델 이름, Ollama 로컬 서버 실행되고 있어야 함
model_name = "hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M"

# 공공데이터포털 API
PUBLIC_DATA_SERVICE_KEY = "Your Data Service Key"

# Kakao 지도 API를 사용하여 HTML iframe 생성
KAKAO_API_KEY = "your_kakao_api_key"

# OpenWeather API Key
OPENWEATHER_API_KEY = "Your Openweather API Key"

# HTML을 렌더링하기 위한 기본 템플릿
def generate_map_iframe_html(query, width, height):
    encoded_query = quote(query)
    return f"""
    <iframe
        width="{width}"
        height="{height}"
        src="https://map.kakao.com/link/search/{encoded_query}"
        frameborder="0"
        allowfullscreen>
    </iframe>
    """

# 날씨 예보를 가져오는 함수
def get_weather_forecast(city):
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=kr"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        forecast_data = []

        current_time = datetime.now()

        # 시간 구하기
        for delta in [0, 12]:  # 0은 현재시간, 6은 +6시간, 12는 +12시간
            forecast_time = current_time + timedelta(hours=delta)
            forecast_data.append({
                "time": forecast_time.strftime("%H시 %M분"),  
                "temp": data['list'][delta]['main']['temp'],
                "description": data['list'][delta]['weather'][0]['description'],
                "weekday": forecast_time.strftime("%A"),  
                "temp_min": data['list'][delta]['main']['temp_min'],  
                "temp_max": data['list'][delta]['main']['temp_max'],  
            })

        # 각 요일별로 최저 및 최고 기온을 구하기
        daily_min_max = {}
        for forecast in data['list']:
            date = datetime.fromtimestamp(forecast['dt']).strftime('%Y-%m-%d')
            temp_min = forecast['main']['temp_min']
            temp_max = forecast['main']['temp_max']
            if date not in daily_min_max:
                daily_min_max[date] = {'temp_min': temp_min, 'temp_max': temp_max}
            else:
                daily_min_max[date]['temp_min'] = min(daily_min_max[date]['temp_min'], temp_min)
                daily_min_max[date]['temp_max'] = max(daily_min_max[date]['temp_max'], temp_max)

        return forecast_data, daily_min_max
    else:
        return None, None

# 공공데이터포털 API 호출하여 맛집 정보를 가져오는 함수
def get_restaurant_info():
    base_url = "BASE_URL"
    endpoint = "ENDPOINT"
    url = f"{base_url}{endpoint}"

    # 파라미터 설정
    params = {
        "page": 1,
        "perPage": 10,
        "returnType": "JSON",
        "serviceKey": PUBLIC_DATA_SERVICE_KEY 
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        response_data = response.json()
        restaurant_list = []

        for item in response_data.get("data", []):
            restaurant_info = {
                "업소명": item.get("업소명"),
                "소재지": item.get("소재지(도로명)"),
                "음식의유형": item.get("음식의유형"),
                "추천메뉴": item.get("주된음식")
            }
            restaurant_list.append(restaurant_info)

        return random.sample(restaurant_list, min(4, len(restaurant_list)))
    
    else:
        st.error(f"API 요청에 실패했습니다: 상태 코드 {response.status_code}")
        return None
    
# 공공데이터포털 API 호출하여 숙박업소 정보를 가져오는 함수
def get_accommodation_info():
    base_url = "BASE_URL"
    endpoint = "ENDPOINT"
    url = f"{base_url}{endpoint}"

    params = {
        "page": 1,
        "perPage": 10,
        "returnType": "JSON",
        "serviceKey": PUBLIC_DATA_SERVICE_KEY  
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        response_data = response.json()
        accommodation_list = []

        for item in response_data.get("data", []):
            accommodation_info = {
                "업소명": item.get("업소명"),
                "소재지": item.get("소재지도로명주소"),
                "업태": item.get("업태"),
            }
            accommodation_list.append(accommodation_info)

        return random.sample(accommodation_list, min(4, len(accommodation_list)))
    
    else:
        st.error(f"API 요청에 실패했습니다: 상태 코드 {response.status_code}")
        return None

# 공공데이터포털 API 호출하여 관광지 정보를 가져오는 함수
def get_thematic_tour_info():
    base_url = "BASE_URL"
    endpoint = "ENDPOINT"
    url = f"{base_url}{endpoint}"

    params = {
        "pageNo": 1,
        "perPage": 10,
        "returnType": "JSON",
        "serviceKey": PUBLIC_DATA_SERVICE_KEY 
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        if response.status_code == 200:
            response_data = response.json()
            tour_list = []

            for item in response_data.get("data", []):
                tour_info = {
                    "테마": item.get("테마"),
                    "요약": item.get("요약"),
                    "코스정보": item.get("코스정보"),
                }
                tour_list.append(tour_info)

            selected_tours = random.sample(tour_list, min(1, len(tour_list)))

            return selected_tours
        
        else:
            print(f"API 요청에 실패했습니다: 상태 코드 {response.status_code}")
            return None 
        
    except requests.exceptions.RequestsDependencyWarning as err:
        print(f"API 요청 오류 발생: {err}") 
        return None

def call_model(prompt):
    try:
        # Ollama 모델 호출 
        response_stream = ollama.chat(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            stream=True  # 스트리밍 활성화
        )

        # 스트리밍된 응답을 받아서 실시간으로 업데이트
        full_response = ""
        response_placeholder = st.empty()  # 이 부분에서 Streamlit에 출력할 빈 공간을 준비
        for chunk in response_stream:
            if 'message' in chunk:
                full_response += chunk['message']['content']
                response_placeholder.text(full_response)  # 실시간 업데이트
        st.success("모델 응답 완료")
    except Exception as e:
        st.error(f"모델 호출 오류가 발생했습니다: {e}")       


def generate_prompt(restaurants=None, accommodations=None, tourist=None):
    api_result = ""

    # 맛집 정보가 있는 경우 프롬프트에 맛집 정보만 포함
    if restaurants:
        api_result += "\n[맛집 정보]\n"
        for res in restaurants:
            api_result += f"업소명: {res['업소명']}, 위치: {res['소재지']}, 음식 유형: {res['음식의유형']}, 추천 메뉴: {res['추천메뉴']}\n"
        
        prompt = f"""
        다음은 춘천의 인기 맛집에 대한 정보입니다. {api_result}
        위 내용을 사용하여 당신은 춘천 맛집 가이드에 대한 정보를 사용자에게 소개해야 합니다.

        예시:
        1. 맛집 이름: 방문할 맛집을 기재합니다.
        2. 위치: 장소를 방문할 적절한 시간을 제시합니다.
        3. 음식 유형: 해당 음식의 종류를 간단하게 설명해주세요.
        4. 추천 메뉴: 추천하는 메뉴를 설명해주세요.

        춘천의 유명한 맛집들을 위치와 추천 메뉴를 고려하여 추천해주세요.
        """
        return prompt

    # 숙박업소 정보가 있는 경우 프롬프트에 숙박업소 정보만 포함
    elif accommodations:
        api_result += "\n[숙박업소 정보]\n"
        for acc in accommodations:
            api_result += f"업소명: {acc['업소명']}, 위치: {acc['소재지']}, 업태: {acc['업태']}\n"
        
        prompt = f"""
        다음은 춘천의 인기 숙박업소에 대한 정보입니다. {api_result}
        위 내용을 사용하여 당신은 춘천 여행 가이드에서 숙박에 대한 정보를 사용자에게 소개해야 합니다.

        예시:
        1. 숙박업소 이름: 숙박할 수 있는 업소명을 기재합니다.
        2. 위치: 숙소 위치를 설명합니다.
        3. 분류: 제공되는 숙박업소가 관광호텔, 여관업, 여인숙업, 일반호텔, 숙박업 기타 등 어디에 해당되는지 기재합니다.

        춘천의 숙박업소들을 추천해 주세요.
        """
        return prompt

    elif tourist:
        api_result += "\n[관광지 정보]\n"
        for tour in tourist:
            api_result += f"테마 {tour['테마']}, 요약: {tour['요약']}, 코스정보: {tour['코스정보']}\n"
            
        prompt = f"""
        다음은 춘천의 관광지에 대한 정보입니다. {api_result}
        위 내용을 사용하여 당신은 춘천 관광 가이드에 대한 정보를 사용자에게 소개해야 합니다.

        예시:
        1. 코스정보: 간단하게 정보를 소개합니다.
        2. 소개: 제공되는 코스정보에 대해서 소개합니다.
        3. 추천: 누구와 함께 즐겨야하는지에 대한 정보를 기재합니다.

        춘천의 유명한 관광지를 추천해 주세요.
        """
        return prompt

    else:
        return "사용 가능한 정보가 없습니다. 적절한 데이터를 제공해주세요."

# Streamlit 앱 구현
def main():
    # 화면 너비 설정
    st.set_page_config(layout="wide")
    st.markdown(
    """
    <style>
        /* Sidebar의 색상 및 크기 조정 */
        [data-testid="stSidebar"] {
            background-color: #2C3E50;
            min-width: 200px;
            max-width: 300px;  /* Adjust the maximum width */
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #FFFFFF; /* 헤더 텍스트 색상 (흰색) */
        }
        .stApp {
            background-color: #FFFFF0; /* 배경 색상 */
        }
        
    </style>
    """,
    unsafe_allow_html=True,
)

    # 앱 제목 및 설명
    st.title("🗺️ 여행 가이드 챗봇")
    st.write("검색하고자 하는 장소를 입력하세요. 현재는 **춘천 지역**만 지원합니다")

    # 기본 지도 HTML
    map_html = None

    # 사이드바
    with st.sidebar:
        st.header("🔍 빠른 탐색")
        menu = option_menu(
            menu_title="Menu",  # Title for the menu
            options=["춘천 식당", "춘천 숙소", "춘천 관광지"],  # Menu options
            icons=["apple", "building", "backpack"],            # Icons for the options
            default_index=0,    # Default selected option
            styles={            # Custom styles for the menu
                "container": {"padding": "5!important", "background-color": "#AAAAAA"},
                "icon": {"color": "white", "font-size": "25px"},
                "nav-link": {
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "0px",
                    "--hover-color": "#CDCDFD",
                },
                "nav-link-selected": {
                    "background-color": "#2C3E50",
                    },
            },
        )

        # Date input for selecting forecast date
        my_date = st.date_input("원하는 날짜를 선택하세요", datetime.now())

    # Map query based on user input
    query = menu
    map_html = generate_map_iframe_html(query, "100%", "600")

    # Layout: Columns for map and chatBot
    col1, col2 = st.columns([6, 4])

    # 추천 일정 출력
    with col2:
        st.subheader("📅 추천 일정")
        user_input = st.text_input("검색할 장소를 입력하세요:", placeholder="예: 춘천 식당, 춘천 관광지 ...")

        # 사용자 입력에 따른 추천 일정 생성 
        response_placeholder = st.empty()

        # 정규식을 사용하여 사용자 입력 패턴 매칭 
        try:
            #  "식당" 또는 "맛집"과 관련된 검색을 했을 때
            if re.search(r"(춘천).*?(식당|맛집)", user_input, re.IGNORECASE) or "식당" in menu:
                # 맛집 정보 가져오기
                restaurants = get_restaurant_info()
                if restaurants:
                    prompt = generate_prompt(restaurants=restaurants)
                    call_model(prompt)
                else:
                    st.warning("맛집 정보를 가져올 수 없습니다.")

            # "숙소"와 관련된 검색을 했을 때
            elif re.search(r"(춘천).*?(숙소)", user_input, re.IGNORECASE) or "숙소" in menu:
                # 숙소 정보 가져오기
                accommodations = get_accommodation_info()
                if accommodations:
                    prompt = generate_prompt(accommodations=accommodations)
                    call_model(prompt)
                else:
                    st.warning("숙소 정보를 가져올 수 없습니다.")

            # "관광지"와 관련된 검색을 했을 때
            elif re.search(r"(춘천).*?(관광지)", user_input, re.IGNORECASE) or "관광지" in menu:
                tourist = get_thematic_tour_info()
                if tourist:
                    prompt = generate_prompt(tourist=tourist)
                    call_model(prompt)
                else:
                    st.warning("관광지 정보를 가져올 수 없습니다.")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

    # 지도 및 날씨 정보 출력 (col1)
    with col1:
        if map_html:
            st.components.v1.html(map_html, height=600)
        else:
            st.info("지도가 여기에 표시됩니다.")

        # 날씨 정보 출력
        forecast_data, daily_min_max = get_weather_forecast("Chuncheon")
        if forecast_data:
            st.subheader("☀️ 춘천 날씨 예보")
            for i, forecast in enumerate(forecast_data):
                # 두 컬럼으로 나누기
                left_col, right_col = st.columns([1, 1])  # 두 컬럼으로 나눔
                with left_col: # 현재 시간을 기준으로 시간, 온도, 날씨 출력(left_col)
                    st.write(f"🕓시간: {forecast['time']}")
                    st.write(f"🌡️온도: {forecast['temp']}°C")
                    st.write(f"☁️날씨: {forecast['description']}")
                with right_col: # 요일과 그 날 최저, 최고 기온 출력(right_col)
                    weekday_display = (my_date + timedelta(days=i)).strftime("%A")
                    st.write(f"📅요일: {weekday_display}")
                    date_key = (my_date + timedelta(days=i)).strftime('%Y-%m-%d')
                    if date_key in daily_min_max:
                        st.write(f"🌡️최저 기온: {daily_min_max[date_key]['temp_min']}°C")
                        st.write(f"🌡️최고 기온: {daily_min_max[date_key]['temp_max']}°C")
                st.write("------")
        else:
            st.error("날씨 정보를 가져올 수 없습니다.")

# 메인 실행
if __name__ == "__main__":
    main()
