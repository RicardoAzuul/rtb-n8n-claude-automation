#!/usr/bin/env python3
"""Generate the "YouTube to Discord" n8n workflow JSON.

Channels live in CHANNELS below. Discord webhook URLs are secrets and are read
from config.local.json (git-ignored; see config.example.json), so they never
end up in the repo.

Usage: python3 workflows/youtube_to_discord.py OUT.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# interest -> [(display name, handle, channel id)]
CHANNELS = {
    "Tech": [("NetworkChuck", "NetworkChuck", "UC9x0AN7BWHpCDHSm9NiJFJQ")],
    "Cooking": [
        ("Alton Brown", "AltonBrown", "UCfDNi1aEljAQ17mUrfUjkvg"),
        ("Alvin Zhou", "AlvinKZhou", "UCsdD3quGf01RWABJt8wLe9g"),
        ("Chef Jack Ovens", "ChefJackOvens", "UCqRdvREgI2qLnKtiMfswzZQ"),
        ("cuoredicioccolato", "Spectacular-cuoredicioccolato", "UCntxIE8FKow3FbWG-BCApeQ"),
        ("Internet Shaquille", "internetshaquille", "UCSuT9FSddzI6W5Bij9XwtmA"),
    ],
    "RPG": [
        ("Matthew Colville", "mcolville", "UCkVdb9Yr8fc05_VbAVfskCA"),
        ("MCDM", "helloMCDM", "UCYUOOjT0j8__NMYHijAvNzg"),
        ("Questing Beast", "QuestingBeast", "UCvYwePdbWSEwUa-Pk02u3Zw"),
    ],
    "ASMR": [
        ("SkepticalPickle ASMR", "SkepticalPickleASMR", "UCEqHu6TEeyvTCRKQNl8dmoA"),
        ("Latte ASMR", "LatteASMR", "UCQe2Y7V-C9bNMAcCJCBvzQQ"),
        ("Moonlight Cottage ASMR", "MoonlightCottageASMR", "UCftD_LCuDAwlPipnM6Uikqw"),
        ("Musing Mira ASMR", "musingmira", "UCZ4IabUhlmShkFliqWEXVWg"),
        ("Bonnadora ASMR", "bonnadorasmr", "UCKzWGSDCyb89uFiVVyCe4ww"),
    ],
}

JS = r"""
// Fetch each channel's RSS feed, return only videos not posted before.
// State (seen video IDs per channel) lives in workflow static data, which is
// only persisted for production (scheduled) executions.
const channels = __CHANNELS__;
const webhooks = __WEBHOOKS__;

const state = $getWorkflowStaticData('global');
state.seen = state.seen || {};

const decode = (s) => s
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
  .replace(/&#39;|&apos;/g, "'").replace(/&amp;/g, '&');

const out = [];
for (const ch of channels) {
  let xml;
  try {
    xml = await this.helpers.httpRequest({
      method: 'GET',
      url: `https://www.youtube.com/feeds/videos.xml?channel_id=${ch.channelId}`,
      returnFullResponse: false,
      timeout: 20000,
    });
  } catch (e) {
    console.log(`Feed failed for ${ch.name}: ${e.message}`);
    continue;
  }
  const videos = [...String(xml).matchAll(/<entry>([\s\S]*?)<\/entry>/g)].map((m) => {
    const e = m[1];
    const get = (re) => (e.match(re) || [])[1];
    return {
      id: get(/<yt:videoId>([^<]+)<\/yt:videoId>/),
      title: decode(get(/<title>([^<]*)<\/title>/) || ''),
      url: get(/<link rel="alternate" href="([^"]+)"/),
      published: get(/<published>([^<]+)<\/published>/),
    };
  }).filter((v) => v.id);

  const first = !state.seen[ch.channelId];
  const seen = new Set(state.seen[ch.channelId] || []);
  const fresh = videos.filter((v) => !seen.has(v.id));
  // First time we see a channel: record its videos, don't flood Discord.
  if (!first) {
    for (const v of fresh.sort((a, b) => a.published.localeCompare(b.published))) {
      out.push({ json: {
        category: ch.category,
        channel: ch.name,
        videoId: v.id,
        title: v.title,
        url: v.url,
        published: v.published,
        webhookUrl: webhooks[ch.category],
      } });
    }
  }
  state.seen[ch.channelId] = [...videos.map((v) => v.id), ...seen].slice(0, 100);
}
return out;
"""


def build(webhooks):
    channels = [
        {"category": cat, "name": name, "handle": handle, "channelId": cid}
        for cat, items in CHANNELS.items()
        for name, handle, cid in items
    ]
    js = (JS.replace("__CHANNELS__", json.dumps(channels, indent=2))
            .replace("__WEBHOOKS__", json.dumps(webhooks, indent=2)))
    return {
        "name": "YouTube to Discord",
        "nodes": [
            {
                "parameters": {"rule": {"interval": [{"triggerAtHour": 9}]}},
                "id": "a1000000-0000-4000-8000-000000000001",
                "name": "Daily at 09:00",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 0],
            },
            {
                "parameters": {"jsCode": js.strip()},
                "id": "a1000000-0000-4000-8000-000000000002",
                "name": "Find new videos",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [224, 0],
            },
            {
                "parameters": {
                    "method": "POST",
                    "url": "={{ $json.webhookUrl }}",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify({ content: '📺 **' + $json.channel + '** posted a new video:\\n' + $json.title + '\\n' + $json.url }) }}",
                    "options": {
                        "batching": {"batch": {"batchSize": 1, "batchInterval": 1000}}
                    },
                },
                "id": "a1000000-0000-4000-8000-000000000003",
                "name": "Post to Discord",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [448, 0],
            },
        ],
        "connections": {
            "Daily at 09:00": {"main": [[{"node": "Find new videos", "type": "main", "index": 0}]]},
            "Find new videos": {"main": [[{"node": "Post to Discord", "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


if __name__ == "__main__":
    cfg = json.loads((ROOT / "config.local.json").read_text())
    hooks = cfg["discord_webhooks"]
    missing = [c for c in CHANNELS if not hooks.get(c, "").startswith("https://discord.com/api/webhooks/")]
    if missing:
        sys.exit(f"config.local.json: missing/invalid Discord webhook for: {', '.join(missing)}")
    Path(sys.argv[1]).write_text(json.dumps(build(hooks), indent=2, ensure_ascii=False))
