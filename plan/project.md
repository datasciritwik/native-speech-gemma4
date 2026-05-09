# Extending Gemma 4 (E2B / E4B) for Audio Output: A Research & Implementation Roadmap

> **Project goal.** Gemma 4 (and its predecessor Gemma 3n) accept audio + image + video + text as input but only produce **text** as output. The objective is to extend the output modality to **speech / audio**, with the eventual aim of building a **low-latency speech-to-speech (S2S) model** suitable for real-time conversation.
>
> **Audience of this doc.** Someone with general ML background who has not yet worked on speech / audio LLMs. The doc is split into:
>   1. **Part 1 — Literature survey:** what to read, in what order, and why.
>   2. **Part 2 — Coding & implementation:** the toolchain, libraries, codebases to study, and a concrete build sequence.
>   3. **Part 3 — Key architectural decisions** that will shape both your reading and your code.
>
> Treat the suggested order as a default, not a rule. If you already know transformers and PyTorch well, skip the refresher sections.

---

## 0. Framing the problem before you start

Before reading or coding anything, be very clear in writing about three things:

1. **What "extend output modality to audio" means in practice.** There are two qualitatively different versions of this problem, and they need different literature and different code:
    - **(a) Cascaded:** keep Gemma's text output, then run a Text-To-Speech (TTS) model on top. Lower research novelty, much easier to build, but typical end-to-end latency is 800 ms–2 s and paralinguistic information (emotion, prosody, interruptions) is lost in the text bottleneck.
    - **(b) End-to-end speech-out LLM:** the LLM directly generates **discrete audio tokens** (or some other audio representation) interleaved with or instead of text tokens. This is what Moshi, GLM-4-Voice, Mini-Omni, AudioPaLM, etc. do. Latency can be ~200 ms, and you preserve non-linguistic cues. This is the harder, more interesting version, and it is what the rest of this doc assumes you ultimately want.

2. **What "low latency" means numerically.** Set an explicit target. Reasonable goalposts:
    - Cascaded baseline: ~1 s time-to-first-audio.
    - Streaming non-full-duplex (e.g. simple chunked output): 300–500 ms.
    - Full-duplex Moshi-class: 160–250 ms theoretical, ~300 ms practical on a single mid-range GPU.

3. **What success looks like for the literature survey itself.** A useful end-state: you can, in 10 minutes on a whiteboard, sketch (i) how a neural audio codec turns waveforms into discrete tokens, (ii) how an LLM is conditioned to predict those tokens, (iii) how Moshi handles two simultaneous audio streams + text, and (iv) where in that pipeline a frozen Gemma 4 backbone would slot in.

---

## Part 1 — Literature Survey

The goal is breadth-then-depth. Skim the foundational work to know the vocabulary, then deep-read the 4–6 papers that are most directly your "ancestors."

For each paper below: **(S)** = skim (1 hr), **(R)** = read carefully (3–4 hrs incl. notes), **(D)** = deep-read with code (1–3 days).

### A. Background you need before the speech literature makes sense

If any of these aren't already comfortable, fix them first — most modern speech-LLM papers assume them.

- **(R) "Attention Is All You Need"** — Vaswani et al., 2017. The transformer baseline. https://arxiv.org/abs/1706.03762
- **(S) GPT / decoder-only LM training basics.** Any tutorial; Karpathy's "Let's build GPT" video is a fast way to refresh.
- **(R) "Neural Discrete Representation Learning" (VQ-VAE)** — van den Oord et al., 2017. https://arxiv.org/abs/1711.00937 — vector quantization is the conceptual heart of every neural audio codec you'll touch.
- **(S) "wav2vec 2.0"** — Baevski et al., 2020. https://arxiv.org/abs/2006.11477 — self-supervised speech representations; useful context for "semantic" audio tokens.
- **(S) "HuBERT"** — Hsu et al., 2021. https://arxiv.org/abs/2106.07447 — same purpose as wav2vec 2.0; widely cited as a source of *semantic* speech tokens.

**Audio signal-processing primer.** You don't need to be a DSP expert, but you should be fluent with: sampling rate, framing/hopping, mel-spectrograms, what an STFT is, and what "16 kHz mono PCM" means. Half a day with the `librosa` and `torchaudio` tutorials is enough.

### B. Neural Audio Codecs — the bridge from waveform to tokens

