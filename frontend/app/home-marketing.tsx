import Link from "next/link";

import "./homepage.css";

const dialNumber =
  process.env.NEXT_PUBLIC_PHONE_NUMBER ??
  process.env.LIVEKIT_PHONE_NUMBER ??
  null;

export default function HomeMarketing() {
  return (
    <div className="home">
      <nav className="site-nav" aria-label="Primary">
        <span className="logo">What Now</span>
        <div className="links">
          <a href="#how">How</a>
          <a href="#phases">Phases</a>
          <a href="#dashboard">Room</a>
          <Link href="/login" className="nav-auth">
            Login
          </Link>
        </div>
      </nav>

      <header className="hero">
        <h1 className="dual-q" aria-label="What Now and Now What">
          <span className="q-a">What Now?</span>
          <span className="q-b">Now What?</span>
        </h1>
        {dialNumber ? (
          <a href={`tel:${dialNumber}`} className="num">
            {dialNumber}
          </a>
        ) : (
          <Link href="/login" className="num">
            Login to call
          </Link>
        )}
        <p className="tap">
          {dialNumber
            ? "Call from your phone · log in to see your session"
            : "Log in and register your phone to start"}
        </p>
        <Link
          href="/dashboard"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "inline-block",
            marginTop: 12,
            fontSize: 13,
            color: "#9ed4f5",
            opacity: 0.7,
            textDecoration: "none",
          }}
        >
          View Dashboard →
        </Link>
        <div className="orb" role="img" aria-label="Voice orb idle" />
        <p className="sub">
          After 911 and the people you love, pick up any phone. A calm voice walks
          you through what comes next.
        </p>
      </header>

      <section className="section" id="how">
        <div className="section-inner">
          <p className="section-kicker">How it works</p>
          <h3>You talk on a real phone. We handle the rest.</h3>
          <p className="body">
            Dial from any handset. LiveKit SIP connects you to the voice agent.
            The laptop on stage shows the orb — not a microphone.
          </p>
          <div className="steps">
            <div className="step">
              <span className="n">01</span>
              <strong>Dial</strong>
              <p>SIP connects you to the agent.</p>
            </div>
            <div className="step">
              <span className="n">02</span>
              <strong>Speak</strong>
              <p>Transcript routes to Qwen + Moss.</p>
            </div>
            <div className="step">
              <span className="n">03</span>
              <strong>Listen</strong>
              <p>One calm step at a time.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section" id="phases">
        <div className="section-inner">
          <p className="section-kicker">Phases</p>
          <h3>Four beats. One thread.</h3>
          <div className="phases-row" aria-label="Conversation phases">
            <span className="phase-pill on">Safety</span>
            <span className="phase-arrow">→</span>
            <span className="phase-pill off">Scene</span>
            <span className="phase-arrow">→</span>
            <span className="phase-pill off">Insurance</span>
            <span className="phase-arrow">→</span>
            <span className="phase-pill off">Legal</span>
          </div>
        </div>
      </section>

      <section className="section" id="dashboard">
        <div className="section-inner room-inner">
          <p className="section-kicker">What the room sees</p>
          <h3>Mission control on the projector.</h3>
          <p className="body">
            While you hold the phone, judges watch live transcript, tool fires,
            sponsors, and reasoning — streamed over SSE.
          </p>
          <div className="bezel">
            <div className="dash" aria-label="Dashboard preview">
              <div className="dash-bar">
                <span>/dashboard</span>
                <span className="live">● LIVE</span>
              </div>
              <div className="dash-grid">
                <div className="dash-tx">
                  <p className="dash-line user">
                    Caller: I called 911. They&apos;re on the way.
                  </p>
                  <p className="dash-line ai">
                    Agent: Good. Stay with me. Is anyone hurt?
                  </p>
                  <p className="dash-line user">
                    Caller: My friend slipped on wet tile.
                  </p>
                </div>
                <div className="dash-side">
                  <span className="dash-pill">TOOL · scene_guide</span>
                  <p className="dash-meta">
                    PHASE: Safety
                    <br />
                    MOSS: 134ms
                    <br />
                    QWEN: wet surface → hazard
                  </p>
                  <div className="sponsors">
                    <span className="sp on">Unsiloed</span>
                    <span className="sp">Moss</span>
                    <span className="sp">Qwen</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="cta-band">
        {dialNumber ? (
          <a href={`tel:${dialNumber}`} className="num">
            {dialNumber}
          </a>
        ) : (
          <Link href="/login" className="num">
            Login to call
          </Link>
        )}
        <Link
          href="/dashboard"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "block",
            marginTop: 16,
            fontSize: 13,
            color: "#9ed4f5",
            opacity: 0.7,
            textDecoration: "none",
          }}
        >
          View Dashboard →
        </Link>
      </section>

      <footer className="site-footer">
        <span>What Now</span>
        <span>Phone + projector demo</span>
      </footer>
    </div>
  );
}
