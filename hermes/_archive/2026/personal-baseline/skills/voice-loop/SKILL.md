---
name: voice-loop
description: Use when the user sends a voice message in Telegram (or asks for a spoken reply). Transcribes audio with Groq Whisper Turbo, generates a reply with the profile's reasoning model, and renders the reply with Google TTS. Keeps continuity with the previous voice exchange via Hermes session memory.
---

# voice-loop

When a voice message arrives on Telegram (or any voice-enabled channel), follow this loop:

## 1. Transcribe

Use Groq Whisper Turbo. Hermes' built-in voice tooling handles the audio-file plumbing; just call:

```
voice.transcribe(audio_path, model="whisper-large-v3-turbo", provider="groq")
```

If the audio is longer than 60 seconds, transcribe in chunks; preserve speaker turns if diarization is available.

## 2. Compose the reply

Read the user's transcribed text. Pull recent context with:

```
session_search.search(query=transcribed_text, window_days=14)
memory.read("MEMORY.md")
memory.read("USER.md")
```

If the user's message references something from a prior conversation, surface it explicitly in the reply ("yesterday you said you wanted to..."). This continuity is the core differentiator from a generic chatbot — never skip it.

Reply length should match the question. Voice replies are lossy on long content; if the answer is >30 seconds spoken, offer to send a text follow-up.

## 3. Render

Use Google TTS (standard voice, en-US-Neural2-D for Alex unless overridden in `USER.md`):

```
voice.synthesize(reply_text, provider="google", voice="en-US-Neural2-D")
```

Send the resulting audio to the same Telegram thread the message came from.

## 4. Persist

Write the exchange to Hermes session memory automatically (built-in). When `MEMORY.md` accumulates a useful pattern (e.g., "Alex always asks for tomorrow's priorities at 9pm"), surface that to the agent on the next turn.

## Edge cases

- **Audio is silent / unintelligible:** reply with text "I couldn't make out the audio — could you re-send or type it?"
- **STT confidence low:** include a confidence note in the reply ("did you mean \_\_\_ ?").
- **Network out:** drop to text-only with the same reply text.
- **Reduced-motion / quiet hours:** if Alex set a quiet-hours window in `USER.md`, send text-only between those hours.

## Cost discipline

Groq Whisper Turbo is ~free at this volume. Google TTS Standard is ~$4/1M chars. If voice traffic exceeds 10K characters/day for 7 consecutive days, cost-watch skill alerts; the option is to switch to local TTS (Coqui XTTS) — that decision is logged in `MEMORY.md` if it ever fires.

## Don't

- Auto-reply if the message contains an outbound-to-third-party request (e.g., "text my dad \_\_\_"). Switch to approval mode.
- Use voice for sensitive information — if the message contains anything that would trigger PII redaction, fall back to text and note why.
