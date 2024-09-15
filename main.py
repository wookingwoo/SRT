import os
import random
import requests
from SRT import SRT
from time import sleep
from dotenv import load_dotenv
from datetime import datetime

# .env 파일 로드 및 환경 변수 설정
load_dotenv()

SRT_PHONE_NUMBER = os.getenv("SRT_PHONE_NUMBER")
SRT_PASSWORD = os.getenv("SRT_PASSWORD")
CARD_NUMBER = os.getenv("CARD_NUMBER")
CARD_PASSWORD = os.getenv("CARD_PASSWORD")
CARD_VALIDATION_NUMBER = os.getenv("CARD_VALIDATION_NUMBER")
CARD_EXPIRE_DATE = os.getenv("CARD_EXPIRE_DATE")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

MIN_WAIT = 10
MAX_WAIT = 300
MAX_RETRIES = 1000  # 전체 예약 시도 횟수


def log_with_timestamp(message):
    """현재 시각과 함께 로그 메시지를 출력"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] {message}")


def send_slack_notification(message):
    """슬랙 알림을 보내는 함수"""
    payload = {"text": message}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            log_with_timestamp(f"Slack notification sent: {message}")
        else:
            log_with_timestamp(
                f"Failed to send Slack notification: {response.status_code}"
            )
    except requests.RequestException as e:
        log_with_timestamp(f"Slack notification error: {e}")


def find_and_reserve_train(srt, dep, arr, date, time):
    """기차 찾기 및 예약 시도 함수"""
    try:
        trains = srt.search_train(dep, arr, date, time)
        if trains:
            reservation = srt.reserve(trains[0])
            srt.pay_with_card(
                reservation,
                number=CARD_NUMBER,
                password=CARD_PASSWORD,
                validation_number=CARD_VALIDATION_NUMBER,
                expire_date=CARD_EXPIRE_DATE,
            )
            return True, f"Reservation successful: {reservation}"
        else:
            return False, "No trains available for reservation."
    except Exception as e:
        return False, f"Reservation or payment failed: {e}"


if __name__ == "__main__":
    srt = SRT(SRT_PHONE_NUMBER, SRT_PASSWORD)

    # 예약할 노선 정보 리스트
    routes = [
        {
            "departure_station": "익산",
            "arrival_station": "동탄",
            "travel_date": "20240917",
            "preferred_time": "200000",
        },
        {
            "departure_station": "광주송정",
            "arrival_station": "동탄",
            "travel_date": "20240918",
            "preferred_time": "090000",
        },
        # 필요시 추가 노선을 여기에 작성
    ]

    attempt = 0  # 시도 횟수
    route_index = 0  # 순서대로 노선을 번갈아가면서 시도하기 위한 인덱스

    while attempt < MAX_RETRIES:
        # 현재 시도할 노선 선택 (순서대로 순환)
        current_route = routes[route_index]
        dep = current_route["departure_station"]
        arr = current_route["arrival_station"]
        date = current_route["travel_date"]
        time = current_route["preferred_time"]

        log_with_timestamp(
            f"Attempt {attempt + 1}/{MAX_RETRIES}: Trying route {dep} -> {arr} on {date} at {time}"
        )

        # 기차 찾기 및 예약 시도
        success, message = find_and_reserve_train(srt, dep, arr, date, time)

        log_with_timestamp(message)

        # 예약에 성공하면 성공 알림 전송 후 종료
        if success:
            log_with_timestamp(
                f"Reservation successful on attempt {attempt + 1}. {message}"
            )
            send_slack_notification(
                f":tada: Reservation successful on attempt {attempt + 1}. {message}"
            )
            break

        # 다음 노선으로 순환
        route_index = (route_index + 1) % len(routes)
        attempt += 1

        # 실패 시 대기 후 재시도
        delay = random.uniform(MIN_WAIT, MAX_WAIT)
        log_with_timestamp(f"Waiting for {delay:.2f} seconds before next attempt.")
        sleep(delay)

    # 예약 시도가 최대 횟수에 도달했을 때 실패 알림 전송
    if attempt == MAX_RETRIES:
        log_with_timestamp(
            f"Reached maximum retry attempts. Reservation failed. (MAX_RETRIES: {MAX_RETRIES})"
        )
        send_slack_notification(
            f":man-gesturing-no: Reached maximum retry attempts. Reservation failed. (MAX_RETRIES: {MAX_RETRIES})"
        )
