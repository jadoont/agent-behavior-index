// Canary for metric 3: an install-time outbound connection to a TRUSTED destination
// (api.github.com) from a process chain the control run never produces
// (npm -> sh -> node -> https). Reads nothing, sends nothing, uses no credentials --
// the point is the chain, not the payload.
const https = require("https");

https
  .get(
    { host: "api.github.com", path: "/zen", headers: { "user-agent": "abi-canary" } },
    (res) => res.resume().on("end", () => process.exit(0)),
  )
  .on("error", () => process.exit(0));
