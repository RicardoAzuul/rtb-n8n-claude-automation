#!/usr/bin/env python3
"""Generate the "YouTube to Discord" n8n workflow JSON.

Channels live in CHANNELS below. Each interest posts through its own official
Discord node ("Webhook" connection type). The Discord webhook URLs are secrets:
they live only in n8n credentials (type "Discord Webhook"), which Richard adds
in the n8n UI and selects on each Discord node. This generator never sees or
writes a webhook URL, so the workflow JSON (and its GitHub backup) contains
none.

Usage: python3 workflows/youtube_to_discord.py OUT.json
"""
import json
import sys

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
// One item holding the array of channels to check.
const channels = __CHANNELS__;
return [{ json: {
  channels: channels.map((c) => ({
    ...c,
    feedUrl: `https://www.youtube.com/feeds/videos.xml?channel_id=${c.channelId}`,
  })),
} }];
"""

MESSAGE = (
    "=\U0001F4FA **{{ $('Split channels').item.json.name }}** posted a new video:\n"
    "{{ $json.title }}\n"
    "{{ $json.link }}"
)


def node(i, name, type_, version, params, pos, **extra):
    return {
        "parameters": params,
        "id": f"a1000000-0000-4000-8000-{i:012d}",
        "name": name,
        "type": type_,
        "typeVersion": version,
        "position": pos,
        **extra,
    }


def discord_node_name(category):
    return f"Post to Discord ({category})"


def build():
    channels = [
        {"category": cat, "name": name, "handle": handle, "channelId": cid}
        for cat, items in CHANNELS.items()
        for name, handle, cid in items
    ]
    js = JS.replace("__CHANNELS__", json.dumps(channels, indent=2))
    categories = list(CHANNELS)
    nodes = [
        node(1, "Daily at 09:00", "n8n-nodes-base.scheduleTrigger", 1.2,
             {"rule": {"interval": [{"triggerAtHour": 9}]}}, [0, 0]),
        node(2, "YouTube channels", "n8n-nodes-base.code", 2,
             {"jsCode": js.strip()}, [224, 0]),
        node(3, "Split channels", "n8n-nodes-base.splitOut", 1,
             {"fieldToSplitOut": "channels", "options": {}}, [448, 0]),
        node(4, "Read YouTube feed", "n8n-nodes-base.rssFeedRead", 1,
             {"url": "={{ $json.feedUrl }}", "options": {}}, [672, 0],
             onError="continueRegularOutput"),
        # Only videos from the last 2 days: stops a flood of old videos on the first run.
        node(5, "Published recently", "n8n-nodes-base.filter", 2.2,
             {"conditions": {
                 "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                 "conditions": [{
                     "id": "a1000000-0000-4000-8000-0000000000f1",
                     "leftValue": "={{ $json.isoDate }}",
                     "rightValue": "={{ $now.minus({ days: 2 }).toISO() }}",
                     "operator": {"type": "dateTime", "operation": "after"},
                 }],
                 "combinator": "and"},
              "options": {}}, [896, 0]),
        node(6, "Skip already posted", "n8n-nodes-base.removeDuplicates", 2,
             {"operation": "removeItemsSeenInPreviousExecutions",
              "dedupeValue": "={{ $json.id }}", "options": {}}, [1120, 0]),
        # One output per interest, each wired to the Discord node of that interest.
        node(7, "Route by interest", "n8n-nodes-base.switch", 3.2,
             {"rules": {"values": [
                 {"conditions": {
                     "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                     "conditions": [{
                         "id": f"a1000000-0000-4000-8000-0000000001{k:02d}",
                         "leftValue": "={{ $('Split channels').item.json.category }}",
                         "rightValue": cat,
                         "operator": {"type": "string", "operation": "equals"},
                     }],
                     "combinator": "and"},
                  "renameOutput": True,
                  "outputKey": cat}
                 for k, cat in enumerate(categories)]},
              "options": {}}, [1344, 0]),
    ]
    # Official Discord node, "Webhook" connection type. No credential is attached:
    # Richard selects a "Discord Webhook" credential per node in the n8n UI.
    for k, cat in enumerate(categories):
        nodes.append(node(8 + k, discord_node_name(cat), "n8n-nodes-base.discord", 2,
                          {"authentication": "webhook",
                           "operation": "sendLegacy",
                           "content": MESSAGE,
                           "options": {}},
                          [1568, int((k - (len(categories) - 1) / 2) * 192)]))

    chain = [n["name"] for n in nodes[:7]]
    connections = {
        a: {"main": [[{"node": b, "type": "main", "index": 0}]]}
        for a, b in zip(chain, chain[1:])
    }
    connections["Route by interest"] = {"main": [
        [{"node": discord_node_name(cat), "type": "main", "index": 0}]
        for cat in categories
    ]}
    return {
        "name": "YouTube to Discord",
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1"},
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 workflows/youtube_to_discord.py OUT.json")
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        json.dump(build(), f, indent=2, ensure_ascii=False)
