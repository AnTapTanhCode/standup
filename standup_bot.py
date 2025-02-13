import os
import threading
import time
import schedule
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Initialize Slack Bolt App
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

STANDUP_QUESTIONS = [
    "1️⃣ Hôm qua bạn đã làm gì?",
    "2️⃣ Hôm nay bạn dự định làm gì?",
    "3️⃣ Có gặp khó khăn gì không?"
]

CHANNEL_ID = "C08C95WE2VD"  # Thay bằng ID channel chung
user_responses = {}  # Dictionary lưu câu trả lời của từng user

def ask_next_question(user_id, step):
    """Gửi câu hỏi tiếp theo cho user"""
    if step < len(STANDUP_QUESTIONS):
        app.client.chat_postMessage(channel=user_id, text=STANDUP_QUESTIONS[step])
        user_responses[user_id]["step"] = step
    else:
        # Nếu user trả lời hết, gửi tổng hợp vào channel
        send_summary_to_channel(user_id)

def send_summary_to_channel(user_id):
    """Gửi tổng hợp câu trả lời vào channel"""
    channel_id = CHANNEL_ID
    responses = user_responses.get(user_id, {}).get("answers", [])

    if responses:
        text = f"📢 *Standup report của <@{user_id}>:*\n"
        for i, answer in enumerate(responses):
            text += f"\n*{STANDUP_QUESTIONS[i]}*\n👉 {answer}\n"

        app.client.chat_postMessage(channel=channel_id, text=text)
    
    # Xóa dữ liệu sau khi gửi
    del user_responses[user_id]

def get_channel_members(channel_id):
    """Lấy danh sách các thành viên trong channel"""
    try:
        response = app.client.conversations_members(channel=channel_id)
        members = response.get("members", [])
        return [m for m in members if m != "USLACKBOT"]  # Loại bot ra
    except Exception as e:
        print(f"⚠️ Không thể lấy danh sách thành viên: {e}")
        return []

def send_dm(user_id):
    """Gửi tin nhắn riêng đến user để thu thập câu trả lời"""
    try:
        app.client.chat_postMessage(
            channel=user_id,
            text="🌅 Chào buổi sáng! Đã đến giờ Standup, vui lòng cập nhật công việc của bạn hôm nay.",
        )
        # Khởi tạo trạng thái user
        user_responses[user_id] = {"step": 0, "answers": []}
        
        # Hỏi câu đầu tiên
        ask_next_question(user_id, 0)
    except Exception as e:
        print(f"⚠️ Không thể gửi tin nhắn DM cho {user_id}: {e}")

@app.event("message")
def handle_message(event):
    """Nhận câu trả lời từ user và gửi ngay lên channel chung"""
    user_id = event["user"]
    text = event["text"]

    if user_id in user_responses:
        step = user_responses[user_id]["step"]
        user_responses[user_id]["answers"].append(text)

        # Hỏi câu tiếp theo hoặc gửi tổng hợp
        ask_next_question(user_id, step + 1)

def schedule_standups():
    """Lên lịch gửi tin nhắn DM mỗi ngày"""
    schedule.every().monday.at("08:15").do(lambda: [send_dm(user) for user in get_channel_members(CHANNEL_ID)])
    schedule.every().tuesday.at("08:15").do(lambda: [send_dm(user) for user in get_channel_members(CHANNEL_ID)])
    schedule.every().thursday.at("08:15").do(lambda: [send_dm(user) for user in get_channel_members(CHANNEL_ID)])
    schedule.every().wednesday.at("08:15").do(lambda: [send_dm(user) for user in get_channel_members(CHANNEL_ID)])
    schedule.every().friday.at("08:15").do(lambda: [send_dm(user) for user in get_channel_members(CHANNEL_ID)])
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Kiểm tra lịch mỗi phút

if __name__ == "__main__":
    # Chạy schedule trong một luồng riêng để không chặn bot
    scheduler_thread = threading.Thread(target=schedule_standups, daemon=True)
    scheduler_thread.start()
    
    # Khởi động Slack Bot (Socket Mode)
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()
