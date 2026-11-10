
import { useState, useRef, useEffect } from "react";
import {
  Mic, MicOff, Send, Volume2, VolumeX,
  RotateCcw, Sparkles, User, Bot, Loader2
} from "lucide-react";
import "./index.css";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const suggestions = [
  "Tell me about your journey",
  "What's your biggest superpower?",
  "What are you currently learning?",
  "How do you handle challenges?",
  "Why should we hire you?"
];

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [model, setModel] = useState("");
  const [error, setError] = useState("");
  const [profile, setProfile] = useState("auto");

  const bottomRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Stop microphone and speech when leaving the page.
  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
      window.speechSynthesis?.cancel();
    };
  }, []);

  async function sendMessage(text = input) {
    const question = text.trim();

    if (!question || loading) return;

    const history = messages.map(({ role, content }) => ({
      role: role === "assistant" ? "model" : "user",
      content
    }));

    setMessages(prev => [
      ...prev,
      { role: "user", content: question }
    ]);

    setInput("");
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: question,
          history,
          profile
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to get a response.");
      }

      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: data.reply,
          model: data.model_used,
          sources: data.sources || [],
          detectedProfile: data.detected_profile || "general"
        }
      ]);

      setModel(data.model_used || "");

    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function startListening() {
    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError("Speech recognition isn't supported in this browser. Please use Chrome or type your question.");
      return;
    }

    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onstart = () => {
      setListening(true);
      setError("");
    };

    recognition.onresult = event => {
      const transcript = event.results[0][0].transcript;
      setInput(transcript);
    };

    recognition.onerror = event => {
      const errorMessages = {
        network: "Speech recognition couldn't reach your browser's online speech service. Check your internet connection, disable any VPN or network filter that may block it, or type your question instead.",
        "not-allowed": "Microphone access is blocked. Allow microphone access for this site in your browser settings, then try again.",
        "service-not-allowed": "Your browser isn't allowing its speech-recognition service. Try Chrome or Edge, or type your question instead.",
        "audio-capture": "No microphone was found. Connect a microphone and try again.",
        "no-speech": "No speech was detected. Try speaking closer to your microphone.",
        "language-not-supported": "Speech recognition doesn't support the selected language in this browser."
      };

      setListening(false);
      setError(
        errorMessages[event.error] ||
        `Speech recognition failed (${event.error}). You can type your question instead.`
      );
    };

    recognition.onend = () => {
      setListening(false);
      if (recognitionRef.current === recognition) {
        recognitionRef.current = null;
      }
    };

    recognitionRef.current = recognition;

    try {
      recognition.start();
    } catch (startError) {
      recognitionRef.current = null;
      setListening(false);
      setError(
        `Couldn't start speech recognition: ${startError.message || "please check your microphone permissions and try again."}`
      );
    }
  }

  function speak(text) {
    if (!window.speechSynthesis) {
      setError("Speech output is not supported in this browser.");
      return;
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-IN";
    utterance.rate = 1;
    utterance.pitch = 1;

    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);

    window.speechSynthesis.speak(utterance);
  }

  function stopSpeaking() {
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }

  function resetChat() {
    window.speechSynthesis.cancel();
    recognitionRef.current?.stop();

    setMessages([]);
    setInput("");
    setError("");
    setModel("");
    setProfile("auto");
    setSpeaking(false);
    setListening(false);
  }

  return (
    <div className="app">
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">
            <Sparkles size={20} />
          </div>
          <div>
            <h2>Meet Yash</h2>
            <span>AI conversation experience</span>
          </div>
        </div>

        <button className="reset-btn" onClick={resetChat}>
          <RotateCcw size={16} />
          <span>New conversation</span>
        </button>
      </header>

      <main className="main-container">
        <section className="hero">
          <div className="online-indicator">
            <span className="online-dot" />
            PERSONAL AI ASSISTANT
          </div>

          <h1>
            Get to know <span>Yash.</span>
          </h1>

          <p>
            Ask me about my journey, experiences, strengths,
            ambitions and the things I'm passionate about.
          </p>
        </section>

        <section className="chat-container">
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="avatar-large">
                <Sparkles size={30} />
              </div>

              <h2>Hey, nice to meet you!</h2>

              <p>
                I'm an AI representation of Yash.
                What would you like to know about me?
              </p>

              <div className="suggestions">
                {suggestions.map(item => (
                  <button
                    key={item}
                    onClick={() => sendMessage(item)}
                    disabled={loading}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message, index) => (
                <div
                  className={`message-row ${message.role}`}
                  key={index}
                >
                  <div className="message-avatar">
                    {message.role === "assistant"
                      ? <Bot size={18} />
                      : <User size={18} />}
                  </div>

                  <div className="message-content">
                    <span className="message-label">
                      {message.role === "assistant" ? "YASH'S AI" : "YOU"}
                    </span>

                    <div className="message-content markdown-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>

                    {message.role === "assistant" && message.sources?.length > 0 && (
                      <div className="retrieved-sources" style={{
                        marginTop: "8px",
                        fontSize: "11px",
                        opacity: 0.72
                      }}>
                        <span>Resume sources: </span>
                        {message.sources.map((source, sourceIndex) => (
                          <span key={`${source.source_file}-${sourceIndex}`}>
                            {source.source_file}
                            {sourceIndex < message.sources.length - 1 ? " · " : ""}
                          </span>
                        ))}
                      </div>
                    )}

                    {message.role === "assistant" && (
                      <button
                        className="listen-btn"
                        onClick={() =>
                          speaking
                            ? stopSpeaking()
                            : speak(message.content)
                        }
                      >
                        {speaking
                          ? <VolumeX size={15} />
                          : <Volume2 size={15} />}
                        {speaking ? "Stop audio" : "Listen"}
                      </button>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="loading-message">
                  <Loader2 className="spinner" size={18} />
                  Thinking...
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          )}
        </section>

        {error && (
          <div className="error-box">
            <span>{error}</span>
            <button onClick={() => setError("")}>Dismiss</button>
          </div>
        )}

        <section className="input-section">
          <div className="profile-selector" style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            marginBottom: "12px",
            flexWrap: "wrap"
          }}>
            <label htmlFor="resume-profile" style={{ fontSize: "13px", opacity: 0.8 }}>
              Resume focus
            </label>
            <select
              id="resume-profile"
              value={profile}
              onChange={e => setProfile(e.target.value)}
              disabled={loading}
              style={{
                padding: "9px 12px",
                borderRadius: "10px",
                border: "1px solid var(--border, #d1d5db)",
                background: "var(--surface, #fff)",
                color: "inherit",
                fontSize: "13px"
              }}
            >
              <option value="auto">Auto-detect from question</option>
              <option value="data_analyst">Data Analyst resume</option>
              <option value="data_scientist">Data Scientist resume</option>
              <option value="data_engineer">Data Engineer resume</option>
              <option value="genai">Generative AI resume</option>
              <option value="general">Search all resumes</option>
            </select>
            <span style={{ fontSize: "12px", opacity: 0.65 }}>
              You can change this at any time.
            </span>
          </div>
          <div className="input-box">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter") sendMessage();
              }}
              placeholder="Ask me anything..."
              disabled={loading}
            />

            <button
              className={`mic-btn ${listening ? "recording" : ""}`}
              onClick={startListening}
              title="Speak your question"
            >
              {listening ? <MicOff size={20} /> : <Mic size={20} />}
            </button>

            <button
              className="send-btn"
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              title="Send message"
            >
              <Send size={19} />
            </button>
          </div>

          <p className="input-hint">
            {listening
              ? "Listening... Speak now."
              : "Press Enter to send · Tap the microphone to speak"}
          </p>
        </section>

        <footer>
          <span>
            {model ? `Powered by ${model}` : "AI-powered conversation"}
          </span>
          <span>Built with React + FastAPI</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
