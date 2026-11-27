import { useState, useEffect, useRef } from "react";
import {
  Activity, CalendarDays, CheckCircle2, Clock3, Headphones,
  LayoutDashboard, Mic, Phone, PhoneOff, Search, Settings,
  Stethoscope, Bell, ArrowUpRight
} from "lucide-react";

import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";

import "./App.css";

// Fetch doctors, appointments and open slots from the API in one go.
async function fetchDashboardData() {
  const [d, a, s] = await Promise.all([
    fetch("/api/doctors"),
    fetch("/api/appointments"),
    fetch("/api/slots"),
  ]);

  if (!d.ok || !a.ok || !s.ok) {
    throw new Error("Dashboard API unavailable");
  }

  const doctorData = await d.json();
  const appointmentData = await a.json();
  const slotData = await s.json();

  return {
    doctors: Array.isArray(doctorData) ? doctorData : doctorData.doctors || [],
    appointments: Array.isArray(appointmentData)
      ? appointmentData
      : appointmentData.appointments || [],
    slots: Array.isArray(slotData) ? slotData : slotData.slots || [],
  };
}

export default function App() {
  const clientRef = useRef(null);
  const audioRef = useRef(null);

  const [tab, setTab] = useState("Overview");
  const [search, setSearch] = useState("");
  const [doctors, setDoctors] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [slots, setSlots] = useState([]);
  const [apiConnected, setApiConnected] = useState(false);
  const [callActive, setCallActive] = useState(false);
  const [message, setMessage] = useState(
    "Your voice assistant is ready. Start a call to book or manage appointments."
  );

  const [transcript, setTranscript] = useState([]);

  async function refreshDashboard() {
    try {
      const data = await fetchDashboardData();
      setDoctors(data.doctors);
      setAppointments(data.appointments);
      setSlots(data.slots);
      setApiConnected(true);
    } catch {
      setApiConnected(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await fetchDashboardData();
        if (cancelled) return;

        setDoctors(data.doctors);
        setAppointments(data.appointments);
        setSlots(data.slots);
        setApiConnected(true);
      } catch {
        if (!cancelled) setApiConnected(false);
      }
    }

    load();
    const id = setInterval(load, 3000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const filteredDoctors = doctors.filter((d) =>
    `${d.doctor_name || d.name || ""} ${d.specialization || d.specialty || ""}`
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  const bookedCount = appointments.filter(
    a => (a.status || "").toUpperCase() === "BOOKED"
  ).length;

  const cancelledCount = appointments.filter(
    a => (a.status || "").toUpperCase() === "CANCELLED"
  ).length;

  const availableDoctors = doctors.filter(
    d => Number(d.open_today) > 0
  ).length;

  async function startCall() {
    if (clientRef.current) return;

    try {
      setMessage("Connecting to your AI voice assistant...");

      setTranscript(old => [
        ...old,
        {
          speaker: "System",
          text: "Connecting to the voice assistant...",
          time: "Now"
        }
      ]);

      const client = new PipecatClient({
        transport: new SmallWebRTCTransport(),
        enableMic: true,
        enableCam: false,

        callbacks: {
          onConnected: () => {
            setCallActive(true);
            setMessage("Connected! You can now speak to your assistant.");

            setTranscript(old => [
              ...old,
              {
                speaker: "System",
                text: "Voice connection established.",
                time: "Now"
              }
            ]);
          },

          onDisconnected: () => {
            setCallActive(false);
            setMessage("Call disconnected. You can start another conversation.");
            clientRef.current = null;
          },

          onTrackStarted: (track, participant) => {
            if (participant?.local) return;      // ignore your own mic
            if (track.kind !== "audio") return;  // only the bot's audio
            if (audioRef.current) {
              audioRef.current.srcObject = new MediaStream([track]);
              audioRef.current
                .play()
                .catch(err => console.error("Audio play failed:", err));
            }
          },

          onBotReady: () => {
            setMessage("Your AI assistant is ready. Start speaking!");
          },

          onUserTranscript: (data) => {
            if (!data.final || !data.text?.trim()) return;

            setTranscript(old => [
              ...old,
              {
                speaker: "You",
                text: data.text,
                time: "Now"
              }
            ]);
          },

          onBotTranscript: (data) => {
            if (!data.text?.trim()) return;

            setTranscript(old => [
              ...old,
              {
                speaker: "NexovAI Assistant",
                text: data.text,
                time: "Now"
              }
            ]);
          },

          onError: (error) => {
            console.error("Pipecat error:", error);
            setMessage("Voice connection error. Please try again.");
          }
        }
      });

      clientRef.current = client;

      await client.startBotAndConnect({
        endpoint: "/start",
        requestData: {
          transport: "webrtc",
          enableDefaultIceServers: true
        }
      });

    } catch (error) {
      console.error("Voice connection failed:", error);

      try {
        await clientRef.current?.disconnect();
      } catch (disconnectError) {
        console.error("Cleanup error:", disconnectError);
      }

      clientRef.current = null;
      setCallActive(false);
      setMessage(
        "Could not connect to the voice assistant. Check the backend terminal."
      );
    }
  }

  async function endCall() {
    try {
      await clientRef.current?.disconnect();
    } catch (error) {
      console.error("Disconnect error:", error);
    }
    if (audioRef.current) audioRef.current.srcObject = null;

    clientRef.current = null;
    setCallActive(false);
    setMessage("Call ended. You can start another conversation.");
  }

  return (
    <div className="app-shell">
      <audio ref={audioRef} autoPlay playsInline />

      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon"><Activity size={23} /></div>
          <div>
            <strong>NEXOV<span>AI</span></strong>
            <small>HEALTH ASSISTANT</small>
          </div>
        </div>

        <div className="side-label">WORKSPACE</div>

        {[
          ["Overview", LayoutDashboard],
          ["Appointments", CalendarDays],
          ["Doctors", Stethoscope]
        ].map(([name, Icon]) => (
          <button
            key={name}
            className={`nav-item ${tab === name ? "selected" : ""}`}
            onClick={() => setTab(name)}
          >
            <Icon size={18} /> {name}
          </button>
        ))}

        <div className="side-label tools-label">SYSTEM</div>

        <button className="nav-item" onClick={() => setTab("Settings")}>
          <Settings size={18} /> Settings
        </button>

        <div className="sidebar-bottom">
          <div className="support-icon"><Headphones size={20} /></div>
          <strong>Need assistance?</strong>
          <p>Your AI-powered appointment desk is available around the clock.</p>
          <span className="online"><i /> System online</span>
        </div>

        <div className="sidebar-footer">© 2026 NexovAI</div>
      </aside>

      <main className="main-area">

        <header className="topbar">
          <div>
            <div className="breadcrumb">
              Workspace <span>/</span> {tab}
            </div>

            <h1>
              {tab === "Overview" ? "Dashboard overview" : tab}
            </h1>

            <p className="subheading">
              Manage your clinic appointments with your AI voice assistant.
            </p>
          </div>

          <div className="top-actions">
            <div className="connection">
              <i className={apiConnected ? "green-dot" : "amber-dot"} />
              {apiConnected ? "Database connected" : "API integration pending"}
            </div>

            <button className="bell-button" aria-label="Notifications">
              <Bell size={19} />
            </button>

            <div className="avatar">N</div>
          </div>
        </header>

        <section className="stats-grid">

          <div className="stat-card">
            <div className="stat-icon purple"><CalendarDays /></div>
            <div>
              <span>Total appointments</span>
              <strong>{appointments.length}</strong>
              <small>All records</small>
            </div>
            <ArrowUpRight className="stat-arrow" size={17} />
          </div>

          <div className="stat-card">
            <div className="stat-icon green"><CheckCircle2 /></div>
            <div>
              <span>Booked appointments</span>
              <strong>{bookedCount}</strong>
              <small>Confirmed bookings</small>
            </div>
            <ArrowUpRight className="stat-arrow" size={17} />
          </div>

          <div className="stat-card">
            <div className="stat-icon orange"><Clock3 /></div>
            <div>
              <span>Available doctors</span>
              <strong>{availableDoctors}</strong>
              <small>With open slots today</small>
            </div>
            <ArrowUpRight className="stat-arrow" size={17} />
          </div>

          <div className="stat-card">
            <div className="stat-icon red"><Activity /></div>
            <div>
              <span>Cancelled</span>
              <strong>{cancelledCount}</strong>
              <small>Cancelled appointments</small>
            </div>
            <ArrowUpRight className="stat-arrow" size={17} />
          </div>

        </section>

        <section className="content-grid">

          <div className="panel voice-panel">

            <div className="panel-heading">
              <div>
                <span className="eyebrow">AI VOICE ASSISTANT</span>
                <h2>Appointment assistant</h2>
              </div>

              <span className="live-badge">
                <i /> {callActive ? "CALL ACTIVE" : "READY"}
              </span>
            </div>

            <div className={`voice-orb ${callActive ? "active" : ""}`}>
              <div className="orb-inner">
                <Mic size={34} />
              </div>
            </div>

            <h3>
              {callActive ? "Assistant session" : "How can we help today?"}
            </h3>

            <p className="voice-description">{message}</p>

            <div className="call-controls">
              {!callActive ? (
                <button className="start-call" onClick={startCall}>
                  <Phone size={18} /> Start call
                </button>
              ) : (
                <button className="end-call" onClick={endCall}>
                  <PhoneOff size={18} /> End call
                </button>
              )}
            </div>

            <div className="voice-footnote">
              <span><i /> ElevenLabs voice</span>
              <span><i /> Gemini AI</span>
              <span><i /> Pipecat</span>
            </div>

          </div>

          <div className="panel transcript-panel">

            <div className="panel-heading">
              <div>
                <span className="eyebrow">CONVERSATION</span>
                <h2>Live transcript</h2>
              </div>

              <span className="transcript-status">
                {callActive ? "● Live" : "● Waiting"}
              </span>
            </div>

            <div className="transcript-list">
              {transcript.map((item, index) => (
                <div className="transcript-message" key={index}>
                  <div className="message-avatar">
                    {item.speaker === "System"
                      ? "S"
                      : item.speaker === "You"
                        ? "Y"
                        : "N"}
                  </div>

                  <div className="message-body">
                    <div className="message-meta">
                      <strong>{item.speaker}</strong>
                      <span>{item.time}</span>
                    </div>

                    <p>{item.text}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="transcript-bottom">
              <span>
                <Mic size={15} />
                Speech recognition powered by ElevenLabs
              </span>
            </div>

          </div>

        </section>

        <section className="panel data-panel">

          <div className="panel-heading data-heading">
            <div>
              <span className="eyebrow">CLINIC DIRECTORY</span>
              <h2>Available doctors</h2>
              <p>Doctors available for appointment booking</p>
            </div>

            <div className="search-box">
              <Search size={17} />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search doctors..."
              />
            </div>
          </div>

          <div className="doctor-grid">
            {filteredDoctors.map((doctor, index) => {
              const doctorSlots = slots
                .filter(s => String(s.doctor_id) === String(doctor.doctor_id))
                .slice(0, 6);
              const openToday = Number(doctor.open_today) || 0;

              return (
                <div
                  className="doctor-card"
                  key={doctor.doctor_id || doctor.id || index}
                >
                  <div className="doctor-avatar">
                    {(doctor.doctor_name || doctor.name || "D")
                      .split(" ")
                      .slice(-1)[0][0]}
                  </div>

                  <div className="doctor-info">
                    <strong>
                      {doctor.doctor_name || doctor.name}
                    </strong>

                    <span>
                      {doctor.specialization || doctor.specialty}
                    </span>

                    <small>
                      Consultation: {
                        doctor.consultation_fee
                          ? `₹${doctor.consultation_fee}`
                          : doctor.fee || "—"
                      }
                    </small>

                    <div className="slot-row">
                      {doctorSlots.length === 0 && (
                        <span className="slot-none">No open slots</span>
                      )}
                      {doctorSlots.map(s => (
                        <span className="slot-chip" key={s.slot_id}>
                          {String(s.slot_date).slice(5, 10)}{" "}
                          {String(s.start_time).slice(0, 5)}
                        </span>
                      ))}
                    </div>
                  </div>

                  <span className={`available-tag ${openToday > 0 ? "" : "unavailable"}`}>
                    {openToday > 0 ? `${openToday} today` : "None today"}
                  </span>
                </div>
              );
            })}

            {filteredDoctors.length === 0 && (
              <p className="empty-state">No doctors found.</p>
            )}
          </div>

        </section>

        <section className="panel data-panel appointments-panel">

          <div className="panel-heading data-heading">
            <div>
              <span className="eyebrow">RECENT ACTIVITY</span>
              <h2>Appointments</h2>
              <p>Latest appointment records</p>
            </div>

            <button className="refresh-button" onClick={refreshDashboard}>
              Refresh data
            </button>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>APPOINTMENT</th>
                  <th>PATIENT</th>
                  <th>DOCTOR</th>
                  <th>DATE & TIME</th>
                  <th>STATUS</th>
                </tr>
              </thead>

              <tbody>
                {appointments.map((a, i) => {
                  const status = (a.status || "BOOKED").toUpperCase();

                  return (
                    <tr key={a.appointment_id || a.id || i}>
                      <td>#{a.appointment_id || a.id}</td>
                      <td>{a.patient_name || a.patient || "—"}</td>
                      <td>{a.doctor_name || a.doctor || "—"}</td>
                      <td>
                        {a.appointment_date || a.date || "—"}
                        <span className="time-text">
                          {a.appointment_time || a.time || ""}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`status-pill ${
                            status === "BOOKED" ? "booked" : "cancelled"
                          }`}
                        >
                          {status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {appointments.length === 0 && (
              <p className="empty-state">
                No appointments to display yet.
              </p>
            )}
          </div>

        </section>

        <footer className="page-footer">
          NexovAI Health Assistant
          <span>•</span>
          Powered by AI, designed for better care.
        </footer>

      </main>
    </div>
  );
}