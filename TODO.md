# TODO

## News workflow (`egPPRlZmUz28A0Rn`)

- [ ] Include each article's short description (the RSS `description` /
      `contentSnippet` field) next to the title and link, for both AD and NOS.
  - Discord: the "Format AD" / "Format NOS" lists only show title, link and
    time. Adding the description means more messages per run (Discord's
    2000-char limit), so decide on a length cap per item (e.g. 200 chars).
    Escape it like the title (mentions, markdown).
  - Herdr: the `news-ad` / `news-nos` rows already carry the description in
    `summary`, trimmed to 300 chars. Decide whether that cap should change.
