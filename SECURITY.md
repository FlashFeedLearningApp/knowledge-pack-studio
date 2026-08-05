# Security and credential handling

Knowledge Pack Studio uses bring-your-own-provider credentials.

## API keys

- Prefer Colab Secrets for `OPENAI_API_KEY`.
- A key entered in the Studio UI is masked and retained only in the active Python process.
- Keys must never be written to run artifacts, notebooks, logs, traces, exported bundles, or Git.
- Error artifacts record exception type and message; provider libraries and application code must
  redact credentials from exception text before public release.
- Use a dedicated OpenAI project/key with appropriate spend limits for authoring.
- Rotate a key immediately if it appears in notebook output or an exported artifact.

## Trust boundary

In Colab, model calls originate from the user's own runtime. The repository source and installed
package should be reviewed before entering credentials. Pin notebook installs to a reviewed release
tag rather than a mutable branch for production use.

## Reporting

Do not file a public issue containing a credential or sensitive source document. Revoke exposed
credentials before reporting the defect.
