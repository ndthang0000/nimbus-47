# Part 1 Coding Submission

- Repository: https://github.com/ndthang0000/nimbus-47
- Video: https://github.com/ndthang0000/nimbus-47/blob/main/artifacts/coding-demo.mp4
- Cloud artifact: https://github.com/ndthang0000/nimbus-47/blob/main/artifacts/digitalocean-last-run.json
- Screenshot: https://github.com/ndthang0000/nimbus-47/blob/main/artifacts/assistant-playground.png

## Evidence and Limitations

50 English articles and 50 whole-article indexed files; exact prompt, API upload and File Search implemented. Docker and manual cloud runs succeeded. Daily cron is installed and active; scheduled invocation verified on October 14, 2026 at 02:00 Vietnam time.

Responses API replaces the retired Assistants API. UI model differs from CLI due to observed UI availability. The UI answer is correct and cited but uses numbered steps rather than bullets; the Article URL label is present. Screenshot is a draft, not proof of saved prompt persistence.

Video is a captioned walkthrough of real code, logs and the supplied UI screenshot, not a continuous recording or voiceover. It does not recreate an initial upload as a new live event.

Article sampling is alphabetical, not comprehensive. Internal embedding chunk totals are not directly exposed. Sync swaps are not atomic; a narrow API-create/persist crash window can leave an orphan. Omitted articles and detached raw files are retained. Update/failure scenarios use mocked API tests; live verification covers unchanged content.

Droplet state needs private backup before destruction. OpenAI store expires after seven inactive days. Focused working time was not automatically tracked.

Part 2 Planning is separate and still outstanding. Send both parts together, separately labeled. Confirm reviewer access if the repository is private.

## Email Draft (complete Part 2 before sending)

Dear HR Team,

Please find my Part 1 Coding Test submission below:

- Source code: https://github.com/ndthang0000/nimbus-47
- Video: https://github.com/ndthang0000/nimbus-47/blob/main/artifacts/coding-demo.mp4
- Cloud run artifact: https://github.com/ndthang0000/nimbus-47/blob/main/artifacts/digitalocean-last-run.json

The README includes setup, chunking details and limitations. I used Responses API with File Search and Vector Store as the current replacement for the retired Assistants API.

[Add the separate Part 2 Planning link here.]

Best regards,
Nguyen Duc Thang

The current video/screenshot predate the active store. Replace them with a user-recorded demo; do not present their old file counts as current.
