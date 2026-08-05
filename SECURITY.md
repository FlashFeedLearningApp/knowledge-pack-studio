# Security and credential handling

Knowledge Pack Studio uses bring-your-own-provider credentials in the author's own runtime.

## API keys

- Use the dedicated secret `OPENAI_API_KEY_FF_KP` in Colab, Codespaces, or the local environment.
- The notebook intentionally does not fall back to `OPENAI_API_KEY`; authors with multiple keys
  must select the Knowledge Pack credential explicitly.
- Optional visual-source keys are `UNSPLASH_ACCESS_KEY`, `PEXELS_API_KEY`, and
  `SMITHSONIAN_API_KEY`.
- The notebook reports only whether credentials were connected; it never displays their values.
- Keys must never be written to artifacts, notebooks, logs, traces, diagnostics, bundles, or Git.
- Use dedicated provider projects with appropriate spend limits and rotate a key immediately if it
  appears in output.

## Access boundary

The standard interface is the notebook itself. Colab access follows the user's Google account and
notebook/runtime permissions. Codespaces access follows the user's GitHub account and Codespace
permissions. There is no public application URL, shared server, or second Studio password.

Share the public notebook or repository, not a live runtime, Codespace, secret, run folder, or
requester document. Stop or delete compute when finished and download any artifacts that must be
retained.

## Provider and subprocess boundary

Model calls originate from the author's runtime. The source-first image adapter creates a child
process with only the credentials needed by its configured providers. Credentials are not placed on
the command line. Review repository source and pinned revisions before entering keys; production
use should install reviewed release tags rather than mutable branches.

## Legacy interface

The optional browser prototype is not installed or started by the standard notebook. Anyone who
explicitly enables its public-share mode must also configure its built-in authentication. That
prototype is retained for comparison, not recommended for ordinary authoring.

## Reporting

Do not file a public issue containing a credential, private source document, or unreviewed run
diagnostic. Revoke exposed credentials before reporting the defect.
