import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Where the user-editable .env lives. In the PyInstaller build, __file__ is
# inside the bundle's _internal\ directory but users (and the installer) put
# .env next to Clicky.exe at the install root — reading _HERE from __file__
# there meant .env edits were silently ignored (GitHub issue #3).
if getattr(sys, "frozen", False):
    _HERE = Path(sys.executable).parent
else:
    _HERE = Path(__file__).parent

# Load env files in priority order. .env.local overrides .env (Next.js convention,
# which is how many users — including this one — keep their real keys).
for _name in (".env", ".env.local"):
    _p = _HERE / _name
    if _p.exists():
        load_dotenv(_p, override=True)


DEFAULT_SYSTEM_PROMPT = """You are Clicky, a VISUAL AI tutor running on Windows. You live
next to the user's cursor. Your job is to *show*, not just tell.

{{CONTEXT}}

HARD RULES (never break):
  1. LOCATE QUESTIONS ("where is X", "how do I click Y", "show me X", "find X"):
     Point at it and explain in ONE sentence. If it's not visible, say so
     plainly instead of guessing.

  2. MULTI-STEP TASKS (export, install, configure, setup, etc.):
     Describe ONLY the next single step, then end with "Say 'next' when
     ready." Never dump a numbered list of 5 steps in one response.

  3. VISION: describe only what is ACTUALLY in the screenshot. Trust your
     eyes over the user's words.

  4. WEB SEARCH: when search results appear, use them as your primary
     source and give a direct answer — never say "I don't know" if the
     results contain real facts. Today is {{TODAY}}.

  5. PUBLIC figures, celebrities, companies, products — answer freely.
     Never refuse with "I can't identify people" — these are public figures
     with public information available.

STYLE: warm, concise, teacher-y. 1-2 sentences per step. No markdown bullets
unless genuinely listing options."""


# Technical rules Clicky needs to actually draw on screen and point at
# elements correctly. Always appended after the user-editable prompt above
# — kept separate because breaking this syntax breaks pointing/drawing, and
# most users have no reason to touch it.
_TECHNICAL_RULES = """

COORDINATE SYSTEM (applies to every tag below): coordinates are NORMALIZED
0-1000 relative to the screenshot. x=0 is the LEFT edge, x=1000 the RIGHT
edge; y=0 is the TOP, y=1000 the BOTTOM. The exact centre of the screen is
500,500. Sizes/radii use the same scale (100 = 10% of screen width).

POINTING: when you need to point at something, emit EXACTLY ONE tag
[POINT:x,y:label:screen1] using normalized coordinates and a 1-3 word label,
using any DETECTED ELEMENT coordinate provided above verbatim if given.

DRAWING TAGS (coords normalized 0-1000, trailing :color always optional):
  [LINE:x1,y1->x2,y2:color]         straight line
  [ARROW:x1,y1->x2,y2:color]        line with arrowhead (points at x2,y2)
  [CIRCLE:x,y,r:label:color]        ring; label optional
  [RECT:x1,y1,x2,y2:color]          rectangle by opposite corners
  [POLY:x1,y1 x2,y2 x3,y3:color]    closed shape, 3+ points (triangles!)
  [TEXT:x,y:content:color:size]     text; size s|m|l (default m)
  [ANGLE:x,y,s,rot:color]           right-angle marker at corner (x,y)
  [CLEAR]                           wipe all drawings
Colors: blue red green yellow orange purple white cyan (default blue).
For real UI elements use anchors instead of guessing coordinates:
  [CIRCLE:@Save button]  [UNDERLINE:@File menu]  — resolved pixel-perfectly.

TEACHING WITH DRAWINGS: when explaining something visible on screen (a
figure, chart, diagram, equation, code), draw ON it — trace edges, label
parts, add helper lines — interleaving tags with your spoken words in the
order a teacher draws on a whiteboard. Place TEXT next to what it names,
never covering it. Use up to ~10 shapes for a full lesson, 1-2 for a quick
highlight.

ACCURACY DISCIPLINE: if DETECTED FIGURES are listed above, copy those
vertex numbers into your tags EXACTLY. Only estimate coordinates for things
not listed. When estimating: fix the figure's bounding box first, derive
every endpoint from it, and reuse IDENTICAL numbers for shared vertices.

NARRATION SYNC: Clicky speaks your response sentence by sentence and draws
each sentence's tags WHILE saying that sentence — put every tag immediately
after the words that describe it, spread across the lesson (1-2 tags per
sentence), never dump all tags at the start or end."""


