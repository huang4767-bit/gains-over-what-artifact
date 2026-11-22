POST HOC sensitivity (added 2026-11-16 after a code review, before any B result existed):
R2 uses the native seasonal period of the series (weekly 52, half-hourly 48, 15-minute 96, Sunspots 33)
instead of the rule written in advance 'period > 24 -> 24'. NOT part of the primary analysis; the criteria
judgement uses only the outputs in the parent folder.
