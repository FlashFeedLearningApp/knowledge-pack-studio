# Security and credential handling

Knowledge Pack Studio uses bring-your-own-provider credentials.

## API keys

- Prefer the dedicated Colab Secret `OPENAI_API_KEY_FF_KP`.
- The notebook intentionally does not fall back to `OPENAI_API_KEY`; authors with multiple keys
  must select the Knowledge Pack credential explicitly.
- The Studio UI has no API-key input. It reports only whether the dedicated credential was
  connected when the application launched.
- Local CLI users may provide the same credential through the `OPENAI_API_KEY_FF_KP` environment
  variable.
- Keys must never be written to run artifacts, notebooks, logs, traces, exported bundles, or Git.
- Error artifacts record exception type and message; provider libraries and application code must
  redact credentials from exception text before public release.
- Use a dedicated OpenAI project/key with appropriate spend limits for authoring.
- Rotate a key immediately if it appears in notebook output or an exported artifact.

## Colab-private access

Keeping an API key in the Python process prevents credential persistence, but it does not control
who may invoke that process. The standard notebook therefore launches Gradio with `share=False`.
In Colab, Gradio embeds the application through `google.colab.kernel.proxyPort` after checking
`google.colab.kernel.accessAllowed`; it does not create a public `gradio.live` tunnel. Access follows
the current user's Colab notebook/runtime authorization, so no second Studio password is required.
Close the runtime when finished and share the notebook—not a copied runtime-proxy URL.

## Explicit public sharing

Setting `share=True` creates a publicly reachable Gradio tunnel. The launcher refuses to create one
unless `auth=(username, password)` is also supplied. Gradio's built-in login is a basic access layer,
not enterprise authentication; use the private Colab flow for normal authoring.

## Trust boundary

In Colab, model calls originate from the user's own runtime. The repository source and installed
package should be reviewed before entering credentials. Pin notebook installs to a reviewed release
tag rather than a mutable branch for production use.

## Reporting

Do not file a public issue containing a credential or sensitive source document. Revoke exposed
credentials before reporting the defect.
