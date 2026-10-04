# Two-minute demo video

Screen-record the live site (https://derka1385.github.io/APORIA/) at 1440 × 900. About 290 spoken words. Numbers
are from the README results block; read them from the page, not from memory.

| Time | Screen | Say |
|---|---|---|
| 0:00–0:15 | Site hero, the particle object replaying a run | "Swarms of AI agents built on one model tend to think alike: same moves, same objections, same answer. APORIA asks whether you can change *how* an agent thinks, and measure it." |
| 0:15–0:35 | Scroll to the research question, then the two fingerprint panels | "Five reasoners, one LLM, one question. They share an engine with explicit cognitive functions: metacognition, curiosity, counterfactual tests, adversarial experiments, memory, a logic checker. What differs is their policy, and one dial, Δ, sets how far apart those policies are. Here is where each reasoner spent its compute. On the left, five copies of one policy. On the right, five cognitive policies." |
| 0:35–1:05 | Click "Replay a recorded run" → the lab replays the Qwen3-30B Δ 1 run | "This is a real run on Qwen3-30B on an evroc GPU. Each cluster is one reasoner's argument graph growing step by step. The skeptic raises objections and runs adversarial tests. The formalist translates the argument into logic and a truth table checks it. The explorer branches into thought experiments. Nobody is told to disagree." |
| 1:05–1:35 | Back to the site → Results: KPIs, then the Δ sweep chart | "Then we measure. As Δ goes from 0 to 1, the five reasoning paths become far less similar, the kinds of argument they build diverge, and they raise objections no other reasoner found. Persona prompts move less than policies do. And the honest part: their conclusions still converge. Architecture changed the process, not yet the answer." |
| 1:35–1:55 | Compression section | "Next, we go inside the weights. With LobBot, each profile gets its own compressed Qwen3-30B-A3B: experts pruned on that profile's own reasoning traces. The task specs are built from the recorded runs and ready to run." |
| 1:55–2:00 | Hero again | "APORIA: a lab where the way an AI thinks becomes something you can test." |

Before recording: let the hero object play one full loop (about 12 s), and open the lab replay once so the run is cached.
