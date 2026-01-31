import os
import logging
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION (use environment variables) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set. Set it to your Gemini/GenAI API key.")

# Configure client (use genai.configure or Client depending on SDK)
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception:
    # Some genai versions require creating a Client instance instead
    client = genai.Client(api_key=GEMINI_API_KEY)

# instantiate the model (adjust the model name if needed)
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception:
    model = None

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


def generate_response_from_model(prompt):
    """Try several possible SDK call patterns to get response text."""
    if model is None:
        raise RuntimeError("Model is not initialized for the installed genai SDK")

    # Try known method names in order
    attempts = [
        ("generate_content", lambda p: model.generate_content(p)),
        ("generate", lambda p: model.generate(p)),
        ("predict", lambda p: model.predict(p)),
        ("__call__", lambda p: model(p)),
    ]

    last_exc = None
    for name, fn in attempts:
        try:
            resp = fn(prompt)
            # Common places to find text
            if isinstance(resp, str):
                return resp
            if hasattr(resp, "text") and resp.text:
                return resp.text
            if hasattr(resp, "output") and resp.output:
                return getattr(resp, "output")
            # Some SDKs return structured JSON in .result or .content
            if hasattr(resp, "result"):
                res = getattr(resp, "result")
                if isinstance(res, str):
                    return res
                if isinstance(res, dict):
                    # try common keys
                    for k in ("content", "text", "output"):
                        if k in res and res[k]:
                            return res[k]
            # Fallback to string conversion
            return str(resp)
        except AttributeError as ae:
            last_exc = ae
            continue
        except Exception as e:
            last_exc = e
            # If it's a runtime error from the API, raise so caller can handle/log
            logger.debug("Attempt %s failed: %s", name, e)
            continue

    # If all attempts failed, raise the last exception
    if last_exc:
        raise last_exc
    raise RuntimeError("Failed to generate response from model")


@app.route("/bot", methods=['POST'])
def bot():
    global current_persona

    # 1. Get User Message
    incoming_msg = request.values.get('Body', '').strip()

    if not incoming_msg:
        return send_reply("I didn't get any message. Send some text and I'll reply.")

    # 2. Check for switching command
    if incoming_msg.lower().startswith("!switch"):
        parts = incoming_msg.split()
        if len(parts) > 1 and parts[1] in AGENTS:
            current_persona = parts[1]
            # Twilio will send literal characters; avoid Markdown
            return send_reply(f"✅ Switched to {current_persona.upper()} mode.")
        else:
            return send_reply(f"❌ Unknown agent. Options: {', '.join(AGENTS.keys())}")

    # 3. Ask Gemini / GenAI
    try:
        system_instruction = AGENTS.get(current_persona, AGENTS["default"])
        prompt = f"System: {system_instruction}\nUser: {incoming_msg}"

        resp_text = generate_response_from_model(prompt)
        return send_reply(resp_text)
    except Exception as e:
        logger.exception("Error while generating response")
        return send_reply("My brain is tired. Try again later.")


def send_reply(msg):
    resp = MessagingResponse()
    resp.message(msg)
    return str(resp)


if __name__ == "__main__":
    # Use host='0.0.0.0' if you want external access (e.g., via ngrok)
    app.run(host="127.0.0.1", port=3000)\n