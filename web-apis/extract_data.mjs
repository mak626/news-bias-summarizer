import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const web = path.resolve(here, "../web/dist");

function literal(source, declaration) {
  const marker = `const ${declaration}=`;
  const start = source.indexOf(marker);
  if (start < 0) throw new Error(`Could not find ${declaration}`);
  const open = source.indexOf("[", start + marker.length);
  let depth = 0;
  let quote = null;
  let escaped = false;
  for (let i = open; i < source.length; i += 1) {
    const c = source[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (c === "\\") escaped = true;
      else if (c === quote) quote = null;
      continue;
    }
    if (c === "'" || c === '"' || c === "`") { quote = c; continue; }
    if (c === "[") depth += 1;
    if (c === "]" && --depth === 0) return source.slice(open, i + 1);
  }
  throw new Error(`Could not parse ${declaration}`);
}

const indiaContext = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(web, "news-data.js"), "utf8"), indiaContext);

const appSource = fs.readFileSync(path.join(web, "app.js"), "utf8");
const dimensions = vm.runInNewContext(`(${literal(appSource, "dimensions")})`);
const media = vm.runInNewContext(`(${literal(appSource, "media")})`);
const stories = vm.runInNewContext(`(${literal(appSource, "stories")})`);

const visualsContext = {};
const visualsSource = fs.readFileSync(path.join(web, "story-visuals.js"), "utf8")
  .replace(/const storyVisuals\s*=\s*/, "storyVisuals = ");
vm.runInNewContext(visualsSource, visualsContext);

const output = JSON.stringify({
  edition: indiaContext.window.indiaEdition,
  lab: { dimensions, media, stories, visuals: visualsContext.storyVisuals }
});

if (process.argv[2]) fs.writeFileSync(process.argv[2], output);
else process.stdout.write(output);
