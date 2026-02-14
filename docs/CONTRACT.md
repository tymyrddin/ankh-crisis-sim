# Simulation Contract: Ankh-Morpork: Lord Vetinari's Dilemma

A statement of what the simulation will and will not model (sets expectations for players and guides development).

## The simulation models

### What breaks
- Critical infrastructure services: energy, water, transport, communications, public services, commercial activity, residential habitability
- Dependencies between them (water needs power, hospitals need both)
- Degradation over time from underinvestment
- Gradual deterioration that may go unnoticed until too late

### Who is affected
- Districts with different characteristics (wealthy, poor, industrial, mixed)
- Specific building types with different sensitivities
- The unequal distribution of impact (systemic inequality is a feature, not a bug)
- This inequality can worsen or improve based on player choices

### How they feel about it
- Public trust (aggregate confidence in leadership)
- District-level satisfaction
- Media attention and narrative framing (simple headlines with optional depth)
- Protests, political pressure, regulatory intervention
- Legitimacy (harder to regain than trust)

### What you can do about it
- A curated set of remedy types (patch, upgrade, workaround, compensate, blame, communicate)
- Each with distinct cost, downtime, effectiveness, and side effects
- Press statements that influence narrative
- Recovery priorities that shape equity outcomes

### When consequences land
- Immediate effects (service restoration, cost)
- Delayed effects (recurrence risk, trust changes, political fallout)
- Cumulative effects (legitimacy, election outcomes)
- Duration penalties (longer outages hurt more)

### The story of it all
- How events are framed (neglect, attack, bad luck, incompetence, investment)
- How press statements shape framing
- How rumours spread during information blackouts
- How narrative shapes political consequences

### Time and pacing
- Real-time simulation with pause
- Variable speed (fast-forward through quiet periods)
- Events unfold at realistic relative speeds

### Endings
- Multiple loss conditions (election, revolt, bankruptcy, collapse, assassination)
- Natural term completion
- Early retirement
- No victory, only reflection

## The simulation will NOT model

### Technical details
- No packet captures
- No CVEs, exploits, or malware names
- No "how" of attacks, only "what failed" and "what it costs"
- No firewall rules, patch versions, or configuration settings

### Individual threat actors
- No named hackers, criminal gangs, or nation-state groups as characters
- Actors appear only through the *events* they cause
- No attribution minigame (attribution is uncertain and arrives late, if at all)

### Perfect information
- You do not see all failures immediately
- Some failures are hidden until detected by satisfaction drops, media, or cascades
- You do not know root causes without investigation (which costs time)
- You do not know if a fix will hold

### Unlimited resources
- Budget is finite and contested (other departments want it)
- Political capital is finite
- Time is finite (election cycles, crisis windows)
- Attention is finite (you cannot investigate everything)

### Easy fixes
- No silver bullets
- Every choice has trade-offs
- Some damage is permanent (lost trust never fully returns)
- Good decisions often hurt now, bad decisions hurt later

### Winners
- No high scores
- No "optimal" playthroughs
- No beating the game
- Only surviving and accounting for your choices
- Only "You served your term. Here is what happened."

### Technical jargon
- No "availability, integrity, confidentiality" framing
- No "risk matrices" or "risk scores"
- Plain language only: "People are angry," "The hospital is struggling," "The brewery can't brew"

### Required deep attention
- Simple headlines always visible
- Richer stories available but optional
- Players can engage at their preferred depth

## TL;DR

1. Run in real-time with pause: Players control pace, can speed through quiet periods
2. Use multi-layered visibility: Major failures immediate, minor failures require detection
3. Provide two narrative layers: Simple headlines always, richer stories on demand
4. Allow press statements: Narrative is output of actions, including communication
5. Make stressors dynamic: Fixed at start but evolve with player choices
6. Support multiple end conditions: Loss, term completion, retirement
7. Use simplified relative models: Configurable for eventual real-world calibration
