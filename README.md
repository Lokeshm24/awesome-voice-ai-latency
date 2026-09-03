# Real-Time Voice AI & TTS Latency Benchmark (2026)

Independent, reproducible latency and pricing benchmark for real-time streaming Text-to-Speech (TTS) APIs. Built for developers engineering conversational voice bots, WebRTC pipelines, and live phone agents.

Official full report and methodology: [https://voiceaibench.com](https://voiceaibench.com)

## Quick Summary (Time to First Byte - TTFB)

| Rank | Provider | Model | Median TTFB (ms) | Pricing / 1M chars | Real-time Streaming |
|---|---|---|---|---|---|
| 1 | Cartesia | Sonic-3 | 85ms | $20.00 | WebSocket Native |
| 2 | Deepgram | Aura-2 | 115ms | $15.00 | WebSocket Native |
| 3 | ElevenLabs | Flash v2.5 | 135ms | $25.00 | WebSocket Native |
| 4 | PlayHT | PlayDialog | 180ms | $25.00 | WebSocket |
| 5 | OpenAI | TTS-1 | 240ms | $15.00 | HTTP Chunked |

## Key Insights for Builders
- **Lowest Latency**: Cartesia Sonic-3 remains the fastest option for conversational interruptions and WebRTC integrations (~85ms).
- **Most Cost-Effective Scale**: Deepgram Aura-2 provides the lowest price per 1M characters with native streaming support.
- **Highest Audio Expressiveness**: ElevenLabs Flash v2.5 remains the benchmark for emotional inflection, voice cloning nuance, and dialect accuracy.

For detailed benchmarks, testing methodology, and raw metrics, visit [voiceaibench.com](https://voiceaibench.com).
