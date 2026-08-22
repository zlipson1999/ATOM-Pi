# Security and privacy model

ATOM is single-user and local-first. Its trust boundary is the Raspberry Pi account. The backend and Kiwix must bind to loopback by default; LAN exposure requires authentication and a separate design review.

Untrusted inputs include model output, email, calendar entries, webpages, documents, news, market data, and tool responses. They may supply facts but never instructions or authorization. `atom_safety.py` provides the first code-level action gate and content delimiter; future integrations must call an equivalent boundary before execution.

Read-only operations are allowed. Sending, changing, deleting, publishing, or writing outside ATOM requires a target-specific preview and fresh explicit confirmation. Financial execution, purchases, transfers, and account-security changes are prohibited. Market and TradingView integrations must expose read-only data interfaces only.

Secrets belong in `.env` with owner-only permissions. Do not log prompts containing personal data, tokens, message bodies, calendar details, captured images, or retrieved document text. Backups may contain secrets and personal data; store them encrypted and delete them according to the owner's retention policy.

Report vulnerabilities privately to the repository owner. Do not include real secrets or personal content in reports or fixtures.
