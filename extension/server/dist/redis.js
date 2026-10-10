import { createClient } from "redis";
// Upstash Redis (over TLS). Configure via REDIS_URL, e.g.
//   rediss://default:<token>@<host>:6379
// If REDIS_URL is missing or Redis is unreachable, caching is skipped and
// requests fall through to the live model — Redis must never break the API.
const SUMMARY_TTL_SECONDS = 60 * 60 * 24 * 7; // 7 days
let client = null;
let connecting = null;
async function getClient() {
    if (!process.env.REDIS_URL)
        return null;
    if (client?.isOpen)
        return client;
    if (!connecting) {
        connecting = (async () => {
            const c = createClient({ url: process.env.REDIS_URL });
            c.on("error", (err) => console.error("Redis error:", err));
            await c.connect();
            client = c;
            console.log("Redis connected");
            return client;
        })().catch((err) => {
            console.error("Redis connection failed, caching disabled:", err);
            connecting = null;
            return null;
        });
    }
    return connecting;
}
export async function getCachedSummary(key) {
    const c = await getClient();
    if (!c)
        return null;
    try {
        return await c.get(key);
    }
    catch (err) {
        console.error("Redis GET failed:", err);
        return null;
    }
}
export async function setCachedSummary(key, value) {
    const c = await getClient();
    if (!c)
        return;
    try {
        await c.set(key, value, { EX: SUMMARY_TTL_SECONDS });
    }
    catch (err) {
        console.error("Redis SET failed:", err);
    }
}