This is the single most important sub-area for your project. A speech-LLM is, mechanically, a language model over codec tokens. Understand at least one codec **deeply**.

- **(R) SoundStream** — Zeghidour et al., 2021. https://arxiv.org/abs/2107.03312 — introduces the encoder-RVQ-decoder pattern that everything else uses.
- **(D) EnCodec** — Défossez et al., "High Fidelity Neural Audio Compression," 2022. https://arxiv.org/abs/2210.13438 — Meta's codec; the de facto baseline. Read the paper, then run the open-source `encodec` package on a few of your own audio files. You should be able to encode → look at the integer token stream → decode and listen.
- **(R) DAC (Descript Audio Codec)** — Kumar et al., NeurIPS 2023. https://arxiv.org/abs/2306.06546 — improved fidelity at lower bitrates.
- **(D) Mimi (used in Moshi)** — Défossez et al., 2024 (see Moshi paper §3). Mimi is **streaming** (12.5 Hz frame rate, ~80 ms per frame), and that streaming property is what makes 200 ms full-duplex possible. If you intend to do real-time S2S, you must understand Mimi specifically. https://github.com/kyutai-labs/moshi
- **(S) Low-frame-rate codecs** — e.g. NVIDIA's "Low Frame-rate Speech Codec," 2024 (https://arxiv.org/abs/2409.12117) and U-Codec, 2025 (https://arxiv.org/abs/2510.16718). These let an LLM produce 1 second of audio in far fewer tokens, which directly lowers latency and training cost.

**What you want to come out understanding:** RVQ (residual vector quantization), why codecs use **multiple parallel codebooks** per frame, the trade-off between frame rate, bitrate, and reconstruction quality, and the difference between **semantic tokens** (HuBERT-style, good for content) and **acoustic tokens** (EnCodec/Mimi-style, good for fidelity).

### C. Audio / Speech LLMs — generating tokens with a transformer

These papers establish "an LLM can autoregressively generate discrete audio tokens." Read at least three.

- **(R) AudioLM** — Borsos et al., 2022. https://arxiv.org/abs/2209.03143 — the seminal "language model over audio tokens" paper; introduces the semantic→coarse→fine token hierarchy.
- **(D) VALL-E** — Wang et al., 2023. https://arxiv.org/abs/2301.02111 — first widely-known neural codec language model for zero-shot TTS. The architecture (autoregressive coarse model + non-autoregressive fine model on EnCodec tokens) is a template you'll see reused everywhere.
- **(S) VALL-E 2** — 2024. Follow-up; main interest is the robustness fixes.
- **(R) AudioPaLM** — Rubenstein et al., 2023. https://arxiv.org/abs/2306.12925 — Google's combined speech+text LLM with a unified vocabulary. Particularly relevant because PaLM is architecturally close to Gemma.
- **(R) SpeechGPT** — Zhang et al., 2023. https://arxiv.org/abs/2305.11000 — extends LLaMA with discrete speech tokens; structurally very similar to what you want to do with Gemma.
- **(S) SPIRIT-LM** — Nguyen et al., 2024. https://arxiv.org/abs/2402.05755 — interleaves speech and text tokens in a single stream.

### D. Real-time / streaming / full-duplex speech-to-speech (your direct ancestors)

This is the cluster you should know best. **Moshi is the single most important paper in this whole doc** for your project — read it in full, multiple times, and read the open-source code.

- **(D) Moshi** — Défossez et al., 2024. https://arxiv.org/abs/2410.00037. Code: https://github.com/kyutai-labs/moshi. Key contributions to understand:
    - **Mimi codec** (streaming, low frame rate).
    - **Multi-stream architecture:** user audio stream + Moshi audio stream + text "inner monologue" stream are predicted in parallel — turns are not segmented.
    - **Inner Monologue:** time-aligned text tokens predicted as a *prefix* to audio tokens, giving the model a textual scratchpad before speaking. Major quality win.
    - **Depth-Transformer + Temporal-Transformer split:** a small transformer handles inter-codebook dependencies at one timestep; a large 7B transformer handles temporal dependencies across timesteps. This is what makes a 7B-parameter model viable in real time.