@dataclass
class Config:
    # LLM
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY") or None)
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY") or None)
    # Point the OpenAI provider at any OpenAI-compatible server (DeepSeek,
    # Alibaba DashScope/Qwen, SiliconFlow, OpenRouter...). Empty = real OpenAI.
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "").strip())
    openai_default_model: str = field(default_factory=lambda: os.getenv("OPENAI_DEFAULT_MODEL", "").strip())
    # Botoes simplificados do companheiro Seu Nono: DeepSeek e Sabia (Maritaca).
    # Os dois usam o mesmo provedor generico (ai/openai_compat_provider.py).
    # As chaves seguem o mesmo nome usado no portal Controle Popular.
    deepseek_api_key: Optional[str] = field(default_factory=lambda: os.getenv("AI_API_KEY_DEEPSEEK") or None)
    deepseek_base_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))
    deepseek_model: str = field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    maritaca_api_key: Optional[str] = field(default_factory=lambda: os.getenv("AI_API_KEY_MARITACA") or None)
    maritaca_base_url: str = field(default_factory=lambda: os.getenv("MARITACA_BASE_URL", "https://chat.maritaca.ai/api"))
    maritaca_model: str = field(default_factory=lambda: os.getenv("MARITACA_MODEL", "sabiazinho-4"))
    # Portal Controle Popular: quando ligado, o companheiro pergunta ao Seu Nono
    # pelo endpoint /api/companheiro — o portal guarda o RAG e as chaves.
    portal_ativo: bool = field(default_factory=lambda: os.getenv(
        "CLICKY_PORTAL_ATIVO", "0"
    ).strip().lower() in ("1", "true", "sim", "yes", "on"))
    portal_url: str = field(default_factory=lambda: os.getenv(
        "CLICKY_PORTAL_URL", "https://www.controlepopular.com.br"
    ))
    companheiro_token: Optional[str] = field(default_factory=lambda: os.getenv("COMPANHEIRO_TOKEN") or None)
    # Ponte local (sessao pareada): servidor SO no loopback que recebe, do
    # navegador, as coordenadas dos alvos do Seu Nono (chips [n] e "Abrir
    # pagina"). O portal abre a conexao; a pagina publica alcanca 127.0.0.1
    # pelo preflight de Private Network Access.
    ponte_porta: int = field(default_factory=lambda: max(
        1024, min(65535, int(os.getenv("CLICKY_PONTE_PORTA", "8765") or 8765))
    ))
    google_api_key: Optional[str] = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or None)
    ollama_host: str = field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    # Legacy single-model knob — still respected as a fallback for both slots
    # below. New users should prefer OLLAMA_VISION_MODEL / OLLAMA_TEXT_MODEL.
    # Default was "llama3.2-vision" until it stopped loading: it is built on
    # the 'mllama' architecture, which newer Ollama releases dropped. `ollama
    # pull` still succeeds and `ollama list` still shows it, so it looked
    # installed and correct — then every screen-aware question came back as an
    # opaque HTTP 500 from /api/chat. qwen2.5vl:3b is what the setup wizard
    # already pulls, so this also makes the two agree.
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5vl:3b"))
    # Two-slot model selection: vision = screen-aware queries, text = Code Mode
    # / journal Q&A / no-screenshot replies. Either can be overridden at runtime
    # via cfg.set_ollama_model("vision"|"text", name).
    ollama_vision_model: str = field(default_factory=lambda: os.getenv("OLLAMA_VISION_MODEL", "") or os.getenv("OLLAMA_MODEL", "qwen2.5vl:3b"))
    ollama_text_model:   str = field(default_factory=lambda: os.getenv("OLLAMA_TEXT_MODEL", "") or "llama3.2:3b")

    # Ollama performance tuning knobs (keep_alive, GPU offload, thread count, context length)
    ollama_keep_alive:   str = field(default_factory=lambda: os.getenv("OLLAMA_KEEP_ALIVE", "10m"))
    ollama_num_gpu:      int = field(default_factory=lambda: int(os.getenv("OLLAMA_NUM_GPU", "-1")))
    ollama_num_thread:   Optional[int] = field(default_factory=lambda: int(v) if (v := os.getenv("OLLAMA_NUM_THREAD", "").strip()) else None)
    ollama_num_ctx:      int = field(default_factory=lambda: int(os.getenv("OLLAMA_NUM_CTX", "4096")))

    # LM Studio — local OpenAI-compatible server (Developer tab → Start Server).
    # No key needed. Leave LMSTUDIO_MODEL empty to use whatever's loaded.
    lmstudio_host: str = field(default_factory=lambda: os.getenv("LMSTUDIO_HOST", "http://localhost:1234/v1"))
    lmstudio_model: str = field(default_factory=lambda: os.getenv("LMSTUDIO_MODEL", ""))

    # STT
    deepgram_api_key: Optional[str] = field(default_factory=lambda: os.getenv("DEEPGRAM_API_KEY") or None)
    whisper_model: str = field(default_factory=lambda: os.getenv("WHISPER_MODEL", "base"))
    # ISO code (e.g. "de", "en"). Empty = auto-detect language per utterance.
    whisper_language: str = field(default_factory=lambda: os.getenv("WHISPER_LANGUAGE", ""))
    # sounddevice input device index. Empty/unset = system default mic.
    mic_device_index: Optional[int] = field(default_factory=lambda: (
        int(v) if (v := os.getenv("MIC_DEVICE_INDEX", "").strip()) else None
    ))
    # Fixed reply language (ISO 639-1, e.g. "de"). Empty = auto-detect per
    # message (can mix languages if transcription is inconsistent).
    response_language: str = field(default_factory=lambda: os.getenv("RESPONSE_LANGUAGE", ""))
    # User-defined scope/rules appended to every system prompt (e.g. "only
    # help with Excel, refuse anything else"). Empty = no restriction.
    custom_instructions: str = field(default_factory=lambda: os.getenv(
        "CUSTOM_INSTRUCTIONS", DEFAULT_SYSTEM_PROMPT
    ).replace("\\n", "\n"))

    # TTS
    elevenlabs_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY") or None)
    elevenlabs_voice_id: str = field(default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", ""))

    # Search
    tavily_api_key: Optional[str] = field(default_factory=lambda: os.getenv("TAVILY_API_KEY") or None)

    # App
    # Push-to-talk. Two-key modifier combo — no clash with app shortcuts and
    # easier to hold than a 3-key chord. Override with CLICKY_HOTKEY in .env.
    hotkey: str = field(default_factory=lambda: os.getenv("CLICKY_HOTKEY", "ctrl+win"))

    # Microphone mode:
    #   "hotkey"  (default) — mic opens only while you're asking something.
    #             Tap the hotkey and speak; Clicky answers when you stop
    #             talking. Holding it also works and ends on release.
    #   "ambient" — legacy always-on mic with "Clicky" wake-word detection.
    #             Costs a continuous Whisper pass over everything it hears.
    mic_mode: str = field(default_factory=lambda: (
        os.getenv("CLICKY_MIC_MODE", "hotkey").strip().lower() or "hotkey"
    ))

    # How long a tap may last before it counts as a hold. Under this, releasing
    # the key does NOT stop the recording — silence detection does.
    tap_max_seconds: float = field(default_factory=lambda: float(
        os.getenv("CLICKY_TAP_MAX_SECONDS", "0.6") or 0.6
    ))

    def ambient_mic(self) -> bool:
        """True when the mic should stay open and scan for the wake word."""
        return self.mic_mode == "ambient"

    # Bichinho que segue o cursor. "preguica" (padrao) e o bicho-preguica do
    # companheiro Seu Nono; "triangulo" e o buddy azul original do Clicky.
    buddy_theme: str = field(default_factory=lambda: (
        os.getenv("CLICKY_BUDDY_THEME", "preguica").strip().lower() or "preguica"
    ))

    def set_buddy_theme(self, tema: str) -> None:
        """Troca o bichinho entre preguica e triangulo, gravando no .env."""
        tema = "triangulo" if tema == "triangulo" else "preguica"
        self.buddy_theme = tema
        os.environ["CLICKY_BUDDY_THEME"] = tema
        self._write_env("CLICKY_BUDDY_THEME", tema)

    # Tamanho do bicho: 1 = 36 px, 2 = 72 px (padrao), 3 = 108 px. Escala
    # inteira para o pixel art nao borrar.
    buddy_escala: int = field(default_factory=lambda: max(
        1, min(6, int(os.getenv("CLICKY_BUDDY_ESCALA", "2") or 2))
    ))

    def set_buddy_escala(self, escala: int) -> None:
        """Define o tamanho do bicho (1 a 6), gravando no .env."""
        escala = max(1, min(6, int(escala)))
        self.buddy_escala = escala
        os.environ["CLICKY_BUDDY_ESCALA"] = str(escala)
        self._write_env("CLICKY_BUDDY_ESCALA", str(escala))

    # Bicho discreto quando ocioso: enquanto so segue o cursor, sem apontar
    # nada, ele fica translucido e um pouco menor, para nao cobrir os dados da
    # pagina. Volta ao normal na primeira acao (apontar, ouvir, pensar, falar).
    # Valores em 0..1: `alfa` = opacidade ociosa, `escala` = tamanho ocioso.
    buddy_ocioso_alfa: float = field(default_factory=lambda: max(
        0.2, min(1.0, float(os.getenv("CLICKY_BUDDY_OCIOSO_ALFA", "0.5") or 0.5))
    ))
    buddy_ocioso_escala: float = field(default_factory=lambda: max(
        0.5, min(1.0, float(os.getenv("CLICKY_BUDDY_OCIOSO_ESCALA", "0.82") or 0.82))
    ))

    def set_buddy_ocioso(self, alfa: float, escala: float) -> None:
        """Ajusta a discricao do bicho ocioso (0..1), gravando no .env."""
        self.buddy_ocioso_alfa = max(0.2, min(1.0, float(alfa)))
        self.buddy_ocioso_escala = max(0.5, min(1.0, float(escala)))
        os.environ["CLICKY_BUDDY_OCIOSO_ALFA"] = f"{self.buddy_ocioso_alfa:.2f}"
        os.environ["CLICKY_BUDDY_OCIOSO_ESCALA"] = f"{self.buddy_ocioso_escala:.2f}"
        self._write_env("CLICKY_BUDDY_OCIOSO_ALFA", f"{self.buddy_ocioso_alfa:.2f}")
        self._write_env("CLICKY_BUDDY_OCIOSO_ESCALA", f"{self.buddy_ocioso_escala:.2f}")

    def set_portal_ativo(self, ativo: bool) -> None:
        """Liga/desliga o modo portal: responder pelo Seu Nono do site."""
        self.portal_ativo = bool(ativo)
        valor = "1" if ativo else "0"
        os.environ["CLICKY_PORTAL_ATIVO"] = valor
        self._write_env("CLICKY_PORTAL_ATIVO", valor)

    def set_mic_mode(self, mode: str) -> None:
        """Persisted switch between hotkey-only and always-listening."""
        mode = "ambient" if mode == "ambient" else "hotkey"
        self.mic_mode = mode
        os.environ["CLICKY_MIC_MODE"] = mode
        self._write_env("CLICKY_MIC_MODE", mode)

    def provedores_openai_compat(self) -> dict[str, dict]:
        """Presets dos botoes simplificados (DeepSeek e Sabia/Maritaca).

        Devolve, por id, os argumentos que o `OpenAICompatProvider` espera.
        `aceita_imagem` fica False nos dois: o chat do DeepSeek e o Sabiazinho
        respondem por texto — mandar imagem daria erro.
        """
        return {
            "deepseek": {
                "rotulo": "DeepSeek",
                "base_url": self.deepseek_base_url,
                "api_key": self.deepseek_api_key or "",
                "modelo": self.deepseek_model,
                "aceita_imagem": False,
            },
            "maritaca": {
                "rotulo": "Sabia (Maritaca)",
                "base_url": self.maritaca_base_url,
                "api_key": self.maritaca_api_key or "",
                "modelo": self.maritaca_model,
                "aceita_imagem": False,
            },
        }

    def llm_provider(self) -> str:
        """Returns the active LLM provider (runtime override > priority chain).

        Priority chain: Claude > OpenAI > GitHub Copilot > Gemini > Ollama.
        """
        override = os.environ.get("CLICKY_ACTIVE_LLM", "").strip().lower()
        if override in self.available_llm_providers():
            return override
        if self.portal_ativo:
            return "portal"
        if self.anthropic_api_key:
            return "claude"
        if self.openai_api_key:
            return "openai"
        try:
            from ai.github_copilot_provider import is_authenticated as _gh_ok
            if _gh_ok():
                return "copilot"
        except Exception:
            pass
        if self.google_api_key:
            return "gemini"
        if self.deepseek_api_key:
            return "deepseek"
        if self.maritaca_api_key:
            return "maritaca"
        return "ollama"

    def available_llm_providers(self) -> list[str]:
        """All providers the user can switch to right now."""
        out = []
        if self.portal_ativo:
            out.append("portal")
        if self.anthropic_api_key:
            out.append("claude")
        if self.openai_api_key:
            out.append("openai")
        try:
            from ai.github_copilot_provider import is_authenticated as _gh_ok
            if _gh_ok():
                out.append("copilot")
        except Exception:
            pass
        if self.google_api_key:
            out.append("gemini")
        if self.deepseek_api_key:
            out.append("deepseek")
        if self.maritaca_api_key:
            out.append("maritaca")
        out.append("ollama")     # always available if the daemon is running
        out.append("lmstudio")   # always available if the local server is running
        return out

    def set_active_llm(self, name: str) -> None:
        """Runtime switch — next query uses this provider. Persisted to .env."""
        name = name.lower()
        os.environ["CLICKY_ACTIVE_LLM"] = name
        # Write to .env so the choice survives restarts
        env_path = _HERE / ".env"
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True) if env_path.exists() else []
            key = "CLICKY_ACTIVE_LLM"
            found = False
            for i, line in enumerate(lines):
                if line.startswith(key + "=") or line.startswith(key + " ="):
                    lines[i] = f"{key}={name}\n"
                    found = True
                    break
            if not found:
                lines.append(f"\n{key}={name}\n")
            env_path.write_text("".join(lines), encoding="utf-8")
        except Exception:
            pass  # non-fatal — runtime switch still works via os.environ

    # ── API key management ───────────────────────────────────────────────
    #
    # Keys used to be .env-only, which meant a packaged install had no way to
    # enter one short of hand-editing a file next to Clicky.exe. These helpers
    # back the Settings → API Keys dialog.

    # env var name → (dataclass attribute, human label)
    API_KEY_FIELDS = {
        "ANTHROPIC_API_KEY":  ("anthropic_api_key",  "Anthropic (Claude)"),
        "OPENAI_API_KEY":     ("openai_api_key",     "OpenAI (GPT)"),
        "GOOGLE_API_KEY":     ("google_api_key",     "Google (Gemini)"),
        "AI_API_KEY_DEEPSEEK": ("deepseek_api_key",  "DeepSeek"),
        "AI_API_KEY_MARITACA": ("maritaca_api_key",  "Sabia (Maritaca)"),
        "COMPANHEIRO_TOKEN":  ("companheiro_token",  "Controle Popular (token do companheiro)"),
        "ELEVENLABS_API_KEY": ("elevenlabs_api_key", "ElevenLabs (voice)"),
        "DEEPGRAM_API_KEY":   ("deepgram_api_key",   "Deepgram (speech-to-text)"),
        "TAVILY_API_KEY":     ("tavily_api_key",     "Tavily (web search)"),
    }

    @staticmethod
    def env_path() -> Path:
        """The .env Clicky reads and writes — next to Clicky.exe when frozen."""
        return _HERE / ".env"

    def get_api_key(self, env_var: str) -> str:
        attr = self.API_KEY_FIELDS.get(env_var, (None, None))[0]
        return (getattr(self, attr, None) or "") if attr else ""

    def set_api_key(self, env_var: str, value: str) -> None:
        """Set (or clear) one key: live in this process + persisted to .env."""
        if env_var not in self.API_KEY_FIELDS:
            return
        value = (value or "").strip()
        attr = self.API_KEY_FIELDS[env_var][0]

        setattr(self, attr, value or None)
        if value:
            os.environ[env_var] = value
        else:
            os.environ.pop(env_var, None)

        self._write_env(env_var, value)

    def _write_env(self, key: str, value: str) -> None:
        """Upsert KEY=value in .env, removing the line entirely when cleared."""
        path = self.env_path()
        try:
            lines = (
                path.read_text(encoding="utf-8").splitlines(keepends=True)
                if path.exists() else []
            )
            out, found = [], False
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                    found = True
                    if value:
                        out.append(f"{key}={value}\n")
                    # cleared → drop the line
                    continue
                out.append(line)

            if value and not found:
                if out and not out[-1].endswith("\n"):
                    out.append("\n")
                out.append(f"{key}={value}\n")

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("".join(out), encoding="utf-8")
        except Exception:
            pass  # runtime value still applied; persistence is best-effort

    def clear_active_llm(self) -> None:
        """Unpin the provider so the key-priority chain decides again.

        Used when the key behind a pinned provider is removed — otherwise
        llm_provider() keeps naming a provider that can no longer answer.
        """
        os.environ.pop("CLICKY_ACTIVE_LLM", None)
        self._write_env("CLICKY_ACTIVE_LLM", "")

    def stt_provider(self) -> str:
        # Allow explicit override via env (so users can force whisper_cpp etc.)
        forced = os.getenv("CLICKY_STT", "").strip().lower()
        if forced in ("deepgram", "openai", "whisper_cpp", "faster_whisper"):
            return forced
        if self.deepgram_api_key:
            return "deepgram"
        if self.openai_api_key:
            return "openai"
        # Prefer whisper.cpp (GPU-accelerated, same engine as Handy) when the
        # pywhispercpp package is installed; otherwise fall back to faster-whisper.
        try:
            import pywhispercpp  # noqa: F401
            return "whisper_cpp"
        except ImportError:
            return "faster_whisper"

    def tts_provider(self) -> str:
        if self.elevenlabs_api_key:
            return "elevenlabs"
        if self.openai_api_key:
            return "openai"
        return "edge_tts"

    def search_provider(self) -> str:
        if self.tavily_api_key:
            return "tavily"
        return "duckduckgo"

    def describe(self) -> dict:
        """Human-readable summary of active providers for the setup panel."""
        return {
            "llm": self.llm_provider(),
            "stt": self.stt_provider(),
            "tts": self.tts_provider(),
            "search": self.search_provider(),
            "ollama_model": self.ollama_model,
            "ollama_vision_model": self.get_ollama_model("vision"),
            "ollama_text_model":   self.get_ollama_model("text"),
            "lmstudio_host": self.lmstudio_host,
            "lmstudio_model": self.lmstudio_model or "(auto — whatever's loaded)",
        }

    # ── Ollama runtime model selection ───────────────────────────────────

    def get_ollama_model(self, kind: str = "vision") -> str:
        """Return the active model for the given kind ("vision" | "text").

        Reads runtime override from CLICKY_OLLAMA_VISION_MODEL /
        CLICKY_OLLAMA_TEXT_MODEL first, then the dataclass field, then the
        legacy single-model knob.
        """
        env_key = "CLICKY_OLLAMA_VISION_MODEL" if kind == "vision" else "CLICKY_OLLAMA_TEXT_MODEL"
        runtime = os.environ.get(env_key, "").strip()
        if runtime:
            return runtime
        return self.ollama_vision_model if kind == "vision" else self.ollama_text_model

    def set_ollama_model(self, kind: str, name: str) -> None:
        """Runtime switch for vision/text Ollama model. Persists for the session."""
        if kind not in ("vision", "text"):
            return
        env_key = "CLICKY_OLLAMA_VISION_MODEL" if kind == "vision" else "CLICKY_OLLAMA_TEXT_MODEL"
        os.environ[env_key] = (name or "").strip()
        # Mirror onto the dataclass so describe() picks it up immediately
        if kind == "vision":
            self.ollama_vision_model = name
        else:
            self.ollama_text_model = name


# Singleton
cfg = Config()
