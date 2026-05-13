# Why I made this

I built this because I wanted to watch the feedback loops play out.

The threat model in [docs/threatmodel.md](docs/threatmodel.md) is short, and that is the point. Seven domains. Six
trigger categories. Six systemic stressors. Five recovery pathways. You can read it in five minutes. What you cannot do
in five minutes is work out, in your head, what actually happens when those pieces interact. At least I can not.

That was the question.

A pump fails in the Shades. Trust drops, but only in the Shades, because the inequality stressor scales the damage by
district. The fall in district trust reweights into the city aggregate, which depresses political stability, which
slows the response to the next incident, which extends a different event's downtime, which triggers a duration penalty
on local trust, which closes the loop a different way. You can write out any one of those arrows. Writing all of them at
once does not fit on a whiteboard.

So I built the whiteboard.

The threat model is the spec. The code follows the threat model, not the other way round. Every stressor in the threat
model has an engine effect. Every recovery pathway is offered for the domains the threat model lists. The
narrative-effects stressor accumulates when you reach for press statements, decays nothing on its own, and quietly
amplifies trust damage on the events you are ignoring. You can see the loop happen. You can also feel it close on you
twenty minutes into a session.

Some of the loops surprised me. The press statement is the obvious one: it slows scandal decay, so it feels free, until
the window expires and the contradicts penalty fires and the narrative-effects counter ticks up and the next scandal
hurts more than it would have. That is four layers of feedback from one button. None of those layers are clever
individually. They are just compounded.

This is also why the simulator does not let you win. There is no high score. The threat model does not specify a victory
state, so the engine does not provide one. What it provides is a record of which loops you fed and which ones fed you.

If you want to know what governing a fragile system feels like from the inside, this is the cheapest way I could think
of to find out. The contract in [docs/contract.md](docs/contract.md) is the honest companion to the threat model: it
lists what the simulator pretends to model and, more usefully, what it refuses to. No packet captures, no named
hackers, no risk matrices, no high scores. No real elections lost, no real water cut, no real Watch officers reassigned
to Lord Rust's carriage. Just a city that keeps reminding you, in small mechanical ways, that everything depends on
everything else.

I wanted to see how that lands. Now I can.