- **(R) GLM-4-Voice** — Zeng et al., 2024. https://arxiv.org/abs/2412.02612 — Tsinghua's end-to-end Chinese/English speech model; lower-frame-rate tokenizer; good comparison point to Moshi.
- **(R) Mini-Omni / Mini-Omni 2** — Xie et al., 2024. https://arxiv.org/abs/2408.16725 — explicitly built as an **adapter** on top of a frozen text LLM (Qwen2). This is probably the closest published architecture to what you want to do with Gemma.
- **(R) LLaMA-Omni** — Fang et al., 2024. https://arxiv.org/abs/2409.06666 — similar adapter-on-frozen-LLM strategy with a streaming decoder.
- **(S) Hibiki** — Kyutai, 2025. Streaming speech-to-speech *translation* using the Moshi multi-stream framework. https://github.com/kyutai-labs/hibiki
- **(S) Spectron, PSLM** — earlier interleaved single-stream attempts; mainly read to understand what Moshi's multi-stream design is *correcting*.

**Reading strategy for this section:** read Moshi first and let it act as the lens through which you read the others. For each subsequent paper write a one-page diff: what changed vs Moshi, what got better, what got worse.

### E. Gemma-specific

You need to know your backbone in detail.

- **(D) Gemma 3 Technical Report** — Gemma Team / DeepMind, 2025. https://arxiv.org/pdf/2503.19786 — covers the underlying architecture (local/global attention ratio, KV-cache reduction, distillation training).
- **(R) Gemma 3n developer guide / blog post.** https://developers.googleblog.com/en/introducing-gemma-3n-developer-guide/ — covers the architectural innovations that the E2B/E4B variants share with Gemma 4: **MatFormer** (nested submodels), **Per-Layer Embeddings (PLE)**, **KV Cache Sharing**, the audio encoder, and the MobileNet-v5-based vision encoder.
- **(R) Gemma 4 release notes** (April 2026). The 2B / 4B edge variants share the audio-input encoder lineage with Gemma 3n but with a ~50% smaller audio encoder and 40 ms frame duration, both relevant if you plan to keep the encoder and only add a decoder side.
- **(S) Gemini Nano** material — only because it shares architectural DNA with Gemma 3n / 4. Not strictly required.

**What you must internalize:** how Gemma's audio *encoder* currently produces representations that get fused with the language model's residual stream. To extend to audio *output*, you need a symmetric path on the way out — a "speech head" or auxiliary decoder. The MatFormer story matters because if you train an extension on E4B, you may be able to inherit it on the nested E2B with little extra work.

### F. Training techniques you'll lean on

You will not train Gemma from scratch. You will be doing some flavour of **continued pre-training + fine-tuning**, almost certainly with parameter-efficient methods.

- **(R) LoRA** — Hu et al., 2021. https://arxiv.org/abs/2106.09685
- **(S) QLoRA** — Dettmers et al., 2023. https://arxiv.org/abs/2305.14314 — for fitting training into single-GPU memory.
- **(S) Adapters** — Houlsby et al., 2019. https://arxiv.org/abs/1902.00751 — conceptually older than LoRA but cleaner mental model for "added module on a frozen backbone."
- **(R) Knowledge distillation basics** — Hinton et al., 2015. https://arxiv.org/abs/1503.02531 — useful if you later want to compress the speech-extended model.
- **(R) "Balancing Speech Understanding and Generation Using Continual Pre-training for Codec-based Speech LLM"** — 2025. https://arxiv.org/abs/2502.16897 — directly studies the catastrophic-forgetting problem you'll face when adding speech generation to a model that was only trained for understanding.
- **(S) Curriculum learning for speech LLMs** — survey or recent paper of your choice. The standard recipe: ASR → TTS on text+speech → speech-to-speech, in increasing difficulty.

### G. Evaluation

Decide your metrics before you write training code.

- **WER (Word Error Rate)** for any speech you generate — transcribe with Whisper-large-v3 and compare to the ground-truth transcript.
- **Speaker similarity (SECS)** if you care about preserving voice identity — cosine similarity of WavLM/ECAPA-TDNN embeddings.
- **MOS / UTMOS** for naturalness. UTMOS is an automated proxy for human MOS and is what most recent papers report.
- **Latency benchmarks:** time-to-first-audio-frame (TTFAF), real-time factor (RTF). Define and measure these from day one.
- **For full-duplex models:** turn-taking quality, interruption handling, false barge-in rate. Moshi's evaluation section is a good template.

### H. Datasets you should know about

You'll need at least one ASR-style dataset and one TTS-style dataset; ideally a conversational dataset.

