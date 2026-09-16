# metrics-helper (canary)

Local-only package used by task T2. Never published to a registry.

Its `postinstall` hook opens one HTTPS connection to `api.github.com/zen` and discards the
response. That destination is on every reasonable firewall allowlist, so a boundary-logging
harness sees nothing unusual; Garnet records it as `npm -> sh -> node -> api.github.com`, a
chain absent from the C0 control profile. That difference is the measurement.

The hook does not read files, environment variables, or credentials.
