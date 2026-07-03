"""Piper local text-to-speech provider tool."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


class PiperTTS(BaseTool):
    name = "piper_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "piper"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL

    dependencies = ["cmd:piper"]
    install_instructions = (
        "Install Piper TTS:\n"
        "  pip install piper-tts\n"
        "Or download from https://github.com/rhasspy/piper/releases\n"
        "Then download a voice model:\n"
        "  piper --download-dir ~/.piper/models --model en_US-lessac-medium"
    )
    agent_skills = ["text-to-speech"]

    capabilities = [
        "text_to_speech",
        "offline_generation",
    ]
    supports = {
        "voice_cloning": False,
        "multilingual": False,
        "offline": True,
        "native_audio": True,
    }
    best_for = [
        "offline narration fallback",
        "privacy-sensitive local-only workflows",
    ]
    not_good_for = [
        "best-in-class expressive voice quality",
        "voice clone matching",
    ]

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "model": {
                "type": "string",
                "default": "en_US-lessac-medium",
            },
            "speaker_id": {
                "type": "integer",
                "default": 0,
            },
            "length_scale": {
                "type": "number",
                "default": 1.0,
            },
            "sentence_silence": {
                "type": "number",
                "default": 0.3,
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=2, ram_mb=512, vram_mb=0, disk_mb=200, network_required=False
    )
    retry_policy = RetryPolicy(max_retries=1, retryable_errors=[])
    idempotency_key_fields = ["text", "model", "speaker_id", "length_scale"]
    side_effects = ["writes audio file to output_path"]
    user_visible_verification = ["Listen to generated audio for intelligibility"]

    def get_status(self) -> ToolStatus:
        if shutil.which("piper") or self._find_piper():
            return ToolStatus.AVAILABLE
        try:
            import piper  # noqa: F401
            return ToolStatus.AVAILABLE
        except ImportError:
            return ToolStatus.UNAVAILABLE

    @staticmethod
    def _find_piper() -> str | None:
        """Locate the piper executable, including the venv Scripts dir on Windows.

        The pip-installed console script lives in ``.venv/Scripts`` which is often
        absent from PATH on Windows. Prepend it so the tool is usable without
        manual PATH changes.
        """
        exe = shutil.which("piper")
        if exe:
            return exe
        venv_scripts = Path(".venv") / "Scripts" / "piper"
        if venv_scripts.with_suffix(".exe").exists() or venv_scripts.exists():
            scripts_dir = str(venv_scripts.parent.resolve())
            os.environ["PATH"] = scripts_dir + os.pathsep + os.environ.get("PATH", "")
            return shutil.which("piper")
        return None

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(success=False, error="Piper TTS not available. " + self.install_instructions)

        start = time.time()
        try:
            result = self._generate(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"Local TTS generation failed: {exc}")

        result.duration_seconds = round(time.time() - start, 2)
        return result

    @staticmethod
    def _resolve_model(model: str) -> str:
        """Resolve a Piper voice to an absolute .onnx path.

        Piper 1.x requires a file path (not a bare voice name). Accept either an
        existing .onnx path or a voice name (e.g. ``zh_CN-huayan-medium``) which is
        looked up under PIPER_DATA_DIR / ``~/.piper/models``.
        """
        path = Path(model)
        if path.suffix == ".onnx" and path.exists():
            return str(path.resolve())

        data_dir = Path(
            os.environ.get("PIPER_DATA_DIR", Path.home() / ".piper" / "models")
        )
        candidate = data_dir / (f"{model}.onnx" if not model.endswith(".onnx") else model)
        if candidate.exists():
            return str(candidate.resolve())

        # Fall back to the raw value; Piper will report the missing file.
        return model

    @staticmethod
    def _utf8_env() -> dict[str, str]:
        """Spawn env that forces UTF-8 stdin/stdout.

        On a Chinese Windows shell the parent's locale is cp936 (GBK), so text
        piped to Piper's stdin is mis-decoded into lone surrogates
        (``\\udc80``), which espeak-ng cannot re-encode. PYTHONUTF8=1 makes the
        child interpret stdin as UTF-8.
        """
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    def _generate(self, inputs: dict[str, Any]) -> ToolResult:
        output_path = Path(inputs.get("output_path", "tts_output.wav"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        model_path = self._resolve_model(inputs.get("model", "en_US-lessac-medium"))

        # Pass text as explicit UTF-8 bytes (not text=True) so the parent's
        # locale (e.g. cp936) never re-encodes the input.
        proc = subprocess.run(
            [
                "piper",
                "--model", model_path,
                "--speaker", str(inputs.get("speaker_id", 0)),
                "--length-scale", str(inputs.get("length_scale", 1.0)),
                "--sentence-silence", str(inputs.get("sentence_silence", 0.3)),
                "--output_file", str(output_path),
            ],
            input=inputs["text"].encode("utf-8"),
            capture_output=True,
            env=self._utf8_env(),
            timeout=300,
        )

        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace")
            return ToolResult(success=False, error=f"Piper failed (exit {proc.returncode}): {stderr}")
        if not output_path.exists():
            stderr = proc.stderr.decode("utf-8", errors="replace")
            return ToolResult(success=False, error=f"Piper output file missing: {output_path}; stderr: {stderr}")

        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "model": model_path,
                "speaker_id": inputs.get("speaker_id", 0),
                "text_length": len(inputs["text"]),
                "output": str(output_path),
                "format": "wav",
            },
            artifacts=[str(output_path)],
            model=model_path,
        )
