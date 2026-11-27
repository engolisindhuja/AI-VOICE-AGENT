#Voice AI Doctor Appointment Assistant

A voice agent that checks doctor availability, books and cancels appointments, with a React dashboard showing the live transcript, doctors, slots and appointments.

- Voice pipeline: Pipecat (Python), SmallWebRTC
- STT / TTS: ElevenLabs
- LLM: Google Gemini (function calling), model: [Gemini-3.5-flash-lite]
- Dashboard API: FastAPI
- Database: MySQL
- Frontend: React + Vite

 How it works
Browser audio → Pipecat → ElevenLabs STT → Gemini (tools) → ElevenLabs TTS → browser.
Tools: `check_doctor_availability`, `book_appointment`, `cancel_appointment`.
The caller is identified only by the phone number they say, which the agent reads back before booking or cancelling.

1. Create a MySQL database `ai_voice_agent` and import `schema.sql`.
2. Copy `.env.example` to `.env` and fill in your keys and MySQL credentials.
3. Backend: `python -m venv venv`, activate it, then `pip install -r requirements.txt`.
4. Frontend: `cd frontend` then `npm install`.

#run

python -m backend.app.voice_agent --transport webrtc
uvicorn backend.app.api:app --port 8000
cd frontend && npm run dev
```
Open http://localhost:5173 and click Start call.
