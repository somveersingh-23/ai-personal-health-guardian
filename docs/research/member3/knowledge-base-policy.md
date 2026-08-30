# Member 3 Knowledge Base Policy

## Who may approve content
Only designated clinical reviewers and product managers may approve content for the Member 3 RAG knowledge base.

## Accepted source types
- Peer-reviewed medical guidelines
- Internal verified educational materials
- Prototype guidance drafted by the product team

## Review statuses and their meaning
- `pending`: Awaiting review
- `approved`: Reviewed and approved for use
- `rejected`: Rejected for use
- `expired`: Previously approved but now out of date

## Expiry process
Content may have an optional `expires_on` date. When this date passes, the chunk is automatically excluded from retrieval.

## Prohibited content
- Diagnostic claims
- Treatment recommendations
- Fabricated statistics

## Source attribution
All chunks must have a clear `source_name`. Raw URLs are not presented directly in citations but can be tracked via `source_url`.

## Corrections and removals
If a chunk needs correction, it must be updated or marked `rejected`/`expired` in the JSONL file and re-deployed.

## Clear disclaimer
All prototype guidance must clearly state that it is general educational information and not clinical guidance.
