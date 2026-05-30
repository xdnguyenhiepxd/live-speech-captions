import configparser
import os

class Config:
    """Centralized configuration loaded from config.ini"""
    
    def __init__(self, config_path=None):
        if config_path is None:
            # Look for config.ini in the same directory as this script
            config_path = os.path.join(os.path.dirname(__file__), "config.ini")
        
        self.config = configparser.ConfigParser()
        
        if os.path.exists(config_path):
            self.config.read(config_path)
            print(f"[Config] Loaded from: {config_path}")
        else:
            print(f"[Config] Warning: {config_path} not found, using defaults/env vars")
        
        # Cloud STT API (OpenAI / Gemini) — khi Whisper local quá chậm
        self.openai_api_key = (
            os.getenv("OPENAI_API_KEY")
            or self._get("api", "openai_api_key")
            or self._get("api", "api_key", "")
        )
        self.openai_base_url = (
            os.getenv("OPENAI_BASE_URL")
            or self._get("api", "openai_base_url")
            or self._get("api", "base_url", "")
        ) or None
        self.openai_stt_model = self._get(
            "api", "openai_stt_model", "gpt-4o-mini-transcribe"
        )
        self.gemini_api_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or self._get("api", "gemini_api_key", "")
        )
        self.gemini_model = self._get("api", "gemini_model", "gemini-2.5-flash")
        self.deepgram_api_key = (
            os.getenv("DEEPGRAM_API_KEY")
            or self._get("api", "deepgram_api_key", "")
        )
        self.deepgram_model = self._get("api", "deepgram_model", "nova-3")
        self.deepgram_language = self._get("api", "deepgram_language", "en")
        self.realtime_mode = (
            self._get("transcription", "realtime_mode", "true").lower() == "true"
        )
        self.cloud_partial = self._get("transcription", "cloud_partial", "false").lower() == "true"
        # Free Gemini ≈ 5 RPM → tối thiểu ~13s giữa 2 lần gọi API
        self.cloud_min_request_interval = self._getfloat(
            "transcription", "cloud_min_request_interval", 13.0
        )
        
        # Transcription settings
        self.asr_backend = self._get("transcription", "backend", "whisper").lower()
        self.whisper_model = self._get("transcription", "whisper_model", "base")
        self.funasr_model = self._get("transcription", "funasr_model", "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch")
        self.whisper_device = self._get("transcription", "device", "cpu")
        self.whisper_compute_type = self._get("transcription", "compute_type", "int8")
        self.source_language = self._get("transcription", "source_language", "auto")
        if self.source_language == "auto":
            self.source_language = None  # Whisper uses None for auto-detect
        self.transcription_workers = self._getint("transcription", "transcription_workers", 2)
        self.whisper_beam_size = self._getint("transcription", "beam_size", 1)
        self.cpu_threads = self._getint("transcription", "cpu_threads", 0)
        self.vad_filter = self._get("transcription", "vad_filter", "false").lower() == "true"
        self.max_transcribe_seconds = self._getfloat("transcription", "max_transcribe_seconds", 4.0)
        self.log_latency = self._get("transcription", "log_latency", "true").lower() == "true"
        self.use_context_prompt = self._get(
            "transcription", "use_context_prompt", "false"
        ).lower() == "true"
        
        # Audio settings
        self.sample_rate = self._getint("audio", "sample_rate", 16000)
        self.silence_threshold = self._getfloat("audio", "silence_threshold", 0.01)
        self.silence_duration = self._getfloat("audio", "silence_duration", 1.0)
        self.chunk_duration = self._getfloat("audio", "chunk_duration", 0.5)
        
        # Device index: 'auto' = BlackHole (macOS) / VB-CABLE (Windows), or numeric index
        device_idx_str = self._get("audio", "device_index", "auto")
        if device_idx_str.isdigit():
            self.device_index = int(device_idx_str)
        elif device_idx_str.lower() in ("auto", ""):
            self.device_index = self._find_virtual_input_device()
        else:
            self.device_index = None
            
        # Max phrase duration - force processing after N seconds
        self.max_phrase_duration = self._getfloat("audio", "max_phrase_duration", 5.0)
        
        # Streaming mode settings
        self.streaming_mode = self._get("audio", "streaming_mode", "false").lower() == "true"
        self.streaming_interval = self._getfloat("audio", "streaming_interval", 1.5)
        self.streaming_step_size = self._getfloat("audio", "streaming_step_size", 0.2)
        self.update_interval = self._getfloat("audio", "update_interval", 0.5)
        self.streaming_overlap = self._getfloat("audio", "streaming_overlap", 0.3)

        # Realtime tuning
        self.partial_updates = self._get("audio", "partial_updates", "true").lower() == "true"
        self.reader_partial_updates = self._get("audio", "reader_partial_updates", "true").lower() == "true"
        self.reader_update_interval = self._getfloat("audio", "reader_update_interval", 0.9)
        self.partial_window_seconds = self._getfloat("audio", "partial_window_seconds", 4.0)
        self.min_phrase_duration = self._getfloat("audio", "min_phrase_duration", 1.0)
        self.standard_cut_duration = self._getfloat("audio", "standard_cut_duration", 1.2)
        self.soft_cut_at_duration = self._getfloat("audio", "soft_cut_at_duration", 4.0)
        
        # Display settings
        self.display_duration = self._getfloat("display", "display_duration", 3.0)
        self.window_width = self._getint("display", "window_width", 800)
        self.window_height = self._getint("display", "window_height", 120)
        self.reader_font_size = self._getint("display", "reader_font_size", 32)
        self.reader_window_width = self._getint("display", "reader_window_width", 900)
        self.reader_keep_lines = self._getint("display", "reader_keep_lines", 30)
    
    def _get(self, section, key, fallback=""):
        try:
            value = self.config.get(section, key)
            return value if value else fallback
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def _getint(self, section, key, fallback=0):
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def _getfloat(self, section, key, fallback=0.0):
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def _find_virtual_input_device(self):
        """Auto-detect virtual loopback input (BlackHole, VB-CABLE, …)."""
        keywords = (
            "blackhole",
            "vb-audio",
            "vb audio",
            "cable output",
            "voicemeeter",
            "virtual cable",
        )
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            for i, d in enumerate(devices):
                if d["max_input_channels"] <= 0:
                    continue
                name = d["name"].lower()
                if any(k in name for k in keywords):
                    print(f"[Config] Auto-detected capture device: [{i}] {d['name']}")
                    return i
            print("[Config] No virtual capture device found, using default input")
            return None
        except Exception as e:
            print(f"[Config] Error detecting audio devices: {e}")
            return None
    
    def is_streaming_asr(self):
        return self.asr_backend == "deepgram"

    def is_cloud_asr(self):
        return self.asr_backend in ("openai", "gemini", "deepgram")

    def is_batch_cloud_asr(self):
        return self.asr_backend in ("openai", "gemini")

    def print_config(self):
        """Print current configuration for debugging"""
        print("[Config] Current settings:")
        if self.is_cloud_asr():
            if self.is_streaming_asr():
                masked = self._mask_key(self.deepgram_api_key)
                print(f"  Streaming ASR: deepgram | key={masked} | model={self.deepgram_model}")
            else:
                key = (
                    self.openai_api_key
                    if self.asr_backend == "openai"
                    else self.gemini_api_key
                )
                masked = self._mask_key(key)
                print(f"  Cloud ASR: {self.asr_backend} | key={masked}")
                if self.asr_backend == "openai":
                    print(f"  OpenAI STT model: {self.openai_stt_model}")
                else:
                    print(f"  Gemini model: {self.gemini_model}")
                print(
                    f"  Cloud min interval: {self.cloud_min_request_interval}s "
                    f"(tránh 429 RPM)"
                )
        if self.realtime_mode:
            print("  Realtime mode: ON")
        print(f"  ASR Backend: {self.asr_backend}")
        print(f"  Whisper Model: {self.whisper_model}")
        print(
            f"  Beam / CPU threads / VAD: {self.whisper_beam_size} / "
            f"{self.cpu_threads or 'auto'} / {self.vad_filter}"
        )
        print(f"  Max transcribe audio: {self.max_transcribe_seconds}s | log_latency: {self.log_latency}")
        print(f"  Sample Rate: {self.sample_rate}")
        print(f"  Partial updates: {self.partial_updates}")
        print(f"  Max phrase: {self.max_phrase_duration}s")

    @staticmethod
    def _mask_key(key: str) -> str:
        key = (key or "").strip()
        if not key:
            return "(chưa có)"
        if len(key) <= 8:
            return "***"
        return f"{key[:4]}…{key[-4:]}"

# Global config instance
config = Config()


def reload_config(config_path=None):
    """Reload config.ini (sau khi lưu từ Dashboard)."""
    global config
    config = Config(config_path)
    return config