- **LibriSpeech / LibriLight** — read English audiobooks, 1 k / 60 k hours.
- **GigaSpeech, People's Speech** — large, more diverse English speech corpora.
- **Common Voice (Mozilla)** — multilingual, useful for the 140-language Gemma story.
- **Emilia** — large-scale, diverse, multi-speaker. Increasingly the default for modern TTS / speech-LLM work. https://emilia-dataset.github.io/Emilia-Demo-Page/
- **Spotify Podcasts dataset, Fisher** — conversational, *not* read; closer to what you actually want for full-duplex training.
- **Synthesized parallel data:** for early bring-up, use a strong off-the-shelf TTS to generate (text, audio) pairs from a text dataset you trust. Be aware of the bias this introduces.

### Suggested reading order (4–6 weeks, ~10 hrs/week)

| Week | Read | Outcome |
|------|------|---------|
| 1 | A (refresher), B (SoundStream + EnCodec deep) | You can encode/decode audio with EnCodec and explain RVQ. |
| 2 | B (Mimi + DAC), C (AudioLM, VALL-E) | You can draw the "audio tokens go into a transformer" pipeline. |
| 3 | C (AudioPaLM, SpeechGPT), E (Gemma 3 + 3n) | You understand both halves: speech-token LMs and Gemma. |
| 4 | D (Moshi deep, Mini-Omni, LLaMA-Omni) | You can articulate the multi-stream / inner-monologue design. |
| 5 | F (LoRA, continual pre-training paper), G (metrics) | You have a training recipe and metrics in mind. |
| 6 | Re-read Moshi + Mini-Omni alongside their code; write a 5-page design doc for *your* model. | Concrete architectural plan. |

**Take notes per paper using a fixed template:** problem, key idea in one sentence, exact loss function, training data, ablations that matter, what would change if applied to Gemma. After 15 papers this template will start saving you serious time when you need to look something up.

---

## Part 2 — Coding & Implementation Skills

This part is sequenced so each phase builds the skills the next one assumes. Don't skip Phase A even if it feels basic — the bugs you hit later (NaN losses, OOMs, slow dataloaders) will all be in this layer.

### Phase A — Foundational toolchain (1–2 weeks)

If you've used these casually, that isn't enough. Get fluent.

- **PyTorch, advanced.** Custom `nn.Module`s, forward/backward hooks, `register_buffer` vs `register_parameter`, `torch.compile`, mixed precision (`torch.amp`), gradient checkpointing, `nn.functional` vs module versions. Recommended: re-implement a small transformer from scratch following Karpathy's nanoGPT. ~3 days.
- **Hugging Face stack.** `transformers` (especially `AutoModelForCausalLM`, `GenerationConfig`, custom `forward`), `datasets` (streaming + `map`), `accelerate` (multi-GPU, mixed precision), `peft` (LoRA / QLoRA). https://huggingface.co/docs
- **Weights & Biases** or similar for experiment tracking. Pick one, learn it once, use it everywhere.
- **Reading other people's training scripts.** Don't write your own training loop until you've read at least three open-source ones (HF examples, nanoGPT, Mini-Omni). The patterns are remarkably standardized.

### Phase B — Audio-specific tooling (1–2 weeks)

- **`torchaudio` and `librosa`.** Loading WAVs at the right sample rate, resampling, framing, mel-spectrograms.
- **`soundfile`, `pydub`** for I/O quirks.
- **EnCodec** (`pip install encodec`). Encode a 10-second clip, look at the integer codes, decode, listen. Then do the same with **Mimi** from the `moshi` package.
- **Whisper.** You'll use it both as an evaluator (transcribe generated speech, compute WER) and possibly as a teacher / data filter.
- **Streaming patterns.** Read the Mimi streaming code in the `moshi` repo. Understand the difference between offline encode (you have the whole waveform) and streaming encode (audio comes in 80 ms chunks and you must produce tokens with bounded latency).

### Phase C — Distributed / efficient training (1 week, mostly reading)

You'll likely train on a single 8×A100 or 8×H100 node, or rented equivalents.

- **DeepSpeed ZeRO** stages 1–3, or **PyTorch FSDP**. Pick one.
- **bf16 vs fp16** — bf16 is the safe default on Ampere+.
- **Gradient checkpointing** — costs ~30% throughput, halves activation memory.
- **Flash-Attention 2 / 3** — basically required for long sequences.
- **`accelerate launch`** as the simplest entry point.

