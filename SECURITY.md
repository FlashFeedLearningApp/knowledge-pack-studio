# Security and credential handling

Knowledge Pack Studio uses bring-your-own-provider credentials.

## API keys

- Prefer the dedicated Colab Secret `OPENAI_API_KEY_FF_KP`.
- Store a strong, unique Gradio password in the Colab Secret `FF_KP_STUDIO_PASSWORD`.
- The notebook intentionally does not fall back to `OPENAI_API_KEY`; authors with multiple keys
  must select the Knowledge Pack credential explicitly.
- A key entered in the Studio UI is masked and retained only in the active Python process.
- Keys must never be written to run artifacts, notebooks, logs, traces, exported bundles, or Git.
- Error artifacts record exception type and message; provider libraries and application code must
  redact credentials from exception text before public release.
- Use a dedicated OpenAI project/key with appropriate spend limits for authoring.
- Rotate a key immediately if it appears in notebook output or an exported artifact.

## Public-link access

Keeping an API key in the Python process prevents credential persistence, but it does not control
who may invoke that process. Gradio share URLs are public tunnels, so every Colab launch is
password-protected with the username `ff-kp-author` and the `FF_KP_STUDIO_PASSWORD` secret. The
launcher refuses to create an unauthenticated public share link. Treat both the URL and password as
sensitive, close the runtime when finished, and do not reuse the password elsewhere.

## Trust boundary

In Colab, model calls originate from the user's own runtime. The repository source and installed
package should be reviewed before entering credentials. Pin notebook installs to a reviewed release
tag rather than a mutable branch for production use.

## Reporting

Do not file a public issue containing a credential or sensitive source document. Revoke exposed
credentials before reporting the defect.
