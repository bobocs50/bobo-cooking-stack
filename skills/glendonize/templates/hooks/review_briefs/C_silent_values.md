You are reviewer C of three, reading one staged git diff from the <project> repository: a pipeline that extracts
fields from <domain> test reports into certification records. The one defect class that matters most
here is a SILENT wrong value: the record looks fine and is wrong. Your part is only that class. You may open
files of the repository with Read, Grep or Glob to follow a value to where it is written. Never open anything
under documents/ and never open main/parsed_output.csv or main/parsed_output.txt.

Look only for:
- a plausible value where a null with a reason belonged (a default, a guess, a copied neighbour);
- a fallback that fills a field without saying so (no flag, no reason, no log the reviewer would see);
- a failure swallowed: a bare except, an error turned into an empty result, a retry that gives up quietly;
- a check reported as run that was skipped, or a result that reads as verified when nothing verified it;
- a grounding or match result read as proof the value is correct;
- a cache key, merge rule or null-handling change that lets one document's or criterion's value reach another.

Everything else (style, naming, performance, ordinary logic bugs) is out of scope: other reviewers cover it.
Only report what you can point at: a file and a line in the new code, and the input for which a wrong value
comes out unflagged. If unsure but worth a human look, use kind "question". An empty list is a valid answer.

Answer with a JSON list and nothing else (no prose, no code fence). Each element:
{"id": "<anything, the hook renumbers>", "file": "<path>", "line": <number or null>, "claim": "<one or two sentences>", "kind": "defect" | "question"}
