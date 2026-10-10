import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { cors } from "hono/cors";
import { randomUUID } from "node:crypto";
import { createHash } from "node:crypto";
import { generateText } from "ai";
import { createOpenRouter } from "@openrouter/ai-sdk-provider";
import "dotenv/config";
import { getCachedSummary, setCachedSummary } from "./redis.js";

const app = new Hono();

app.use("*", cors());

const openrouter = createOpenRouter({
  apiKey: process.env.OPENROUTER_API_KEY,
});

// NOTE: "openrouter/free" is a catch-all router — it can land on reasoning
// models (empty text) or non-chat models like safety classifiers
// ("User Safety: safe"). A pinned free instruct model is reliable.
// Override with OPENROUTER_MODEL if needed.
const MODEL = process.env.OPENROUTER_MODEL ?? "nvidia/nemotron-3-super-120b-a12b:free";

// Aswin's SerpAPI: POST http://localhost:8009/submit with the summarized
// text. MOCKED for now (5s delay, random id) until the real API is ready.
// Real call will look like:
//   const res = await fetch("http://localhost:8009/submit", {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify({ text: summary }),
//   });
//   const { id } = await res.json();
//   return id;
async function submitSummary(summary: string): Promise<string> {
  void summary;
  await new Promise((resolve) => setTimeout(resolve, 5000));
  return randomUUID();
}

app.post("/", async (c) => {
  let body: unknown;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "Invalid JSON body. Expected { \"text\": string }." }, 400);
  }

  const text = (body as { text?: unknown } | null)?.text;

  if (typeof text !== "string" || text.trim().length === 0) {
    return c.json({ error: "Missing required field: \"text\" must be a non-empty string." }, 400);
  }

  if (!process.env.OPENROUTER_API_KEY) {
    return c.json({ error: "Server misconfigured: OPENROUTER_API_KEY is not set." }, 500);
  }

  try {
    const input = text.trim();
    const cacheKey = `summary:${createHash("sha256").update(input).digest("hex")}`;

    let summary = await getCachedSummary(cacheKey);
    if (summary) {
      console.log("Summary cache HIT");
    } else {
      console.log("Summary cache MISS");
      const result = await generateText({
        model: openrouter.chat(MODEL),
        system:
          "You compress a news article into a single short search query. " +
          "Describe the exact incident (who, what, where, when) in 1 line, under 20 words, " +
          "using concrete nouns and plain keywords someone would type into Google Search to find related articles. " +
          "No quotes, no punctuation tricks, no explanation, no extra text. Output only the query.",
        prompt: input,
        // Free-router models may spend tokens on hidden reasoning before
        // answering; leave enough budget so the actual summary is emitted.
        maxOutputTokens: 512,
        temperature: 0.2,
      });
      summary = result.text.trim();

      if (summary.length === 0) {
        console.error("Summarization returned empty text.");
        return c.json({ error: "Model returned an empty summary, please retry." }, 502);
      }

      await setCachedSummary(cacheKey, summary);
    }

    const id = await submitSummary(summary);

    return c.json({ id });
  } catch (err) {
    console.error("Summarization failed:", err);
    return c.json({ error: "Failed to summarize text." }, 502);
  }
});

serve(
  {
    fetch: app.fetch,
    port: 8008,
  },
  (info) => {
    console.log(`Server is running on http://localhost:${info.port}`);
  },
);
