from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Temporary Session State Storage
user_sessions = {}

# Supabase aur WhatsApp credentials (Render me environment variables me set karenge)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "YOUR_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "YOUR_PHONE_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "YOUR_SUPABASE_KEY")

def send_whatsapp_message(to_number, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, json=payload, headers=headers)

@app.route("/", methods=["GET"])
def home():
    return "Balaghat Property Bot is Running!", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == "BALAGHAT_VERIFY_TOKEN":
            return challenge, 200
        return "Forbidden", 403

    data = request.get_json()
    try:
        message_data = data['entry'][0]['changes'][0]['value']['messages'][0]
        sender_phone = message_data['from']
        user_msg = message_data['text']['body'].strip()

        if sender_phone not in user_sessions or user_msg.lower() in ["hi", "reset", "sell"]:
            user_sessions[sender_phone] = {"step": 1, "data": {}}
            send_whatsapp_message(sender_phone, "Namaste! Balaghat Property Hub me swagat hai.\n\nProperty Type batayein:\n1. Residential Plot\n2. House / Villa\n3. Commercial Space")
        
        else:
            session = user_sessions[sender_phone]
            step = session["step"]

            if step == 1:
                session["data"]["property_type"] = user_msg
                session["step"] = 2
                send_whatsapp_message(sender_phone, "Property kis Location/Area me hai? (Jaise: Gondia Road, Circuit House Area, Chitragupt Nagar)")

            elif step == 2:
                session["data"]["location"] = user_msg
                session["step"] = 3
                send_whatsapp_message(sender_phone, "Plot ya House ka Total Size (sq ft) me likhein:")

            elif step == 3:
                session["data"]["size_sqft"] = user_msg
                session["step"] = 4
                send_whatsapp_message(sender_phone, "Aapki Total Expected Price (Lakhs me) kitni hai? (Jaise: 25)")

            elif step == 4:
                session["data"]["price_lakhs"] = user_msg
                session["step"] = 5
                send_whatsapp_message(sender_phone, "Property ki Photo ka Link (URL) bhejiye ya 'Skip' likhein:")

            elif step == 5:
                session["data"]["photo_url"] = user_msg if user_msg.lower() != "skip" else ""
                
                # Supabase Database me data save karne ki request
                db_url = f"{SUPABASE_URL}/rest/v1/properties"
                db_headers = {
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                }
                db_payload = {
                    "phone_number": sender_phone,
                    "property_type": session["data"]["property_type"],
                    "location": session["data"]["location"],
                    "size_sqft": session["data"]["size_sqft"],
                    "price_lakhs": session["data"]["price_lakhs"],
                    "photo_url": session["data"]["photo_url"]
                }
                requests.post(db_url, json=db_payload, headers=db_headers)

                send_whatsapp_message(sender_phone, "✅ Dhanyawad! Aapki property details successfully save ho gayi hain. Jald hi buyer aapse contact karega.")
                del user_sessions[sender_phone]

    except Exception as e:
        pass

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
