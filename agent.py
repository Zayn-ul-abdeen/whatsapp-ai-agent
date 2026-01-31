import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
# --- CONFIGURATION (Fill these in!) ---
# In Glitch, it is safer to use .env file, but for testing, you can paste keys here
# WARNING: Don't share this link with others if you paste keys directly.
client = genai.Client(api_key="AIzaSyAKI24H7rbNSABDtkavDKlPhLu7yJ-qMfQ")

# Setup Brain
genai.configure(api_key=Gemini_API_Key)
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask(__name__)

# --- THE 5 AGENTS ---
AGENTS = {
    "default": "You are a helpful assistant. Keep answers short.",
    "business": "You are a ruthless business executive. Focus on money, ROI, and efficiency. Be professional but aggressive.",
    "friend": "You are a best friend. Use slang, emojis (🔥, 😂), and be super supportive. Call the user 'bro'.",
    "coach": "You are a tough gym coach. Yell at the user to work harder. Use caps lock often.",
    "roast": "You are a sarcastic comedian. You answer the question but insult the user slightly while doing it."
}

# Variable to track who is talking
current_persona = "default"

@app.route("/bot", methods=['POST'])
def bot():
    global current_persona
    
    # 1. Get User Message
    incoming_msg = request.values.get('Body', '').strip()
    
    # 2. Check for switching command
    if incoming_msg.lower().startswith("!switch"):
        parts = incoming_msg.split()
        if len(parts) > 1 and parts[1] in AGENTS:
            current_persona = parts[1]
            return send_reply(f"✅ Switched to **{current_persona.upper()}** mode.")
        else:
            return send_reply(f"❌ Unknown agent. Options: {', '.join(AGENTS.keys())}")

    # 3. Ask Gemini
    try:
        system_instruction = AGENTS[current_persona]
        prompt = f"System: {system_instruction}\nUser: {incoming_msg}"
        
        response = model.generate_content(prompt)
        return send_reply(response.text)
    except Exception as e:
        return send_reply("My brain is tired. Try again later.")

def send_reply(msg):
    resp = MessagingResponse()
    resp.message(msg)
    return str(resp)

if __name__ == "__main__":
    app.run(port=3000)
