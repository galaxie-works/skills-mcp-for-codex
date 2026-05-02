---
name: "audio-drama-storyteller"
description: "Create story-first narrated audio in MP3 with text-to-speech, scene beats, character voices, ambience, and sound effect cues. Use when the user wants an audiobook-style narration, audiodrama, tele-dramaturgia, cinematic voiceover, narrated story with effects, or a spoken story saved as MP3."
---

# Audio Drama Storyteller

Use this skill when the user wants something beyond plain TTS: a story that sounds good to hear, with narrator flow, character voice choices, dramatic pacing, ambience, and sound effect moments.

This skill is a composition workflow:
- `speech` handles voice generation
- this skill handles script adaptation, beat design, voice casting, scene structure, and final render planning
- `ffmpeg` is the preferred mixer when the user wants a final MP3 with music or effects

## What this skill should produce

- a story-ready script, not raw prose dumped into TTS
- voice directions per narrator/character
- a cue sheet for ambience and effects
- one or more MP3 voice clips
- optionally a final mixed MP3

## When to use

Trigger on requests like:
- "faz um mp3 narrado"
- "quero uma historia boa de ouvir"
- "text to speech com efeitos"
- "audio drama"
- "tele-dramaturgia"
- "podcast narrativo"
- "audiobook com vozes"
- "narra isso com clima cinematografico"

## Workflow

1. Decide the output type:
   - `voice-only MP3`
   - `narrated story with scene cues`
   - `full audio drama mix`
2. Turn the source text into a listening script:
   - shorten long paragraphs
   - add pauses
   - split lines by narrator / character / scene
   - mark sound cues only where they help
3. Assign voices:
   - narrator
   - main character voices
   - optional secondary voices
4. Generate speech clips using the existing speech workflow and built-in voices only.
5. If the user wants drama, create a cue sheet with:
   - ambience
   - transitions
   - hit effects
   - intro / outro mood
6. If effects or music are available locally, mix with `ffmpeg`.
7. Save final files under a clear folder such as `output/audio-drama/`.

## Rules

- Do not dump raw long-form text into TTS without adaptation.
- Fewer, better sound cues beat constant noise.
- Keep effects behind the narration; the words must stay intelligible.
- Prefer one narrator plus one or two character voices before going too wide.
- If no sound library is available, still produce a strong `voice-only MP3`.
- Be explicit that the voice is AI-generated.

## Voice casting defaults

- Narrator: `cedar`
- Warm / intimate secondary voice: `marin`
- Use short instruction blocks with mood, pacing, pauses, and emphasis

## Output modes

### Mode 1: Voice-only

Use when the user just wants a compelling MP3 fast.

Deliver:
- adapted listening script
- voice spec
- rendered MP3

### Mode 2: Story with cues

Use when the user wants something richer but effects are not ready yet.

Deliver:
- adapted script
- cue sheet
- voice clips

### Mode 3: Full mix

Use when local ambience / SFX files exist or the user provides them.

Deliver:
- adapted script
- cue sheet
- voice clips
- final mixed MP3

## References

- Script and scene design: `references/workflow.md`
- Prompt formats and voice directions: `references/prompt-templates.md`

