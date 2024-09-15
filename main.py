import os
import random
import requests
from SRT import SRT
from time import sleep
from dotenv import load_dotenv
from datetime import datetime  # 현재 시각 추가를 위한 모듈

# .env 파일 로드 및 환경 변수 설정
load_dotenv()

SRT_PHONE_NUMBER = os.getenv("SRT_PHONE_NUMBER")
SRT_PASSWORD = os.getenv("SRT_PASSWORD")
CARD_NUMBER = os.getenv("CARD_NUMBER")
CARD_PASSWORD = os.getenv("CARD_PASSWORD")
CARD_VALIDATION_NUMBER = os.getenv("CARD_VALIDATION_NUMBER")
CARD_EXPIRE_DATE = os.getenv("CARD_EXPIRE_DATE")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


def log_with_timestamp(message):
    """현재 시각과 함께 로그 메시지를 출력하는 함수"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] {message}")


def send_slack_notification(message):
    """슬랙 알림을 보내는 함수"""
    payload = {"text": message}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            log_with_timestamp(f"Slack notification sent: {message}")
            return True
        else:
            log_with_timestamp(
                f"Failed to send Slack notification: {response.status_code}"
            )
    except requests.RequestException as e:
        log_with_timestamp(f"Slack notification error: {e}")
    return False


def find_and_reserve_train(
    srt, dep, arr, date, time, retry_limit=3, min_wait=10, max_wait=120
):
    """기차 찾기 및 예약 시도 함수"""
    for attempt in range(1, retry_limit + 1):
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
        except Exception as e:
            return False, f"Reservation or payment failed: {e}"

        # 검색 결과 없으면 대기 후 재시도
        delay = random.uniform(min_wait, max_wait)
        log_with_timestamp(
            f"No trains found, retrying in {delay:.2f} seconds (Attempt {attempt}/{retry_limit})"
        )
        sleep(delay)

    return (
        False,
        ":man-gesturing-no: Failed to find and reserve a train after maximum retry attempts.",
    )


if __name__ == "__main__":
    srt = SRT(SRT_PHONE_NUMBER, SRT_PASSWORD)

    departure_station = "익산"
    arrival_station = "동탄"
    travel_date = "20240917"
    preferred_time = "200000"

    # 기차 찾기 및 예약 시도
    success, message = find_and_reserve_train(
        srt, departure_station, arrival_station, travel_date, preferred_time
    )

    log_with_timestamp(message)
    send_slack_notification(message)
