import os
import random
import requests
from SRT import SRT
from time import sleep
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경변수에서 정보 로드
SRT_PHONE_NUMBER = os.getenv("SRT_PHONE_NUMBER")
SRT_PASSWORD = os.getenv("SRT_PASSWORD")

CARD_NUMBER = os.getenv("CARD_NUMBER")
CARD_PASSWORD = os.getenv("CARD_PASSWORD")
CARD_VALIDATION_NUMBER = os.getenv("CARD_VALIDATION_NUMBER")
CARD_EXPIRE_DATE = os.getenv("CARD_EXPIRE_DATE")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

RETRY_LIMIT = 10  # 재시도 횟수 제한
MIN_WAIT_TIME = 10  # 최소 대기 시간 (초)
MAX_WAIT_TIME = 120  # 최대 대기 시간 (초)


def send_slack_notification(message):
    """슬랙 알림을 보내는 함수"""
    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)

    if response.status_code == 200:
        print("Slack notification sent successfully")
    else:
        print(f"Failed to send Slack notification. Status code: {response.status_code}")


def find_and_reserve_train(srt, dep, arr, date, time):
    for attempt in range(RETRY_LIMIT):
        trains = srt.search_train(dep, arr, date, time)
        if trains:
            message = f"Trains found: {trains}. Attempting reservation."
            print(message)
            send_slack_notification(message)

            # 기차가 있을 경우 예약을 시도
            reservation = srt.reserve(trains[0])
            message = f"Reservation successful: {reservation}"
            print(message)
            send_slack_notification(message)

            srt.pay_with_card(
                reservation,
                number=CARD_NUMBER,
                password=CARD_PASSWORD,
                validation_number=CARD_VALIDATION_NUMBER,
                expire_date=CARD_EXPIRE_DATE,
            )
            return True
        else:
            delay = random.randint(MIN_WAIT_TIME, MAX_WAIT_TIME)
            message = f"No trains found, retrying in {delay} seconds (Attempt {attempt + 1}/{RETRY_LIMIT})"
            print(message)
            send_slack_notification(message)
            sleep(delay)

    message = "Failed to find and reserve a train after maximum retry attempts."
    print(message)
    send_slack_notification(message)
    return False


if __name__ == "__main__":
    print("SRT_PHONE_NUMBER:", SRT_PHONE_NUMBER)

    srt = SRT(SRT_PHONE_NUMBER, SRT_PASSWORD)

    departure_station = "익산"
    arrival_station = "동탄"
    travel_date = "20240917"
    preferred_time = "200000"

    # 기차 찾기 및 예약 시도
    success = find_and_reserve_train(
        srt, departure_station, arrival_station, travel_date, preferred_time
    )

    if success:
        send_slack_notification("Train reservation successful!")
    else:
        send_slack_notification("Train reservation failed.")
