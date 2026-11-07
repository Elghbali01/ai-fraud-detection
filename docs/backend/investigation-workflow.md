# Investigation workflow

An investigation can be created with or without a link to a stored prediction. Supported statuses
are `Open`, `In Review`, `Escalated`, and `Closed`. Allowed transitions are:

| Current | Next statuses |
|---|---|
| Open | In Review, Escalated, Closed |
| In Review | Open, Escalated, Closed |
| Escalated | In Review, Closed |
| Closed | none |

Outcomes are optional manual values: `Unconfirmed`, `Legitimate`, `Confirmed Fraud`, or
`Inconclusive`. An outcome is explicitly returned as analyst-recorded and not ground truth. The
workflow does not promote notes or investigator choices into training labels. Since Mission 04
has no auth layer, no analyst identity is attached.

Status changes, outcome entry, creation, and note addition append an event. Notes are bounded to
4,000 characters. Investigation list/detail/update/note routes are under
`/api/v1/investigations`. A closed investigation is terminal in this version.