You don't need to be an expert in distributed systems; you need to be able to copy a known-good config, change the model, and have it not OOM.

### Phase D — Codebases to read carefully (1–2 weeks)

Reading a working repo for an architecture you understand on paper is where everything finally clicks. In rough priority order:

1. **`kyutai-labs/moshi`** (https://github.com/kyutai-labs/moshi). Read `moshi/models/lm.py` and the Mimi streaming code. Spend a day getting Moshi to run inference locally. **This is the most useful single repo for your project.**
2. **`google-deepmind/gemma`** and Gemma 3n / 4 in HuggingFace `transformers`. Find the audio encoder and trace how its outputs reach the LM. You will be inserting a symmetric path on the output side.
3. **Mini-Omni** (https://github.com/gpt-omni/mini-omni). Smaller and more readable than Moshi; the "adapter on a frozen text LLM" pattern is exactly what you'll prototype first.
4. **GLM-4-Voice** (https://github.com/THUDM/GLM-4-Voice) — alternative point of comparison.
5. **EnCodec / DAC reference implementations** — for codec internals.

For each, do this: clone, run inference, set a breakpoint at the model's `forward`, run one example, walk the call stack, and write down the tensor shapes at each step. This sounds tedious. It's the highest-ROI activity in this whole project.

### Phase E — Build sequence (the actual work)

A staged plan from "Gemma running on my machine" to "speech-to-speech prototype." Timeboxes are aggressive; double them if this is part-time.

#### Milestone 1 — Run Gemma 4 / 3n inference locally (week 1)
- Get E2B running on a single GPU with the HuggingFace `transformers` integration.
- Feed it text → text. Feed it an audio file → text (transcription). Feed it an image → text.
- Measure throughput (tokens/sec) and time-to-first-token. Record baseline numbers.

#### Milestone 2 — Reproduce a tiny TTS (weeks 2–3)
- Pick a small subset of LibriTTS or LJSpeech.
- Encode all audio with **EnCodec** (or Mimi). Now you have (text, audio-token-sequence) pairs.
- Train a small (~125M parameter) decoder-only transformer from scratch on `text → audio tokens`.
- Decode the predicted tokens back to waveform with the codec's decoder. Listen.
- This is the "I have built a neural-codec language model" milestone. Skipping it is tempting and a mistake.

#### Milestone 3 — Speech head on a *frozen* Gemma (weeks 4–6)
- Freeze Gemma 4 E2B.
- Add a small "speech head": a few transformer layers + projection that, given Gemma's last-layer hidden states, predict EnCodec/Mimi tokens.
- Train the head only on a (text, audio) dataset.
- This is your **cascaded-but-internal** baseline: text comes from Gemma, audio tokens come from a head conditioned on Gemma's hidden states. Latency target: TTFAF < 500 ms on a single GPU.
- This corresponds closely to the Mini-Omni / LLaMA-Omni recipe.

#### Milestone 4 — Joint generation: audio tokens **interleaved** with text (weeks 7–10)
- Now allow Gemma to predict audio tokens *itself* via LoRA on the LM, plus the speech head.
- Use Moshi-style **inner monologue**: text token first, then audio tokens for the corresponding frame.
- Train on a small (~hundreds of hours) curated dataset.
- You are now training a real (small) speech-out LLM. Expect this to take many iterations to debug.

#### Milestone 5 — Streaming inference (weeks 11–12)
- Replace offline codec with streaming Mimi.
- Implement chunked generation: produce audio tokens in groups of N, decode immediately, play out.
- Measure TTFAF and steady-state latency.

#### Milestone 6 — Full-duplex, multi-stream (months 4–6, optional and hard)
- Add a parallel stream for **user audio**. Now Gemma is consuming user audio tokens and producing its own audio tokens at the same time.
- This is where you genuinely reproduce Moshi-style behavior. Expect significant data and compute requirements; this is the boundary between "respectable extension project" and "research contribution."

### Phase F — Hardware & infra realities

- **Inference for E2B/E4B** runs on a single consumer GPU (16–24 GB VRAM with quantization).
- **Training (LoRA only):** 1× A100 40GB or 2× 24GB consumer GPUs is enough for Milestones 3 and arguably 4 with small batch sizes and gradient accumulation.
- **Training the speech head + full LoRA on Gemma E4B:** plan for 4–8× A100 80GB or H100 for Milestone 4.
- **Data preprocessing is its own project.** Budget at least as much storage as your raw audio takes (codec tokens are small but you'll keep both). Cache aggressively.
- **Where to get GPUs:** Lambda, RunPod, Vast.ai for spot pricing; HuggingFace and Modal for managed; your university cluster if you have one. Always benchmark on the exact GPU you'll train on; A100 → H100 → consumer-RTX behavior differs enough to matter.

---

## Part 3 — The architectural decisions that connect Parts 1 and 2

These are the choices you will be implicitly making with each milestone. Make them explicitly.

1. **Cascaded vs end-to-end vs hybrid.** Cascaded (text out → external TTS) is a sensible *baseline* but not the project. Plan to land somewhere on the hybrid spectrum: Gemma still produces text internally (its inner monologue), and audio tokens are produced jointly or by a tightly-coupled head.

2. **Discrete tokens vs continuous representations.** The whole literature is converging on discrete tokens for speech-LLMs (it matches the LM training objective, gives you sampling, scales). Continuous mel-spectrogram regression is older. Use discrete unless you have a strong reason not to.

3. **Single-stream interleaved vs multi-stream parallel.** Single-stream (e.g. SPIRIT-LM, SpeechGPT) is simpler to implement; multi-stream (Moshi) handles overlap and interruption and is the right answer for full-duplex. Start single-stream, plan for multi-stream later.

4. **Train from scratch vs adapter on frozen Gemma.** Adapter (LoRA + speech head) on frozen Gemma is far cheaper, preserves the language quality you're getting Gemma for in the first place, and is well-supported by `peft`. Strongly recommended unless you have strong reasons and lots of GPUs.

5. **Codec choice.** EnCodec is the easy default for offline experiments (Milestones 2–3). **Switch to Mimi for Milestone 5+** because of streaming and the lower frame rate. You will at some point regret writing too much codec-specific code — abstract the codec behind a thin interface from day one.

6. **Inner-monologue or not.** Moshi's evidence is strong: predicting time-aligned text *as a prefix* to audio tokens substantially improves linguistic quality and gives you streaming ASR/TTS for free. The cost is more complex training data alignment. Plan for inner-monologue from Milestone 4 onwards.

7. **Number of codebooks the LM predicts.** RVQ codecs have N codebooks per frame (typically 8). Predicting all N autoregressively per frame multiplies your sequence length by N. The Moshi solution — small "Depth Transformer" for inter-codebook, large "Temporal Transformer" for inter-frame — is essentially the only way to make this fast. Read this part of the Moshi paper twice.

---

## Suggested overall timeline

| Phase | Duration (full-time) | Duration (10 hrs/week) | Output |
|------|---------------------|------------------------|--------|
| Lit survey weeks 1–6 | 6 weeks | 12 weeks | Annotated bibliography + 5-page design doc |
| Coding Phase A–B | 2–3 weeks | 6 weeks | Comfortable with PyTorch + audio tooling |
| Coding Phase C–D | 1–2 weeks | 4 weeks | Comfortable in Moshi / Mini-Omni codebases |
| Milestones 1–3 | 6 weeks | 12 weeks | Frozen-Gemma + speech head, working TTS |
| Milestones 4–5 | 6 weeks | 14 weeks | Interleaved + streaming prototype |
| Milestone 6 (optional) | 8+ weeks | 6 months+ | Full-duplex S2S |

A realistic part-time path to a "respectable working prototype" (through Milestone 5) is **9–12 months**. A full-duplex Moshi-class system as a part-time project will take longer than a year and will need real compute access.

---

## How to use this document

1. Skim the whole thing once so you know what's in it.
2. Read Part 1 §0–§D in detail and start an annotated bibliography. Don't start coding yet.
3. After the design-doc step at the end of week 6, start Phase A code. Read in parallel.
4. Re-visit Part 3 (architectural decisions) before each milestone — your answers will shift as you learn more.
5. Keep a single markdown lab notebook with one entry per training run: hypothesis, config diff, result, what you'd try next. This is the most underrated practice in ML research.

Good luck. The most common failure mode in projects like this is to skip the literature/codec phase and start fine-tuning immediately. The second most common is to skip the small-from-scratch TTS milestone and try to bolt audio output onto a 4B model directly. Don't do either.