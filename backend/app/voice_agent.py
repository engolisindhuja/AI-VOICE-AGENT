
import os
import asyncio
import aiohttp

from datetime import datetime
from dotenv import load_dotenv

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema

from pipecat.frames.frames import EndFrame, LLMRunFrame

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask
from pipecat.pipeline.runner import PipelineRunner

from pipecat.processors.aggregators.llm_response_universal import (
    LLMContext,
    LLMContextAggregatorPair,
)

from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.elevenlabs.stt import (
    ElevenLabsRealtimeSTTService,
    CommitStrategy,
)
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import TransportParams

from backend.app.tools.availability import check_doctor_availability
from backend.app.tools.booking import book_appointment
from backend.app.tools.cancellation import cancel_appointment

import json

def make_json_safe(result):
    if not isinstance(result, dict):
        result = {"result": result}
    return json.loads(json.dumps(result, default=str))

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")


def validate_environment():

    missing = []

    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")

    if not ELEVENLABS_API_KEY:
        missing.append("ELEVENLABS_API_KEY")

    if not ELEVENLABS_VOICE_ID:
        missing.append("ELEVENLABS_VOICE_ID")

    if missing:
        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
        )


def get_tools():
    return ToolsSchema(standard_tools=[
        FunctionSchema(
            name="check_doctor_availability",
            description="Find available doctor appointment slots. All arguments are optional.",
            properties={
                "doctor_id": {"type": "integer", "description": "Doctor ID, if known."},
                "slot_date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
                "specialization": {"type": "string", "description": "e.g. Cardiologist, Dermatologist, General Physician."},
            },
            required=[],
        ),
        FunctionSchema(
            name="book_appointment",
            description="Book an available slot after the caller confirms everything.",
            properties={
                "patient_phone": {"type": "string"},
                "doctor_id": {"type": "integer"},
                "slot_id": {"type": "integer"},
            },
            required=["patient_phone", "doctor_id", "slot_id"],
        ),
        FunctionSchema(
            name="cancel_appointment",
            description="Cancel an appointment after verifying the patient's phone number.",
            properties={
                "patient_phone": {"type": "string"},
            },
            required=["patient_phone"],
        ),
    ])



async def handle_tool_call(params):

    function_name = params.function_name
    arguments = params.arguments or {}

    print(f"Tool called: {function_name}")
    print(f"Arguments: {arguments}")

    try:

        if function_name == "check_doctor_availability":

            result = await asyncio.to_thread(
                check_doctor_availability,
                doctor_id=arguments.get("doctor_id"),
                slot_date=arguments.get("slot_date"),
                specialization=arguments.get("specialization"),
            )

        elif function_name == "book_appointment":

            result = await asyncio.to_thread(
                book_appointment,
                patient_name=arguments.get("patient_name") or arguments["patient_phone"],
                patient_phone=arguments["patient_phone"],
                doctor_id=arguments["doctor_id"],
                slot_id=arguments["slot_id"],
            )

        elif function_name == "cancel_appointment":

            result = await asyncio.to_thread(
                cancel_appointment,
                appointment_id=arguments["appointment_id"],
                patient_phone=arguments["patient_phone"],
            )

        else:

            result = {
                "success": False,
                "message": "Unknown function."
            }

        print(f"Tool result: {result}")

        await params.result_callback(make_json_safe(result))

    except Exception as error:

        print(f"Tool error: {error}")

        await params.result_callback({
            "success": False,
            "message": str(error)
        })



SYSTEM_INSTRUCTION = """
You are a friendly AI doctor appointment assistant.

Your responsibilities:

1. Check doctor availability.
2. Book doctor appointments.
3. Cancel appointments.

IMPORTANT RULES:

- Ask only for the patient's phone number. Never ask for the patient's name.
- The caller's identity comes only from the phone number spoken aloud.
- Read the phone number back and ask for confirmation.
- Never book until the caller confirms the phone number.
- Never invent doctor names, slots, dates or appointment IDs.
- Always check availability before booking.
- Only offer slots returned by the availability tool.
- Before booking, confirm the doctor, date, time and phone number.
- Only book after the patient explicitly confirms.
- For cancellation, collect the appointment ID and phone
  number and use the cancellation tool.
- Never claim an appointment was booked or cancelled unless
  the corresponding tool reports success.
- Never expose internal tool errors as successful bookings.
- Do not provide medical diagnoses.
- Speak naturally and keep responses concise.
"""


async def bot(runner_args):

    validate_environment()

    now = datetime.now()
    date_note = (
        f"\n\nToday is {now.strftime('%A')}, {now.strftime('%Y-%m-%d')}. "
        "Always convert dates the caller says (today, tomorrow, '28th', 'next Monday') "
        "to YYYY-MM-DD using this date. If the caller gives no date, call "
        "check_doctor_availability with no slot_date to list the upcoming slots. "
        "Do not guess doctor names; use what the tool returns."
    )

    print("Starting AI Doctor Appointment Assistant...")

    async with aiohttp.ClientSession() as session:

        # WEBRTC TRANSPORT

        transport = await create_transport(
            runner_args,
            {
                "webrtc": lambda: TransportParams(
                    audio_in_enabled=True,
                    audio_out_enabled=True,
                )
            },
        )

        print("WebRTC transport initialized.")

        stt = ElevenLabsRealtimeSTTService(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            commit_strategy=CommitStrategy.VAD,
            enable_logging=True,
        )

        print("ElevenLabs STT initialized.")


        llm = GoogleLLMService(
        api_key=GEMINI_API_KEY,
        settings=GoogleLLMService.Settings(
        model="gemini-3.5-flash-lite",
        system_instruction=SYSTEM_INSTRUCTION + date_note,
    ),
)

        print("Gemini initialized.")


        tts = ElevenLabsTTSService(
        api_key=ELEVENLABS_API_KEY,
        settings=ElevenLabsTTSService.Settings(
        voice=ELEVENLABS_VOICE_ID,
        model="eleven_turbo_v2_5",
    ),
)

        print("ElevenLabs TTS initialized.")


        llm.register_function(
            "check_doctor_availability",
            handle_tool_call,
        )

        llm.register_function(
            "book_appointment",
            handle_tool_call,
        )

        llm.register_function(
            "cancel_appointment",
            handle_tool_call,
        )

        print("Appointment tools registered.")

        context = LLMContext([], tools=get_tools())

        context_aggregator = LLMContextAggregatorPair(
            context
        )


        pipeline = Pipeline([
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ])

        task = PipelineTask(pipeline)


        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):

            print("Browser client connected.")

            context.add_message({
                "role": "developer",
                "content": (
                    "Please introduce yourself to the patient. "
                    "Say that you are an AI doctor appointment "
                    "assistant and ask how you can help."
                )
            })

            await task.queue_frame(LLMRunFrame())

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):

            print("Browser client disconnected.")

            await task.queue_frame(EndFrame())


        print("Starting Pipecat pipeline...")

        runner = PipelineRunner()

        await runner.run(task)


if __name__ == "__main__":

    from pipecat.runner.run import main

    main()
