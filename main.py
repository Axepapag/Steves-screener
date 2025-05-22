from flask import Flask, request, Response, jsonify, render_template_string
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
import os

app = Flask(__name__)

# Store latest call data
latest_call = {
    "from": None,
    "speech": None,
    "status": "waiting",  # waiting / answered / rejected
}


@app.route("/voice", methods=['POST'])
def voice():
    from_number = request.form.get('From')
    caller_name = request.form.get('CallerName', 'Unknown')

    print(f"Incoming call from: {from_number} ({caller_name})")

    if from_number.startswith('+100') or "VOIP" in caller_name.upper():
        print("Rejected likely spam or VOIP caller.")
        response = VoiceResponse()
        response.reject()
        return Response(str(response), mimetype='text/xml')

    # Ask the caller to speak
    response = VoiceResponse()
    gather = Gather(input="speech", action="/screen", method="POST", timeout=5)
    gather.say(
        "Hi. Steve is using call screening. Please state your name and why you are calling after the tone."
    )
    response.append(gather)
    response.say("No response received. Goodbye.")
    response.hangup()
    return Response(str(response), mimetype='text/xml')


@app.route("/screen", methods=['POST'])
def screen():
    speech_result = request.form.get('SpeechResult', 'No speech detected')
    from_number = request.form.get('From')

    print(f"Caller said: {speech_result}")

    # Save to global state
    latest_call["from"] = from_number
    latest_call["speech"] = speech_result
    latest_call["status"] = "waiting"

    response = VoiceResponse()
    response.say("Thank you. Please hold.")
    response.pause(length=10)
    return Response(str(response), mimetype='text/xml')


@app.route("/connect", methods=['POST'])
def connect_call():
    latest_call["status"] = "answered"
    response = VoiceResponse()
    dial = Dial(caller_id=os.environ.get("TWILIO_PHONE_NUMBER"))
    dial.number(os.environ.get("STEVE_PHONE_NUMBER"))
    response.append(dial)
    return Response(str(response), mimetype='text/xml')


@app.route("/reject", methods=['POST'])
def reject_call():
    latest_call["status"] = "rejected"
    response = VoiceResponse()
    response.say("Steve is not available at this time. Goodbye.")
    response.hangup()
    return Response(str(response), mimetype='text/xml')


@app.route("/status")
def get_status():
    return jsonify(latest_call)


@app.route("/")
def dashboard():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Steve's Call Screener</title>
        <script>
            async function fetchStatus() {
                const res = await fetch("/status");
                const data = await res.json();
                document.getElementById("from").innerText = data.from || "None";
                document.getElementById("speech").innerText = data.speech || "Waiting...";
            }

            async function connect() {
                await fetch("/connect", { method: "POST" });
                alert("Call connected to Steve.");
            }

            async function reject() {
                await fetch("/reject", { method: "POST" });
                alert("Call rejected.");
            }

            setInterval(fetchStatus, 1000);
        </script>
    </head>
    <body>
        <h1>📞 Incoming Call</h1>
        <p><strong>From:</strong> <span id="from">None</span></p>
        <p><strong>They Said:</strong> <span id="speech">Waiting...</span></p>
        <button onclick="connect()">✅ Connect to Steve</button>
        <button onclick="reject()">❌ Reject Call</button>
    </body>
    </html>
    """
    return render_template_string(html)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
