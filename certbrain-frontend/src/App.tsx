import { useState, useEffect, useRef } from "react";
import { Search } from "lucide-react";

interface Cert {
  cert_name: string | null;
  issuer: string | null;
  year: string | number | null;
  source_file?: string;
  one_liner?: string | null;
  learnings?: (string | null)[];
  use_case?: string | null;
  interview_answer?: string | null;
  processed_at?: string;
}

interface Stats {
  total: number;
  last_updated: string;
  pending_review: number;
  pending_review_files: string[];
}

const ICONS = ["🏆","📜","🔐","🛡️","⚡","🌐","🔑","📊","🧩","✨","🎯","🔭","🧠","💡","🔬"];

export default function App() {
  const [certs, setCerts] = useState<Cert[]>([]);
  const [stats, setStats] = useState<Stats>({ total: 0, last_updated: "—", pending_review: 0, pending_review_files: [] });
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [scanMsg, setScanMsg] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Load data on mount ─────────────────────────────────────────────────────
  useEffect(() => {
    fetchAll();
  }, []);

  async function fetchAll() {
    try {
      const [certsRes, statsRes] = await Promise.all([
        fetch("/api/certs"),
        fetch("/api/stats"),
      ]);
      const certsData: Cert[] = await certsRes.json();
      const statsData: Stats = await statsRes.json();
      setCerts(certsData);
      setStats(statsData);
    } catch (e) {
      console.error("Failed to fetch data", e);
    }
  }

  // ── Scan ───────────────────────────────────────────────────────────────────
  async function handleScan() {
    if (isScanning) return;
    setIsScanning(true);
    setScanMsg("Scanning for new certs...");
    try {
      await fetch("/api/scan", { method: "POST" });
      pollRef.current = setInterval(async () => {
        try {
          const r = await fetch("/api/scan_status");
          const s = await r.json();
          if (!s.scanning) {
            clearInterval(pollRef.current!);
            await fetchAll();
            setIsScanning(false);
            setScanMsg("Scan complete!");
            setTimeout(() => setScanMsg(null), 3000);
          }
        } catch {
          clearInterval(pollRef.current!);
          setIsScanning(false);
        }
      }, 1500);
      // Safety: stop polling after 3 min
      setTimeout(() => {
        if (pollRef.current) clearInterval(pollRef.current);
        setIsScanning(false);
      }, 180000);
    } catch {
      setIsScanning(false);
      setScanMsg("Scan failed.");
      setTimeout(() => setScanMsg(null), 3000);
    }
  }

  // ── Filter ─────────────────────────────────────────────────────────────────
  const filtered = query.trim()
    ? certs.filter(c =>
        (c.cert_name ?? "").toLowerCase().includes(query.toLowerCase()) ||
        (c.issuer ?? "").toLowerCase().includes(query.toLowerCase()) ||
        (c.one_liner ?? "").toLowerCase().includes(query.toLowerCase())
      )
    : certs;

  const selectedCert = selectedIndex !== null ? filtered[selectedIndex] : null;
  const reviewFiles = stats.pending_review_files ?? [];

  return (
    <div className="flex flex-col h-screen bg-[#0A0A0B] text-[#E0E0E0] font-sans overflow-hidden border border-[#222]">

      {/* ── Top Bar ──────────────────────────────────────────────────────── */}
      <header className="h-20 flex items-center justify-between px-8 border-b border-[#1A1A1C] bg-[#0D0D0F] shrink-0">
        <div className="flex items-center gap-6">
          <h1 className="text-4xl font-black tracking-tighter text-white">
            CERTBRAIN<span className="text-[#3B82F6]">.</span>
          </h1>
          <div className="h-8 w-[1px] bg-[#222]" />
          <div className="flex gap-8">
            <div className="flex flex-col">
              <span className="text-[10px] uppercase tracking-widest text-[#555] font-bold">Total Certs</span>
              <span className="text-xl font-mono text-white">{stats.total}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] uppercase tracking-widest text-[#555] font-bold">Updated</span>
              <span className="text-xl font-mono text-white text-sm">{stats.last_updated}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] uppercase tracking-widest text-red-500/80 font-bold">Manual Review</span>
              <span className="text-xl font-mono text-red-400">
                {String(stats.pending_review).padStart(2, "0")}
              </span>
            </div>
          </div>
        </div>
        <button
          onClick={handleScan}
          disabled={isScanning}
          className="bg-white text-black px-6 py-2 rounded-full font-bold text-sm tracking-tight hover:bg-[#3B82F6] hover:text-white transition-colors disabled:opacity-50 cursor-pointer"
        >
          {isScanning ? "SCANNING..." : "SCAN FOR NEW CERTS"}
        </button>
      </header>

      {/* ── Main Layout ──────────────────────────────────────────────────── */}
      <main className="flex flex-1 overflow-hidden">

        {/* Sidebar */}
        <aside className="w-80 border-r border-[#1A1A1C] bg-[#0D0D0F] flex flex-col shrink-0 relative z-10">
          <div className="p-4 border-b border-[#1A1A1C]">
            <div className="relative">
              <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                <Search className="w-4 h-4 text-[#444]" />
              </div>
              <input
                type="text"
                placeholder="Filter certifications..."
                value={query}
                onChange={e => { setQuery(e.target.value); setSelectedIndex(null); }}
                className="w-full bg-[#151518] border border-[#222] rounded-lg py-2 pl-10 pr-4 text-xs focus:outline-none focus:border-[#3B82F6] text-white transition-colors"
              />
            </div>
          </div>

          <nav className="flex-1 overflow-y-auto">
            <div className="p-2 space-y-1">
              {filtered.length === 0 && (
                <p className="text-center text-[#444] text-xs py-8">
                  {certs.length === 0 ? "No certs yet. Drop PDFs/images in ~/Documents/certs-pdf and scan." : "No results."}
                </p>
              )}

              {filtered.map((cert, index) => {
                const isActive = selectedIndex === index;
                const name = cert.cert_name || cert.source_file || "Unknown Cert";
                const icon = ICONS[index % ICONS.length];
                return (
                  <div
                    key={index}
                    onClick={() => setSelectedIndex(index)}
                    className={`p-4 rounded-xl border transition-colors cursor-pointer ${
                      isActive
                        ? "bg-[#3B82F6]/10 border-[#3B82F6]/20"
                        : "hover:bg-[#151518] border-transparent"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-base">{icon}</span>
                      <span className={`flex-1 font-bold transition-colors text-sm truncate ${isActive ? "text-white" : "text-[#AAA]"}`}>
                        {name}
                      </span>
                      {isActive && (
                        <span className="text-[9px] bg-[#3B82F6] text-white px-1.5 py-0.5 rounded shrink-0">
                          ACTIVE
                        </span>
                      )}
                    </div>
                    <p className={`text-[10px] mt-1 uppercase font-semibold truncate ${isActive ? "text-[#888]" : "text-[#555]"}`}>
                      {cert.issuer ?? "Unknown"} {cert.year ? `• ${cert.year}` : ""}
                    </p>
                  </div>
                );
              })}

              {/* Manual Review Section */}
              {reviewFiles.length > 0 && (
                <>
                  <div className="px-5 pt-4 pb-2 text-[10px] font-bold text-[#555] uppercase mt-2">
                    Needs Manual Review
                  </div>
                  {reviewFiles.map((file, index) => (
                    <div key={index} className="mx-2 p-4 rounded-xl border border-red-900/30 bg-red-950/10 cursor-default">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-red-400 break-all text-xs">{file}</span>
                        <span className="text-[9px] bg-red-500 text-white px-1.5 py-0.5 rounded shrink-0 ml-2">FAILED</span>
                      </div>
                      <p className="text-[10px] text-red-800 mt-1 uppercase font-semibold">Could not extract automatically</p>
                    </div>
                  ))}
                </>
              )}
            </div>
          </nav>

          <div className="p-4 bg-[#0A0A0B] text-center border-t border-[#1A1A1C] shrink-0">
            <p className="text-[9px] font-mono text-[#444] uppercase">CertBrain v1.1 | Om Mehta</p>
          </div>
        </aside>

        {/* ── Main Panel ─────────────────────────────────────────────────── */}
        <section className="flex-1 bg-[#0A0A0B] p-12 overflow-y-auto relative z-0">
          {!selectedCert ? (
            <div className="flex flex-col items-center justify-center h-full opacity-50">
              <Search className="w-16 h-16 text-[#444] mb-4 stroke-[1.5px]" />
              <h2 className="text-2xl font-bold text-[#AAA]">Select a certificate to view details</h2>
              <p className="text-[#555] mt-2 text-sm">Or click "SCAN FOR NEW CERTS" to process the folder</p>
            </div>
          ) : (
            <div className="max-w-4xl" key={selectedIndex}>
              <div className="flex items-baseline justify-between mb-2">
                <span className="text-sm font-mono text-[#3B82F6] uppercase font-bold tracking-widest">
                  {selectedCert.issuer ?? "Unknown Issuer"}
                </span>
                <span className="text-sm font-mono text-[#555]">
                  {selectedCert.source_file ?? ""}
                </span>
              </div>

              <h2 className="text-5xl md:text-6xl lg:text-7xl font-black text-white leading-[0.85] tracking-tighter mb-8 italic pb-2">
                {selectedCert.cert_name ?? "Unknown Cert"}
              </h2>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-12 mb-12">
                <div className="col-span-1 lg:col-span-2 space-y-6">
                  {selectedCert.one_liner && (
                    <div>
                      <h3 className="text-[10px] uppercase tracking-[0.2em] text-[#555] font-black mb-2">The Gist</h3>
                      <p className="text-2xl font-medium leading-tight text-white">
                        {selectedCert.one_liner}
                      </p>
                    </div>
                  )}
                  {selectedCert.learnings && selectedCert.learnings.filter(Boolean).length > 0 && (
                    <div>
                      <h3 className="text-[10px] uppercase tracking-[0.2em] text-[#555] font-black mb-3">Key Learnings</h3>
                      <div className="flex flex-wrap gap-2">
                        {selectedCert.learnings.filter(Boolean).map((learning, i) => (
                          <span key={i} className="px-3 py-1 bg-[#1A1A1C] border border-[#222] rounded text-xs font-mono text-[#AAA]">
                            {learning}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="space-y-6">
                  {selectedCert.use_case && (
                    <div>
                      <h3 className="text-[10px] uppercase tracking-[0.2em] text-[#555] font-black mb-2">Practical Use Case</h3>
                      <p className="text-sm font-medium leading-relaxed text-[#AAA]">
                        {selectedCert.use_case}
                      </p>
                    </div>
                  )}
                  <div>
                    <h3 className="text-[10px] uppercase tracking-[0.2em] text-[#555] font-black mb-2">Year Issued</h3>
                    <p className="text-sm font-mono text-[#AAA]">{selectedCert.year ?? "N/A"}</p>
                  </div>
                  {selectedCert.processed_at && (
                    <div>
                      <h3 className="text-[10px] uppercase tracking-[0.2em] text-[#555] font-black mb-2">Processed</h3>
                      <p className="text-[10px] font-mono text-[#555]">{selectedCert.processed_at}</p>
                    </div>
                  )}
                </div>
              </div>

              {selectedCert.interview_answer && (
                <div className="bg-white p-8 rounded-2xl">
                  <h3 className="text-[10px] uppercase tracking-[0.2em] text-[#AAA] font-black mb-4">Interview Master Answer</h3>
                  <p className="text-xl font-bold text-black leading-snug">
                    "{selectedCert.interview_answer}"
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Toast */}
          {scanMsg && (
            <div className={`fixed bottom-6 right-6 px-6 py-3 rounded-xl shadow-lg text-sm font-bold text-white z-50 transition-colors ${isScanning ? "bg-[#3B82F6]" : "bg-[#10b981]"}`}>
              {scanMsg}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
